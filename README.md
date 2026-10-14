# Common Ground Migration

> [!IMPORTANT]
> **Portfolio demonstration only.** Common Ground Migration is a fictional service created to demonstrate full-stack software engineering. It is not a migration practice, does not provide legal or migration advice, and must not be used to make migration decisions.

Common Ground Migration is a deployable demonstration website and client-case portal for a migration advisory practice. It combines a warm public website with email-verified accounts, private case tracking, consultation intake and a staff operations workspace.

**Live portfolio demo:** [https://commongroundmigration.duckdns.org/](https://commongroundmigration.duckdns.org/)  
The deployed demo uses HTTPS. It is a portfolio demonstration only and does not provide legal or migration advice.

The brand, people and editorial content are fictional. Replace all demonstration business details with verified practice information before public use. Website content is general information only and must not be presented as individual migration or legal advice.

## Engineering highlights

- End-to-end Django application rather than a static design mock-up
- PostgreSQL persistence in production and SQLite for local development
- Email-verified registration and one-time password-reset codes
- Passwords and verification codes stored as secure hashes
- Role-based client and staff access to case information
- Automated consultation confirmation and staff-notification emails
- Server-side form validation, CSRF protection, bot honeypot and request throttling
- Dockerised deployment behind Nginx with a public health endpoint
- Responsive, accessible interface with keyboard-friendly validation feedback

## Architecture

```text
Browser
   │
   ▼
Nginx reverse proxy
   │
   ▼
Gunicorn → Django application ──→ SMTP provider
   │
   ▼
PostgreSQL persistent volume
```

## What is included

### Public website

- Responsive home page in the warm, human-centred “Concept C” direction
- Visa pathway, practice approach and practical guide pages
- Consultation request form stored in the practice database
- Consultation confirmation email for the person making the enquiry
- New-enquiry email notification for the practice team
- Original local image assets with no third-party image dependency
- Clear information disclaimer and conversion paths

### Client portal

- Registration, secure password hashing and six-digit email verification
- Private access: clients can only view their own cases
- Case stage, visual progress, next action and key date
- Document/evidence checklist with review statuses
- Case timeline and private messages with the advisory team
- Responsive desktop and mobile layout

### Staff workspace

- View and filter all client cases
- Create cases and assign advisers
- Change stage, urgency, key date and next action
- Add and update document checklist items
- Add internal notes that are hidden from clients
- Review consultation enquiries through Django administration

The Django application directory remains named `tickets` so the original database migration history stays safe, but its domain models are now `Case`, `CaseMessage`, `DocumentItem`, `CaseEvent` and `ConsultationRequest`.

## Stack

- Python 3.10+ and Django 5.2 LTS
- SQLite for local development
- PostgreSQL for production
- WhiteNoise for static files
- Gunicorn and Docker for deployment

## Run locally on Windows

```powershell
cd "C:\Users\84783\Documents\New project\flowdesk"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`. The admin site is at `http://127.0.0.1:8000/admin/` and the portal is at `http://127.0.0.1:8000/portal/`.

During local development, verification emails are printed in the PowerShell window running Django. Copy the six-digit code from that output into the verification page. Configure the SMTP variables below for real delivery.

Create an administrator:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Give an existing verified user staff access:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='USERNAME'); u.is_staff=True; u.save()"
```

## Test and verify

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

## Deploy with Docker

1. Install Docker on the server.
2. Copy `.env.example` to `.env` and replace every placeholder.
3. For a public HTTPS domain, set:
   - `ALLOWED_HOSTS=your-domain.example`
   - `CSRF_TRUSTED_ORIGINS=https://your-domain.example`
   - `SECURE_SSL_REDIRECT=True`
   - `SESSION_COOKIE_SECURE=True`
   - `CSRF_COOKIE_SECURE=True`
   - `SECURE_HSTS_SECONDS=31536000` only after HTTPS is confirmed
4. Start the application:

```bash
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
```

Put Caddy, Nginx or the cloud provider’s HTTPS proxy in front of port 8000. Every visitor then uses the same PostgreSQL database and can access the site from desktop or mobile.

## Email delivery

Set these variables for a production SMTP provider:

| Variable | Purpose |
| --- | --- |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` / `EMAIL_PORT` | SMTP server and port |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | Enable one transport mode as required |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP credentials |
| `DEFAULT_FROM_EMAIL` | Verified sender name and address |
| `CONSULTATION_NOTIFICATION_EMAILS` | Comma-separated team inboxes notified of new enquiries |

## Anti-abuse controls

The portfolio deployment uses two lightweight controls that require no third-party CAPTCHA account:

- a hidden honeypot field that discards common automated form submissions;
- server-side limits for consultation submissions and verification/password-reset email requests.

The default limits can be adjusted with:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `CONSULTATION_RATE_LIMIT_COUNT` | `3` | Consultation submissions allowed per source/address window |
| `CONSULTATION_RATE_LIMIT_WINDOW_SECONDS` | `600` | Consultation limit window in seconds |
| `EMAIL_RATE_LIMIT_COUNT` | `5` | Verification/reset requests allowed per source/address window |
| `EMAIL_RATE_LIMIT_WINDOW_SECONDS` | `3600` | Email limit window in seconds |

For a high-traffic production service, replace the file cache with a shared Redis cache and add a managed challenge such as Cloudflare Turnstile.

## Repository safety

The repository intentionally excludes runtime secrets and personal data. Never commit:

- `.env` files or SMTP/application passwords;
- SSH private keys, certificates or deployment archives;
- SQLite databases, PostgreSQL dumps or production user data;
- generated static files and local IDE settings.

Use `.env.example` only as a variable-name template. Store real production values on the server or in a secrets manager.

Before sharing a populated deployment, review the cleanup plan and then apply it:

```bash
python manage.py sanitize_portfolio_data
python manage.py sanitize_portfolio_data --apply
```

The command removes consultation records, cases, client/test accounts, verification records, sessions and administrator activity logs. Staff and superuser accounts are preserved.

## Main routes

- `/` — public home page
- `/services/` — visa pathways
- `/about/` — practice approach
- `/guides/` — editorial guide library
- `/consultation/` — consultation request
- `/signup/` and `/verify-email/` — verified account creation
- `/accounts/login/` — portal login
- `/portal/` — client or staff workspace
- `/admin/` — Django administration
- `/health/` — deployment health check

## Deliberately deferred

Secure file upload/storage, appointment scheduling, payments, real guide article publishing, CRM integration and SMS/chat notifications are not simulated in this version. Those features require provider choices, retention rules and production credentials, so the interface states their current limits rather than pretending they are live.
