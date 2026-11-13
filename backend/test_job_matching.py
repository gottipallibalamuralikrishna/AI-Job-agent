
# test_job_matching.py

import unittest
from types import SimpleNamespace

from app.services.job_matching_service import JobMatchingService


class TestJobMatchingService(unittest.TestCase):

    def setUp(self):
        self.profile = {
            "technical_skills": [
                "React",
                "React Native",
                "JavaScript",
                "TypeScript",
                "HTML",
                "CSS",
                "Material UI",
                "Redux",
                "Python",
                "FastAPI",
                "PostgreSQL",
                "Git",
            ]
        }

    def create_job(self, title, required_skills, description=""):
        return SimpleNamespace(
            title=title,
            required_skills=required_skills,
            description=description,
        )

    def test_react_frontend_job_matches(self):
        job = self.create_job(
            "React Frontend Developer",
            ["React", "JavaScript", "TypeScript", "CSS"],
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertTrue(result["is_match"])
        self.assertEqual(result["decision"], "matched")
        self.assertEqual(result["match_score"], 100.0)

    def test_java_backend_job_does_not_match(self):
        job = self.create_job(
            "Java Backend Developer",
            ["Java", "Spring Boot", "AWS"],
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertFalse(result["is_match"])
        self.assertEqual(result["decision"], "not_matched")

    def test_react_native_job_matches(self):
        job = self.create_job(
            "React Native Developer",
            ["React Native", "JavaScript", "TypeScript"],
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertTrue(result["is_match"])
        self.assertEqual(result["match_score"], 100.0)

    def test_angular_job_does_not_meet_threshold(self):
        job = self.create_job(
            "Angular Developer",
            ["Angular", "TypeScript"],
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertFalse(result["is_match"])
        self.assertEqual(result["match_score"], 50.0)

    def test_python_fastapi_job_matches(self):
        job = self.create_job(
            "Python FastAPI Developer",
            ["Python", "FastAPI", "PostgreSQL"],
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertTrue(result["is_match"])
        self.assertEqual(result["match_score"], 100.0)

    def test_missing_skills_are_returned(self):
        job = self.create_job(
            "Full Stack Developer",
            ["React", "TypeScript", "Docker", "AWS"],
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertIn("docker", result["missing_skills"])
        self.assertIn("aws", result["missing_skills"])

    def test_empty_job_skills_do_not_match(self):
        job = self.create_job(
            "Software Developer",
            [],
            "Looking for a motivated developer.",
        )

        result = JobMatchingService.analyze(self.profile, job)

        self.assertFalse(result["is_match"])
        self.assertEqual(result["match_score"], 0.0)

    def test_java_does_not_match_javascript(self):
        profile = {"technical_skills": ["JavaScript"]}
        job = self.create_job("Backend Developer", ["Java"])

        result = JobMatchingService.analyze(profile, job)

        self.assertEqual(result["matched_skills"], [])
        self.assertFalse(result["is_match"])


if __name__ == "__main__":
    unittest.main()
