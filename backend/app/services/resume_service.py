
import hashlib
import logging
import os
import uuid
import zipfile

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User


PDF_MIME = "application/pdf"

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


class ResumeService:

    def __init__(self, db: Session):
        self.db = db

    def delete_resume(self, resume_id: uuid.UUID, user: User) -> None:
        self.db.query(User).filter_by(id=user.id).with_for_update().one()
        resume = self.db.query(Resume).filter_by(
            id=resume_id, user_id=user.id,
        ).with_for_update().first()
        if resume is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        if resume.parsing_status == "processing":
            raise HTTPException(status_code=409, detail="Wait for resume processing to finish before deleting it.")

        path = Path(resume.storage_path)
        stored_filename = resume.stored_filename
        was_primary = resume.is_primary
        self.db.delete(resume)
        self.db.flush()
        if was_primary:
            replacement = (
                self.db.query(Resume)
                .outerjoin(ResumeProfile, ResumeProfile.resume_id == Resume.id)
                .filter(Resume.user_id == user.id)
                .order_by(
                    (ResumeProfile.id.is_not(None) & (Resume.parsing_status == "parsed")).desc(),
                    Resume.created_at.desc(), Resume.id,
                )
                .first()
            )
            if replacement is not None:
                replacement.is_primary = True
        self.db.commit()

        # Only unlink this upload inside the configured storage directory.
        try:
            if path.name == stored_filename and path.resolve().parent == Path(settings.resume_storage_dir).resolve():
                path.unlink(missing_ok=True)
        except OSError:
            logging.getLogger(__name__).warning("Could not remove stored upload for resume %s", resume_id)

    def _storage_directory(self) -> Path:
        directory = Path(settings.resume_storage_dir)

        if not directory.is_absolute():
            directory = Path.cwd() / directory

        directory.mkdir(parents=True, exist_ok=True)

        return directory.resolve()

    def _validate_docx(self, file_path: Path) -> bool:
        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                names = set(archive.namelist())

                required_files = {
                    "[Content_Types].xml",
                    "word/document.xml",
                }

                if not required_files.issubset(names):
                    return False

                # Avoid accepting unusually large expanded archives.
                if len(archive.infolist()) > 200:
                    return False

                total_uncompressed_size = sum(
                    item.file_size for item in archive.infolist()
                )

                if total_uncompressed_size > 20 * 1024 * 1024:
                    return False

                return True

        except (zipfile.BadZipFile, OSError):
            return False

    def _validate_file(
        self,
        extension: str,
        first_bytes: bytes,
        file_path: Path,
    ) -> str:

        if extension == ".pdf":
            if not first_bytes.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PDF file signature",
                )

            return PDF_MIME

        if extension == ".docx":
            if not first_bytes.startswith(b"PK"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid DOCX file signature",
                )

            if not self._validate_docx(file_path):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid DOCX document",
                )

            return DOCX_MIME

        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported",
        )

    def upload_resume(
        self,
        file: UploadFile,
        current_user: User,
    ) -> Resume:

        original_filename = Path(
            (file.filename or "").replace("\\", "/")
        ).name

        extension = Path(original_filename).suffix.lower()

        if extension not in {".pdf", ".docx"}:
            raise HTTPException(
                status_code=400,
                detail="Only PDF and DOCX files are supported",
            )

        if not original_filename or len(original_filename) > 255:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename",
            )

        directory = self._storage_directory()

        stored_filename = f"{uuid.uuid4()}{extension}"
        final_path = directory / stored_filename

        checksum = hashlib.sha256()
        file_size = 0
        first_bytes = b""

        temp_path = None

        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=directory,
                prefix=".upload-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:

                temp_path = Path(temp_file.name)

                while True:
                    chunk = file.file.read(64 * 1024)

                    if not chunk:
                        break

                    file_size += len(chunk)

                    if file_size > settings.max_resume_size_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail="Resume exceeds the 5 MB size limit",
                        )

                    if not first_bytes:
                        first_bytes = chunk[:8]

                    checksum.update(chunk)
                    temp_file.write(chunk)

            if file_size == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty",
                )

            content_type = self._validate_file(
                extension,
                first_bytes,
                temp_path,
            )

            checksum_value = checksum.hexdigest()

            existing_resume = (
                self.db.query(Resume)
                .filter(
                    Resume.user_id == current_user.id,
                    Resume.checksum_sha256 == checksum_value,
                )
                .first()
            )

            if existing_resume:
                raise HTTPException(
                    status_code=409,
                    detail="You have already uploaded this resume",
                )

            os.replace(temp_path, final_path)
            temp_path = None

            self.db.query(User).filter(User.id == current_user.id).with_for_update().one()
            has_primary = self.db.query(Resume).filter_by(user_id=current_user.id, is_primary=True).first() is not None
            resume = Resume(
                user_id=current_user.id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                storage_path=str(final_path),
                content_type=content_type,
                file_size_bytes=file_size,
                checksum_sha256=checksum_value,
                parsing_status="uploaded",
                is_primary=not has_primary,
            )

            self.db.add(resume)
            self.db.commit()
            self.db.refresh(resume)

            return resume

        except Exception:
            self.db.rollback()

            if final_path.exists():
                final_path.unlink(missing_ok=True)

            raise

        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
