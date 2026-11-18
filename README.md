# InkHive: Collaborative Whiteboard

InkHive is a real-time web whiteboard for classes. A **teacher** creates a session and shares a join code or QR code. **Students** join from any browser and watch the board live, and draw when the teacher allows it. The teacher can upload images and files, send announcements, toggle a session chat, save snapshots (PNG/PDF), and review attendance and participation.

*Formerly called COLLABoard. Renamed because COLLABOARD is another company's registered trademark for whiteboard software (see [docs/LEGAL.md](docs/LEGAL.md)).*

**Status:** a portfolio project, not yet online. It is meant to run as a public demo (see [Portfolio demo](#portfolio-demo)).

## Features

* Accounts with roles (student / teacher / admin); log in with username **or** email
* Session management: create, search, duplicate, delete, invite by QR code
* Live whiteboard: pen, eraser, colors, sizes, undo/redo, highlight, pins, clear all
* Per-student drawing permission with online presence and automatic revoke
* Late joiners receive the current board
* Image/file uploads (images go on the board; PDF/DOCX/PPTX as links)
* Announcements, notification bell, session chat with teacher toggle
* Snapshots saved on the server, saved sessions, PNG/PDF export
* Attendance page with CSV export; teacher/student/admin dashboards with charts
* Terms of Service and Privacy Policy with recorded agreement; download my data; delete my account

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript, Chart.js (vendored) |
| Backend | Python 3.11+, Django 5.2 LTS, Django Channels, Daphne (ASGI), WhiteNoise |
| Database | SQLite (PostgreSQL optional via `DATABASE_URL`) |
| Realtime | WebSockets via Django Channels (broadcast and presence), no external service |
| File storage | Local `media/` folder served by the app |
| Hosting | Render |

## Documentation

Full project documentation lives in [`docs/`](docs/README.md):

| | |
|---|---|
| [PRD](docs/PRD.md): Product Requirements | [SRS](docs/SRS.md): Software Requirements Specification |
| [SDD](docs/SDD.md): Software Design Document | [TRD](docs/TRD.md): Technical Requirements |
| [App Flow](docs/APP_FLOW.md) | [UI/UX Design Brief](docs/UI_UX_DESIGN_BRIEF.md) |
| [Backend Schema](docs/BACKEND_SCHEMA.md): ERD, API, realtime protocol | [Implementation Plan](docs/IMPLEMENTATION_PLAN.md): fix log, roadmap, test plan |
| [Legal & Privacy](docs/LEGAL.md): terms, privacy, data rights, legal launch to-do | [Third-party notices](THIRD_PARTY_NOTICES.md) |

## Getting started

### 1. Clone

```bash
git clone https://github.com/thatguyKire/InkHive.git
cd InkHive
```

### 2. Create a virtual environment and install dependencies

```bash
# macOS / Linux
python3 -m venv env
source env/bin/activate

# Windows (PowerShell)
python -m venv env
.\env\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Configure (optional for local development)

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Nothing is required for local development: the app uses SQLite (`db.sqlite3`) and stores uploads and snapshots in `media/`. Live sync works out of the box. See [TRD §3](docs/TRD.md#3-configuration-environment-variables) for all settings.

### 4. Set up the database

```bash
python manage.py migrate
python manage.py createsuperuser   # optional: admin account (role = admin)
```

### 5. Run

```bash
python manage.py runserver
```

`runserver` uses Daphne, so WebSockets (live drawing) work in development too. Open http://127.0.0.1:8000, sign up as a teacher in one browser and as a student in another (or a private window).

## Running tests

```bash
python manage.py test modules
```

The suite (127 tests) covers the portfolio demo mode, authentication, sessions, access control, the whiteboard APIs and WebSocket consumer, uploads, snapshots/PDF, chat, notifications, dashboards, 29 security attack tests, and the legal features (terms agreement, data download, account deletion, backup retention).

## Security

See **[SECURITY.md](SECURITY.md)** for the threat model, every security control, and the **pre-launch checklist that must be completed before the site goes live**.

## Legal and privacy

The app has a [Terms of Service](modules/legal/templates/legal/terms.html) and [Privacy Policy](modules/legal/templates/legal/privacy.html) (Philippine Data Privacy Act of 2012) at `/legal/terms/` and `/legal/privacy/`. Users must agree at sign-up, and again whenever `TERMS_VERSION` changes. They can download their data or delete their account in Settings. **Before a public launch, finish the team to-do in [docs/LEGAL.md](docs/LEGAL.md#3-before-launch-team-to-do)**.

The name lives in one place: `SITE_NAME` in `collaborative_whiteboard_backend/settings.py` (templates use `{{ brand_name }}`). The logo (`modules/core/static/core/icons/logo.svg`, a bee whose stinger is a pen nib writing a line of ink) has no text in it. All icons and the logo were drawn for this project ([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

## Project structure

```
collaborative_whiteboard_backend/   Django settings, root URLs, WSGI/ASGI
modules/
  authentication/   custom user, signup/login, email-or-username backend, roles
  core/             base layout, landing, media serving, realtime.js client, shared decorators, test helpers
  dashboard/        student / teacher / admin dashboards
  session/          sessions, participants, whiteboard pages + APIs, WebSocket consumer, uploads, attendance
  chat/             session chat rooms and messages
  notifications/    notifications, announcements, bell
  profiles/         profile and email edit
  settings_app/     settings hub, password change
  help_app/         FAQ page
  legal/            Terms of Service, Privacy Policy, terms-acceptance gate
  demo/             portfolio demo mode: one-click demo accounts, daily reset
docs/               PRD, SRS, SDD, TRD, app flow, UI/UX brief, schema, plan
build.sh            Render build script
```

## Portfolio demo

Set `DEMO_MODE=True` and the login page gets **Try as a teacher** / **Try as a student** buttons, so visitors can try the app without signing up:

* Visitors share three demo accounts (`demo_teacher`, `demo_student`, `demo_classmate`) and start in a sample class with a chat message and an announcement.
* Sign-up is turned off. The demo accounts have no password, and can't change their email or delete themselves, so one visitor can't lock the others out.
* Every page shows a banner asking visitors not to enter personal information, and the Terms and Privacy Policy explain the demo.
* Everything the demo accounts make (boards, uploads, chat) is deleted once a day, the next time someone starts the demo. `python manage.py seed_demo --reset` does it by hand.
* Your own accounts (for example the admin) are never touched.

On Render's **free** plan you need no disk. The database lives on the temporary filesystem, so it also resets whenever the free server goes to sleep, which suits a demo. Set `SECRET_KEY` and `DEMO_MODE=True`, and use this start command so the database is created again after each restart:

```bash
python manage.py migrate --noinput && daphne -b 0.0.0.0 -p $PORT collaborative_whiteboard_backend.asgi:application
```

## Deployment (Render)

* **Build command:** `./build.sh` (installs packages, runs migrations, collects static files)
* **Start command:** `daphne -b 0.0.0.0 -p $PORT collaborative_whiteboard_backend.asgi:application` (Daphne is required for WebSockets; Gunicorn/WSGI would serve pages but no live sync)
* **Persistent disk:** SQLite and uploads are files. Without a disk, Render wipes them on every deploy/restart. Add a disk (e.g., mounted at `/var/data`) and set `SQLITE_PATH=/var/data/db.sqlite3` and `MEDIA_ROOT=/var/data/media`
* **Environment:** the variables from `.env.example`; set `SECRET_KEY`; `DEBUG` defaults to `False` on Render
* Run a **single instance** (the realtime layer lives in process memory)
* **Backups:** Render snapshots the disk daily. For extra copies, run `python manage.py backup` (Render Shell); it saves the database and `media/` to `BACKUP_DIR` (e.g. `/var/data/backups`) and deletes copies older than 30 days, as the Privacy Policy promises

## Team

- Bien, Erik Samuel Legaspi | Lead Developer | eriksamuel.bien@cit.edu
- Beato, Angel Anel Celaya | Developer | angelanel.beato@cit.edu
- Bibit, Paul Andrei Eco | Developer | paulandrie.bibit@cit.edu
