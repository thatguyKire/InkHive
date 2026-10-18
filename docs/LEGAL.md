# Legal and Privacy

**System:** COLLABoard: Collaborative Whiteboard · **Date:** 2026-10-18 · **Terms version:** `2026-10-18`

This document lists what the app does to stay on the right side of the law, what personal data it holds, and the **items the team must finish before real users are let in**. It goes with [SECURITY.md](../SECURITY.md).

> **Not legal advice.** The Terms of Service and Privacy Policy were written by the development team as a sensible starting point for a free student project in the Philippines. Have your course adviser and, if the app will be used in real classes, your school's Data Protection Officer review them before launch.

---

## 1. What is in place

| Item | Where | Why it matters |
|---|---|---|
| **Terms of Service** at `/legal/terms/` | `modules/legal/templates/legal/terms.html` | Rules of use, content ownership and licence, "as is" disclaimer, ₱1,000 liability cap, copyright/abuse reporting, Philippine law and Cebu City courts |
| **Privacy Policy** at `/legal/privacy/` | `modules/legal/templates/legal/privacy.html` | Notice required by the Data Privacy Act of 2012 (RA 10173): what is collected, why, who sees it, retention, rights, NPC complaint route |
| **Clickwrap agreement at sign-up**: required checkbox (with an 18+/guardian statement); version and time stored on the user | `authentication/forms.py`, `CustomUser.terms_version` / `terms_accepted_at` | A recorded, affirmative "I agree" is what makes terms enforceable; a link in a footer is not enough |
| **Existing users must accept** before using the app (accounts made before the terms, or after they change) | `modules/legal/middleware.py`, `/legal/accept/` | Covers everyone who signed up before this release |
| **Download my data** (JSON) | Settings → Download my data · `/settings/export/` | Right to access and data portability |
| **Delete account** (password + confirmation, rate-limited) | Settings → Delete account · `/settings/delete-account/` | Right to erasure; deletes owned sessions, uploads, messages, notifications **and the files on disk** |
| **Deleting a session deletes its files** (snapshots shared with a duplicate are kept until the last user is gone) | `modules/session/storage.py` | The Privacy Policy promises deleted data is really gone |
| Only strictly necessary cookies (`sessionid`, `csrftoken`); no analytics, ads, trackers or third-party scripts/fonts | CSP in `core/middleware/security_headers.py` | No cookie-consent banner is needed for strictly necessary cookies |
| "Not an official service of CIT-U" notice | legal pages footer, Terms §1 | Avoids implying the university runs or endorses the app |
| Third-party code licences recorded; unlicensed assets removed | [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) | The background texture (unclear licence) is now drawn in CSS; the Gmail logo on the Help page was replaced by our own envelope icon |
| Contact address for privacy, copyright and abuse reports | `CONTACT_EMAIL` setting (default `COLLABoardDevTeam@gmail.com`) | Shown on the legal and Help pages |

Tests: `modules/legal/tests.py` (19 tests: public pages, signup agreement, the accept gate, data export, account deletion with files, session file cleanup).

## 2. Personal data inventory

| Data | Stored in | Who can see it | Kept until |
|---|---|---|---|
| Username, email, role, student ID, password hash, join/login dates, terms version | `authentication_customuser` | The user; teachers see username + email of their participants; admins | Account deleted |
| Session membership, join time, last active, `can_draw`, stroke/upload counts | `session_participant` | The user; the session's teacher (attendance page + CSV); admins | Session or account deleted |
| Drawings | Browser memory during a session; snapshots in `media/snapshots/` | Session members | Session deleted |
| Uploaded files | `media/session_files/<session>/` + `session_uploadedfile` | Session members | Session or uploader deleted |
| Chat messages | `chat_message` | Session members | Session or sender deleted |
| Announcements / notifications | `notifications_notification` | Recipient | Recipient deleted, or the teacher's account deleted |
| IP address | In-memory rate-limit counters | Nobody (code only) | ≤ 1 hour |
| Failed/blocked login (typed username or email + IP), security events | Server logs (stdout → Render) | Team members with Render access | Render's log retention |

