import { useCallback, useEffect, useState, type ChangeEvent } from "react";

import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import {
  BriefcaseBusiness,
  CheckCircle2,
  ExternalLink,
  Globe,
  Linkedin,
  Mail,
  MessageCircle,
  Phone,
  RefreshCw,
  Search,
  Users,
  X,
} from "lucide-react";

import {
  recruiterContactsApi,
  type ContactType,
  type RecruiterContact,
  type RecruiterContactStats,
  type SourceType,
} from "../../api/recruiterContactsApi";

import "./recruiter-contacts.css";
import RecruiterEmailDialog from '../../components/RecruiterEmailDialog';

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

const CONTACT_TYPES: {
  label: string;
  value: ContactType | "";
}[] = [
  { label: "All contact types", value: "" },
  { label: "Email", value: "email" },
  { label: "Phone", value: "phone" },
  { label: "LinkedIn", value: "linkedin" },
  { label: "Telegram", value: "telegram" },
  { label: "Website", value: "website" },
  { label: "Application URL", value: "application_url" },
];

const SOURCE_TYPES: {
  label: string;
  value: SourceType | "";
}[] = [
  { label: "All sources", value: "" },
  { label: "Telegram", value: "telegram" },
  { label: "WhatsApp", value: "whatsapp" },
  { label: "Greenhouse", value: "greenhouse" },
  { label: "Lever", value: "lever" },
  { label: "RSS", value: "rss" },
  { label: "Career page", value: "career_page" },
  { label: "API", value: "api" },
  { label: "Manual", value: "manual" },
];

function getContactIcon(type: ContactType) {
  switch (type) {
    case "email":
      return <Mail size={16} />;

    case "phone":
      return <Phone size={16} />;

    case "linkedin":
      return <Linkedin size={16} />;

    case "telegram":
      return <MessageCircle size={16} />;

    case "website":
    case "application_url":
      return <Globe size={16} />;

    default:
      return <Users size={16} />;
  }
}

function getContactLabel(type: ContactType) {
  switch (type) {
    case "application_url":
      return "Application URL";
    default:
      return type.charAt(0).toUpperCase() + type.slice(1);
  }
}