No sensitive personal information (health, religion, government IDs …) is requested. Data is hosted by Render (possibly outside the Philippines).

## 3. Before launch: team to-do

| # | Task | Owner | Why |
|---|---|---|---|
| L-1 | ☐ **Rename the app before any public launch.** "COLLABOARD" is a registered US trademark (Reg. No. 5505406, serial 79213521) of IBV Informatik AG for collaboration software, and they sell a product called *Collaboard* that is also an online whiteboard. Using the same name for the same kind of product is the clearest lawsuit risk in this project. Keeping the name for a class demo is low risk; publishing it as a real service is not. | Team | Trademark infringement |
| L-2 | ☐ Get written OK from the course adviser and, before using it with real classes, from CIT-U's Data Protection Officer. Student data handled for a class can make the school responsible too. | Lead | Data Privacy Act, school policy |
| L-3 | ☐ Have the adviser (or a lawyer, if the app goes beyond the course) review the Terms and Privacy Policy. | Lead | Not legal advice |
| L-4 | ☐ Make sure `CONTACT_EMAIL` is an inbox someone checks at least weekly. Privacy requests: answer within 15 days (we promise this). | Team | Promised in the Privacy Policy |
| L-5 | ☐ Confirm who made every icon in `modules/*/static/**/icons/` and the logo. If any came from a site such as Flaticon, Freepik or Icons8, follow its licence (often an attribution link) or replace it, and record it in THIRD_PARTY_NOTICES.md. | Front-end | Copyright |
| L-6 | ☐ Keep backups of `db.sqlite3` and `media/` for **at most 30 days** (the Privacy Policy promises this). | DevOps | Promised retention |
| L-7 | ☐ Decide who the Data Protection Officer is (the Privacy Policy says the lead developer) and make sure that person knows the breach steps in §5. | Lead | RA 10173 |
| L-8 | ☐ Choose a licence for the source code (e.g. MIT) or keep "all rights reserved", and agree on it as a team. All three members hold copyright in the code they wrote. | Team | Clarity for reuse; optional |

## 4. Changing the Terms or Privacy Policy

1. Edit `modules/legal/templates/legal/terms.html` and/or `privacy.html`.
2. If users should agree again (anything that changes their rights or how data is used), set `TERMS_VERSION` in `collaborative_whiteboard_backend/settings.py` to today's date (`YYYY-MM-DD`). The pages show it as the effective date.
3. Deploy. On their next visit every user sees "We've updated our terms" and must accept before continuing.
4. If you change what is collected, exported or deleted, update `modules/settings_app/account.py` and §2 above so the policy stays true.

## 5. Handling reports

**Copyright or abuse report** (to `CONTACT_EMAIL`):
1. Reply within a few days to say it was received.
2. Find the content (session title or code, time). Admins can see everything in the Django admin.
3. If it infringes or breaks the Terms, delete it (or the session) and tell the reporter. Warn the user; suspend repeat offenders (`is_active = False` in the admin).
4. Content that sexualises a minor: do not download or share it; preserve the record and report it to the PNP Women and Children Protection Center or the NBI, then remove it.

**Privacy request** (access, correction, deletion, objection):
1. Confirm the request comes from the account's email address.
2. Most requests are self-service (Download my data, edit email, Delete account); point the user there or do it for them in the admin.
3. Answer within 15 days.

**Personal data breach** (for example, someone downloaded other users' data):
1. Contain it: suspend the Render service, rotate `SECRET_KEY` (logs everyone out), change admin passwords.
2. Write down what happened, what data and how many people are affected, and when you found out.
3. If the breach is likely to put people at risk, notify the **National Privacy Commission** and the affected users promptly. The NPC's rules set a short deadline (counted in hours from discovery), so check the current NPC circular on breach management right away.
4. Fix the cause before going back online.