function getContactHref(contact: RecruiterContact): string | null {
  const value = contact.contact_value.trim();

  switch (contact.contact_type) {
    case "email":
      return `mailto:${value}`;

    case "phone":
      return `tel:${value.replace(/[^\d+]/g, "")}`;

    case "linkedin":
    case "telegram":
    case "website":
    case "application_url":
      if (/^https?:\/\//i.test(value)) {
        return value;
      }

      return null;

    default:
      return null;
  }
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function ContactMetric({
  title,
  value,
  description,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  description: string;
  icon: typeof Users;
  color: string;
}) {
  return (
    <Card className="contact-metric-card">
      <CardContent>
        <Box className="contact-metric-top">
          <Box
            className="contact-metric-icon"
            sx={{
              color,
              backgroundColor: `${color}18`,
            }}
          >
            <Icon size={20} />
          </Box>
        </Box>

        <Typography className="contact-metric-value">
          {value.toLocaleString("en-IN")}
        </Typography>

        <Typography className="contact-metric-title">{title}</Typography>

        <Typography className="contact-metric-description">
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
}

function ContactDetailsDialog({
  contact,
  onClose,
}: {
  contact: RecruiterContact | null;
  onClose: () => void;
}) {
  if (!contact) {
    return null;
  }

  const href = getContactHref(contact);

  return (
    <Dialog
      open={Boolean(contact)}
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      PaperProps={{
        className: "contact-details-dialog",
      }}
    >
      <DialogTitle>
        <Box className="contact-dialog-heading">
          <Box>
            <Typography className="contact-dialog-eyebrow">
              RECRUITER CONTACT
            </Typography>

            <Typography className="contact-dialog-title">
              Contact details
            </Typography>
          </Box>

          <IconButton onClick={onClose} size="small">
            <X size={19} />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={2.5}>
          <Box className="contact-detail-identity">
            <Avatar className="contact-detail-avatar">
              {getContactIcon(contact.contact_type)}
            </Avatar>

            <Box>
              <Typography className="contact-detail-name">
                {contact.contact_name || "Contact name not available"}
              </Typography>

              <Typography className="contact-detail-value">
                {contact.contact_value}
              </Typography>
            </Box>
          </Box>

          <Box className="contact-detail-row">
            <Typography>Contact type</Typography>

            <Chip
              size="small"
              label={getContactLabel(contact.contact_type)}
              className="contact-type-chip"
            />
          </Box>

          <Box className="contact-detail-row">
            <Typography>Verification</Typography>

            <Chip
              size="small"
              icon={
                contact.is_verified ? <CheckCircle2 size={14} /> : undefined
              }
              label={contact.is_verified ? "Verified" : "Unverified"}
              className={
                contact.is_verified
                  ? "contact-verified-chip"
                  : "contact-unverified-chip"
              }
            />
          </Box>

          <Box className="contact-detail-row">
            <Typography>Added on</Typography>
            <Typography>{formatDate(contact.created_at)}</Typography>
          </Box>

          <Box className="contact-job-panel">
            <Typography className="contact-job-panel-label">
              ASSOCIATED JOB
            </Typography>

            <Typography className="contact-job-title">
              {contact.job.title}
            </Typography>

            <Typography className="contact-job-company">
              {contact.job.company_name}
            </Typography>

            <Typography className="contact-job-location">
              {contact.job.location || "Location not specified"}
            </Typography>

            {contact.job.application_url && (
              <Button
                component="a"
                href={contact.job.application_url}
                target="_blank"
                rel="noopener noreferrer"
                size="small"
                endIcon={<ExternalLink size={14} />}
                className="contact-application-link"
              >
                View job application
              </Button>
            )}
          </Box>

          {!contact.is_verified && (
            <Alert severity="info">
              This contact was extracted from a job source and has not been
              independently verified.
            </Alert>
          )}
        </Stack>
      </DialogContent>

      <DialogActions>
        {contact.contact_type === 'email' && <RecruiterEmailDialog contactId={contact.id} />}
        {href && contact.contact_type !== 'email' && (
          <Button
            component="a"
            href={href}
            target={
              contact.contact_type === "phone"
                ? undefined
                : "_blank"
            }
            rel="noopener noreferrer"
            variant="contained"
            endIcon={<ExternalLink size={15} />}
          >
            {contact.contact_type === "phone"
                ? "Call contact"
                : "Open contact"}
          </Button>
        )}

        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function RecruiterContactsPage() {
  const [contacts, setContacts] = useState<RecruiterContact[]>([]);
  const [stats, setStats] = useState<RecruiterContactStats | null>(null);
  const [selectedContact, setSelectedContact] =
    useState<RecruiterContact | null>(null);

  const [search, setSearch] = useState("");
  const [contactType, setContactType] = useState<ContactType | "">("");
  const [sourceType, setSourceType] = useState<SourceType | "">("");

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState("");

  const loadContacts = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const result = await recruiterContactsApi.getContacts({
        page: page + 1,
        page_size: pageSize,
        search: search.trim(),
        contact_type: contactType,
        source_type: sourceType,
      });

      setContacts(result.items);
      setTotal(result.total);
    } catch (err: unknown) {
      let message = "Unable to load recruiter contacts.";

      if (typeof err === "object" && err !== null && "response" in err) {
        const response = (
          err as {
            response?: {
              data?: { detail?: string };
            };
          }
        ).response;

        message = response?.data?.detail ?? message;
      }

      setError(message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, contactType, sourceType]);

  const loadStats = useCallback(async () => {
    try {
      setStatsLoading(true);

      const result = await recruiterContactsApi.getStats();

      setStats(result);
    } catch {
      // Stats are supplementary; keep the contacts table usable.
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadContacts();
    }, 350);

    return () => window.clearTimeout(timeout);
  }, [loadContacts]);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const handleRefresh = () => {
    void loadContacts();
    void loadStats();
  };

  const handleClearFilters = () => {
    setSearch("");
    setContactType("");
    setSourceType("");
    setPage(0);
  };

  const handlePageChange = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handlePageSizeChange = (event: ChangeEvent<HTMLInputElement>) => {
    setPageSize(Number(event.target.value));
    setPage(0);
  };

  return (
    <Box className="recruiter-contacts-page">
      <Box sx={{ mb: 2 }}><RecruiterEmailDialog /></Box>
      <Box className="contacts-page-heading">
        <Box>
          <Typography className="contacts-eyebrow">
            RECRUITMENT INTELLIGENCE
          </Typography>

          <Typography className="contacts-page-title">
            Recruiter Contacts
          </Typography>

          <Typography className="contacts-page-subtitle">
            Discover and manage recruiter contact information collected from
            your job sources.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={<RefreshCw size={16} />}
          onClick={handleRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert
          severity="error"
          onClose={() => setError("")}
          className="contacts-alert"
        >
          {error}
        </Alert>
      )}

      <Box className="contacts-section">
        <Box className="contacts-section-heading">
          <Box>
            <Typography className="contacts-section-title">
              Contact overview
            </Typography>

            <Typography className="contacts-section-description">
              Summary of contacts collected across your job sources.
            </Typography>
          </Box>
        </Box>

        <Box className="contact-metrics-grid">
          <ContactMetric
            title="Total contacts"
            value={statsLoading ? 0 : (stats?.total_contacts ?? 0)}
            description="Collected contact records"
            icon={Users}
            color="#a99aff"
          />

          <ContactMetric
            title="Email addresses"
            value={statsLoading ? 0 : (stats?.total_emails ?? 0)}
            description="Potential recruiter emails"
            icon={Mail}
            color="#65d6a5"
          />

          <ContactMetric
            title="Phone numbers"
            value={statsLoading ? 0 : (stats?.total_phones ?? 0)}
            description="Extracted phone contacts"
            icon={Phone}
            color="#36cfc9"
          />

          <ContactMetric
            title="LinkedIn profiles"
            value={statsLoading ? 0 : (stats?.total_linkedin ?? 0)}
            description="Professional profile links"
            icon={Linkedin}
            color="#f5b95f"
          />
        </Box>
      </Box>

      <Box className="contacts-section">
        <Box className="contacts-results-heading">
          <Box>
            <Typography className="contacts-section-title">
              Contact directory
            </Typography>

            <Typography className="contacts-section-description">
              {total.toLocaleString("en-IN")} contacts found
            </Typography>
          </Box>

          <Chip
            icon={<BriefcaseBusiness size={15} />}
            label={`${stats?.jobs_with_contacts ?? 0} jobs with contacts`}
            className="contacts-job-count-chip"
          />
        </Box>

        <Card className="contacts-filter-card">
          <CardContent className="contacts-filter-content">
            <TextField
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(0);
              }}
              placeholder="Search email, name, company or job..."
              size="small"
              className="contacts-search-field"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={17} />
                  </InputAdornment>
                ),
              }}
            />

            <FormControl size="small" className="contacts-filter-select">
              <InputLabel>Contact type</InputLabel>

              <Select
                value={contactType}
                label="Contact type"
                onChange={(event) => {
                  setContactType(event.target.value as ContactType | "");
                  setPage(0);
                }}
              >
                {CONTACT_TYPES.map((item) => (
                  <MenuItem key={item.label} value={item.value}>
                    {item.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small" className="contacts-filter-select">
              <InputLabel>Source</InputLabel>

              <Select
                value={sourceType}
                label="Source"
                onChange={(event) => {
                  setSourceType(event.target.value as SourceType | "");
                  setPage(0);
                }}
              >
                {SOURCE_TYPES.map((item) => (
                  <MenuItem key={item.label} value={item.value}>
                    {item.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="text"
              onClick={handleClearFilters}
              className="contacts-clear-button"
            >
              Clear filters
            </Button>
          </CardContent>
        </Card>

        <Card className="contacts-table-card">
          {loading ? (
            <Box className="contacts-loading">
              <CircularProgress size={30} />

              <Typography color="text.secondary">
                Loading recruiter contacts...
              </Typography>
            </Box>
          ) : contacts.length === 0 ? (
            <Box className="contacts-empty">
              <Box className="contacts-empty-icon">
                <Users size={28} />
              </Box>

              <Typography variant="h6" fontWeight={750}>
                No contacts found
              </Typography>

              <Typography color="text.secondary" textAlign="center">
                Try changing your search or filters, or collect more jobs from
                your configured sources.
              </Typography>

              {(search || contactType || sourceType) && (
                <Button variant="outlined" onClick={handleClearFilters}>
                  Clear filters
                </Button>
              )}
            </Box>
          ) : (
            <>
              <TableContainer>
                <Table className="contacts-table">
                  <TableHead>
                    <TableRow>
                      <TableCell>Contact</TableCell>
                      <TableCell>Organization</TableCell>
                      <TableCell>Contact type</TableCell>
                      <TableCell>Associated job</TableCell>
                      <TableCell>Location</TableCell>
                      <TableCell>Verification</TableCell>
                      <TableCell>Added</TableCell>
                      <TableCell align="right">Action</TableCell>
                    </TableRow>
                  </TableHead>

                  <TableBody>
                    {contacts.map((contact) => (
                      <TableRow key={contact.id} hover>
                        <TableCell>
                          <Box className="contacts-person-cell">
                            <Avatar className="contacts-person-avatar">
                              {getContactIcon(contact.contact_type)}
                            </Avatar>

                            <Box minWidth={0}>
                              <Typography className="contacts-person-name">
                                {contact.contact_name || "Contact"}
                              </Typography>

                              <Typography
                                className="contacts-person-value"
                                title={contact.contact_value}
                              >
                                {contact.contact_value}
                              </Typography>
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box className="contacts-organization-cell">
                            <Typography className="contacts-organization-name">
                              {contact.job.company_name ||
                                "Organization not identified"}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            icon={getContactIcon(contact.contact_type)}
                            label={getContactLabel(contact.contact_type)}
                            className="contact-type-chip"
                          />
                        </TableCell>

                        <TableCell>
                          <Box className="contacts-job-cell">
                            <Typography className="contacts-job-name">
                              {contact.job.title}
                            </Typography>

                            <Typography className="contacts-job-company">
                              {contact.job.company_name}
                            </Typography>
                          </Box>
                        </TableCell>

                        <TableCell>
                          <Typography className="contacts-location">
                            {contact.job.location || "—"}
                          </Typography>
                        </TableCell>

                        <TableCell>
                          <Chip
                            size="small"
                            label={
                              contact.is_verified ? "Verified" : "Unverified"
                            }
                            className={
                              contact.is_verified
                                ? "contact-verified-chip"
                                : "contact-unverified-chip"
                            }
                          />
                        </TableCell>

                        <TableCell>
                          <Typography className="contacts-date">
                            {formatDate(contact.created_at)}
                          </Typography>
                        </TableCell>

                        <TableCell align="right">
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => setSelectedContact(contact)}
                          >
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <TablePagination
                component="div"
                count={total}
                page={page}
                onPageChange={handlePageChange}
                rowsPerPage={pageSize}
                onRowsPerPageChange={handlePageSizeChange}
                rowsPerPageOptions={PAGE_SIZE_OPTIONS}
              />
            </>
          )}
        </Card>
      </Box>

      <ContactDetailsDialog
        contact={selectedContact}
        onClose={() => setSelectedContact(null)}
      />
    </Box>
  );
}
