# Candidate Assessment Platform — UI/UX Design Brief

**Purpose of this document:** a complete, self-contained brief for a UI/UX designer to redesign the interface of an existing, fully-functional web application. Every screen, state, flow, and piece of on-screen copy currently in the product is documented here. The designer does **not** need access to the codebase.

**Current state, honestly:** the application is **feature-complete and working**, but the UI is **unstyled and utilitarian** — browser-default form controls, ad-hoc inline colours, no header/navigation chrome, no visual hierarchy, no brand. It was built function-first. This brief is the input to making it look and feel like a real product.

**What we want back from the designer:** see [§13 Deliverables](#13-deliverables-requested). In short: high-fidelity mockups for every screen and state, a small design-token system (colours, type, spacing, radius, shadow, in light and — optionally — dark mode), and component specs we can implement in React.

---

## 1. What the product is

A small, single-purpose internal web app that runs a **recruitment assessment** for a handful of pre-invited candidates. It is used by:

- **~15 candidates** — each logs in, books one assessment slot, and (a fixed number of days before their slot) unlocks a downloadable exercise brief + data files + their own API key. They can privately ask the assessor questions.
- **1 administrator** (the assessor) — manages candidate accounts, time slots, content, questions, and configuration.

It is **low-traffic and internal**. Correctness, clarity, trust, and data protection matter far more than performance or scale.

**A defining product value — radical data minimisation.** The app deliberately stores almost nothing about a candidate: **only their first name** plus a system ID like `cand-07`. No email, no surname, no phone, no tracking, no analytics. This is a genuine differentiator and an emotional reassurance for candidates — **the design should lean into it**, not bury it on a legal page.

---

## 2. Goals of the redesign

1. **Make the candidate experience feel like a considered, premium recruitment touchpoint** — calm, confident, reassuring, professional. A candidate's first impression of the hiring organisation runs through this UI.
2. **Make the admin experience efficient and scannable** — dense, fast, status-at-a-glance. It can be plainer than the candidate side, but it should still be clean and modern, not raw HTML.
3. **Give the product a coherent visual system** — typography, colour, spacing, components — instead of 12 pages each styled by hand.
4. **Design every state**, not just the happy path: loading, empty, error, success, disabled, and the important conditional states (locked vs unlocked, answered vs awaiting, booked vs not).
5. **Treat the few "moment" interactions as features**: the unlock countdown, the gated API-key reveal, the prep-window trade-off preview, and the destructive purge confirmation.

**Design asymmetry (important):** the **candidate-facing** side should feel polished and brand-led; the **admin** side should feel like a competent internal tool (think a clean dashboard, not a marketing site). Invest visual effort accordingly.

---

## 3. Personas

### Candidate ("the applicant")
- Pre-invited; received a one-time set-password link and a login URL **by email, sent manually by the assessor** (the app never emails).
- Goals: set a password, log in, book a slot that gives them enough prep time, understand when their materials unlock, download them, retrieve their API key, ask the occasional question.
- Emotional state: this is a job assessment — they may be anxious. The UI should **reduce anxiety**: be clear about what happens and when, never ambiguous, never alarming.
- Likely on **desktop or laptop** primarily (it's a technical exercise), but should be **responsive** and usable on a phone for checking status/booking.

### Administrator ("the assessor")
- One person. Power user. Spends short, focused sessions managing candidates.
- Goals: create candidates and hand out invite links, manage slots, paste API keys, answer questions, monitor who's done what, adjust config, and (at end of process) purge all candidate data.
- Wants **density and speed**: tables, queues, inline actions, clear status. Less hand-holding.

---

## 4. Brand & visual direction

**There is no brand applied yet.** The designer should either apply the hiring organisation's brand (if assets are provided — see [§14 Open questions](#14-open-questions)) or propose a clean, trustworthy, modern direction.

**Tone words:** considered · trustworthy · calm · precise · human (it's explicitly *not* a chatbot — a real person answers questions). Avoid: playful/gimmicky, aggressive, "growth-hacky", or anything that undercuts the data-protection seriousness.

**Existing token scaffold (starting point, not a mandate).** The codebase already declares CSS custom properties in light & dark mode that we can map a new system onto:

| Token | Current light value | Role |
|---|---|---|
| `--text` | `#6b6375` | body text |
| `--text-h` | `#08060d` | headings |
| `--bg` | `#fff` | background |
| `--border` | `#e5e4e7` | borders/dividers |
| `--code-bg` | `#f4f3ec` | code / monospace chips |
| `--accent` | `#aa3bff` (purple) | primary accent |
| `--accent-bg` / `--accent-border` | purple tints | accent surfaces |
| `--shadow` | layered soft shadow | elevation |
| Font (sans/heading) | `system-ui, 'Segoe UI', Roboto, sans-serif` | — |
| Font (mono) | `ui-monospace, Consolas, monospace` | IDs, keys, code |

These are **defined but currently unused** by the pages (pages hardcode colours inline). The designer should **define the real palette/type/spacing as tokens**; we will wire every component to them on rebuild. The purple accent and the dark-mode support are inherited defaults — feel free to replace them. Decide explicitly whether **dark mode** is in scope.

**Current ad-hoc colours in use** (so you know what's there to rationalise): error `red`, success `green`/`#28a745`, info-blue banner `#e8f4fd`/`#1a4a6e`, warning-amber `#fff3cd`/`#856404`, answered-green `#4caf50`/`#e8f5e9`, danger-red `#c0392b`/`#e53e3e`, neutral greys `#555/#666/#888/#f0f0f0`.

---

## 5. Design principles & constraints

- **Accessibility: WCAG 2.1 AA.** Sufficient colour contrast, visible focus states, real labels on every input (many inputs currently use placeholders *instead of* labels — fix this), keyboard operability, `aria` roles for alerts. Don't rely on colour alone to convey state (e.g. answered/awaiting needs an icon or text, not just green/amber).
- **Responsive.** Design at least: desktop (~1126px content column today), tablet, and mobile. Tables on the admin side need a responsive strategy (horizontal scroll is acceptable for the activity matrix; the questions queue should reflow).
- **Honest, low-anxiety UX.** No dark patterns. The prep-window trade-off must be shown truthfully (a candidate booking late genuinely gets less prep time — say so plainly). The destructive purge must feel appropriately serious.
- **Implementation reality.** We rebuild in **React (Vite + TypeScript)**. Prefer a **lightweight** styling approach — CSS variables + plain CSS/CSS-modules, or Tailwind — over a heavy component library. Custom components are fine; please provide enough spec (states, spacing, variants) to build them. Keep new runtime dependencies minimal.
- **Microcopy.** Existing copy is captured in [§11](#11-microcopy-library). You may refine wording for tone, but preserve the *meaning* (especially legal/privacy and the exact purge confirmation phrase).

---

## 6. Information architecture & navigation

There is currently **no navigation chrome** — no header, no logo, no role-aware nav. Admin pages link to each other via a plain text row; candidate pages have ad-hoc links. **Designing the global shell (header/nav/footer, per role) is part of this work.**

### Sitemap

**Public**
- `/privacy` — Privacy notice
- `/login` — Candidate login (also the catch-all/default route)
- `/set-password?token=…` — Set password from an invite/reset link
- `/admin/login` — Admin login

**Candidate (after login)**
- `/dashboard` — Home: booking status, countdown, downloads, API key
- `/book` — Book an assessment slot
- `/questions` — Ask the assessor / view Q&A thread

**Admin (after login)**
- `/admin` — Candidates (list, create, account management, API keys)
- `/admin/slots` — Manage slots & bookings
- `/admin/questions` — Questions queue (answer)
- `/admin/activity` — Activity / monitoring overview
- `/admin/config` — Settings & data (config + destructive purge)

### Navigation needs
- **Candidate:** a simple, calm top bar — logo/wordmark, and (when logged in) links to Dashboard / Book / Questions, plus Log out. Footer keeps the **Privacy** link.
- **Admin:** a persistent admin nav (sidebar or top bar) across the 5 admin pages: Candidates · Slots · Questions · Activity · Settings & data, plus Log out and a clear "you are admin" indicator.
- Consider a visible **logged-in identity** (candidate first name / "Admin") and an unobtrusive **session/Log-out** control.

---

## 7. Global / cross-cutting elements to design

These recur across screens — design them once as a system:

1. **App shell** — header/nav (per role), content container, footer.
2. **Buttons** — primary, secondary, and **destructive** variants; default / hover / focus / disabled / busy ("Saving…", "Booking…", "Purging…") states. (Today every button is a browser-default button.)
3. **Form controls** — text, password, number, date, datetime-local, textarea; with **real labels**, helper text, and inline validation error styling.
4. **Inline feedback** — success (green), error (red `role="alert"`), and an empty/muted state. Consider a lightweight toast/inline-confirmation pattern for save actions.
5. **Status badges/pills** — candidate status (`invited` / `active` / `disabled`); question status (`Awaiting answer` / answered); slot status (`Open (n/cap)` / `Booked by …`); boolean ticks (✓ / —) in the activity matrix.
6. **Cards** — question cards (candidate + admin), preview/info boxes.
7. **Tables** — slots table, activity matrix (wide, many columns), with a responsive strategy.
8. **Banners / notices** — info (the Q&A "human-answered" banner), warning, and a strong **danger** treatment for the purge zone.
9. **Code/credential chips** — monospace display for `cand-07` IDs, set-password URLs (click-to-copy), and the revealed API key (masked, show/hide, copy).
10. **The Countdown** — a focal, reassuring countdown component (see §8).
11. **Loading & empty states** — consistent skeleton/spinner and friendly empty messages (today it's bare "Loading…").

---

## 8. "Moment" interactions (design these with extra care)

These are the emotionally and functionally important interactions:

- **Prep-window preview (booking).** Before a candidate confirms a slot, they see a plain-language sentence stating the exact unlock date and how many prep days they'll get — and crucially, **booking a slot fewer than N days away gives less prep time, shown honestly**. This trade-off is the core decision the candidate makes; make it legible and calm (e.g. a small timeline/visual could help them compare slots, not just a sentence).
- **The lock → countdown → unlock journey (dashboard).** After booking, a candidate is *locked* until their unlock moment. They see a **live countdown** ("3d 4h 12m 09s"). When it hits zero, the page **self-reveals** the downloads + API key with no manual refresh. This is a delightful, anticipation-building moment — design the locked state, the countdown, and the celebratory unlock reveal.
- **Gated API-key reveal.** Once unlocked, the candidate clicks "Reveal API key"; the key shows **masked by default** with show/hide and copy, plus a usage note. Treat the key as a credential — secure, deliberate, not splashed on screen by default.
- **Destructive purge (admin).** "Purge all candidate data" requires typing the exact phrase `PURGE ALL CANDIDATE DATA`; the button stays disabled until it matches, then a browser confirm fires. This must look unmistakably dangerous and final, and clearly list what is deleted vs kept.

---

## 9. Screen-by-screen specification

For each screen: its purpose, who sees it, the content/elements that must be present, and the states to design. On-screen copy in quotes is the **current** wording (refine for tone, preserve meaning).

### 9.1 Candidate Login — `/login` (public; also the default route)
- **Purpose:** candidate logs in with their candidate ID + password.
- **Content:** heading "Candidate login"; **Candidate ID** field (currently placeholder "candidate ID", needs a real label + help text e.g. "the ID your assessor sent you, like `cand-07`"); **Password** field; "Log in" button. Link to set-password? (only via emailed link). 
- **States:** default; submitting (button busy); error (`role="alert"`, e.g. invalid credentials / disabled account). 
- **Notes:** this is many candidates' first impression — give it warmth and a sense of the organisation. Consider a brief reassuring line about the process.

### 9.2 Set Password — `/set-password?token=…` (public, from emailed link)
- **Purpose:** candidate sets their password using a one-time token in the URL.
- **Content:** heading "Set password"; **New password** field (add a confirm field and/or strength/criteria guidance — currently single field, no rules shown); "Set password" button. On success → go to login.
- **States:** default; submitting; error (invalid/expired token — design a clear "this link has expired, ask your assessor for a new one" message); success → redirect to login (consider a brief success confirmation).

### 9.3 Admin Login — `/admin/login` (public)
- **Purpose:** the single admin logs in (username + password).
- **Content:** heading "Admin login"; **Username** + **Password** fields (need labels); "Log in" button; error alert.
- **States:** default; submitting; error. Visually distinct enough that an admin knows they're on the admin entry (but it's not secret).

### 9.4 Candidate Dashboard — `/dashboard` (candidate home)
The most important candidate screen. It has **three major conditional states** plus shared chrome.

- **Shared:** heading/welcome (currently just "Welcome" — personalise with first name); link "Ask the assessor a question" → `/questions`; "Log out".
- **State A — No booking yet:** a clear call-to-action "Book your assessment" → `/book`. Make this prominent; it's the candidate's next step.
- **State B — Booked, locked (before unlock):**
  - "Your assessment is scheduled for **{date/time}**."
  - "Your exercise data unlocks in: **{live countdown}**" — design the countdown as a focal, calming element. Communicate clearly that they don't need to do anything until then.
- **State C — Booked, unlocked:**
  - "Your exercise data is now unlocked. Good luck!" (celebratory but composed)
  - **Download area** (see §9.4a)
  - **API key section** (see §9.4b)
- **Loading state** while booking status loads; **error state** if it fails.

#### 9.4a Download area (within unlocked dashboard)
- Heading "Assessment Files". Files **grouped by category** with headings: "Brief", "Data Files", "Reference Material".
- Each file is a download link labelled with a human title. Note one data file (20-year wind data) is **large** — consider showing file type/size hints and a clear "downloading" affordance.
- **States:** loading ("Loading files…"); error ("Could not load files: …"); empty ("No files available yet.").

#### 9.4b API key section (within unlocked dashboard)
- Heading "Your API Key". Before reveal: a **"Reveal API key"** button (deliberate action, not auto-shown).
- After reveal: the key in a **monospace, read-only field, masked by default**, with **Show/Hide** and **Copy** ("Copied!" feedback), plus a usage note (server-provided text about budget/spend).
- **States:** not-yet-revealed; loading ("Loading…"); revealed (masked/shown); **no key yet** ("Your assessor hasn't added your API key yet." + "Try again"); error.
- **Design intent:** make it feel like handling a secret — secure, calm, with copy affordance front-and-centre once revealed.

### 9.5 Candidate Booking — `/book`
- **Purpose:** pick one open slot and confirm, with full information about the prep-time trade-off.
- **Content:**
  - Heading "Book your assessment slot".
  - **List of open slots** (each a selectable item showing date/time). Currently a list of buttons; design a clear selectable list/cards with the selected one emphasised.
  - **On selection — the prep-window preview** (a box): a sentence, one of two variants:
    - immediate: "If you choose this slot, your exercise data unlocks **immediately**, giving you **{N} days** to work on it before your assessment on **{date}**."
    - future: "If you choose this slot, your exercise data unlocks on **{unlock date}**, giving you **{N} days** to work on it before your assessment on **{assessment date}**."
  - **"Confirm"** button (busy state "Booking…").
- **States:** loading; **empty** ("No slots currently available."); **already-booked** (heading "Already booked", "You already have an assessment booking.", link to dashboard — a candidate gets one booking only); load error; **booking conflict** error (if a slot was just taken — "that slot was just taken, please pick another", list refreshes).
- **Design opportunity:** help the candidate **compare** slots on prep-time, not just pick blindly. A small visual (timeline: today → unlock → assessment, with prep-days highlighted) would make the trade-off intuitive. The honesty here is a feature.

### 9.6 Candidate Q&A — `/questions`
- **Purpose:** ask the assessor private questions; see your own thread. **Strictly private** — a candidate only ever sees their own questions.
- **Content:**
  - Back link to dashboard; heading "Ask the Assessor".
  - **"Human-answered" info banner** — reassures that a real person answers (currently light-blue banner: "**Human-answered:** {SLA text}", e.g. "Questions are answered by a person, usually within 1 working day."). This banner is important: it sets the expectation that this is **not a chatbot**. Design it to feel human and credible.
  - **Question form:** labelled textarea ("Your question", placeholder "Type your question here…"), "Send question" button (busy "Sending…"; disabled when empty).
  - **Thread:** "Your questions" — each question card shows the question, "Asked {date}", and either the **answer** (with "Answered {date}") or an **"Awaiting answer"** badge.
- **States:** submitting; submit error; thread loading; **empty** ("No questions yet. Ask one above."); load error; answered vs awaiting per item.

### 9.7 Privacy — `/privacy` (public)
- **Purpose:** plain-language privacy notice (linked from the footer).
- **Content:** heading "Privacy notice" + three short paragraphs (verbatim in §11) covering: *only first name + system ID stored*; *no email/surname/phone/analytics/marketing, one essential cookie, no consent banner needed*; *held only for the assessment then deleted, erasure on request*.
- **Design intent:** this is a chance to **make the data-minimisation story a brand asset** — clear, confident, even reassuring, rather than dense legalese. Consider iconography (e.g. "what we store" vs "what we don't").

### 9.8 Admin Dashboard / Candidates — `/admin`
- **Purpose:** the admin's home — list candidates, create them, manage their accounts and API keys.
- **Content:**
  - Heading "Candidates"; the admin nav (to Slots / Questions / Activity / Settings & data).
  - **Create candidate:** a "first name" input + "Create" button.
  - **Candidate list** — currently a raw `<ul>` of `"{cand-id} — {first name} — {status}"`. Redesign as a **table or card list** showing: candidate ID (mono chip), first name, **status badge** (`invited`/`active`/`disabled`), and inline controls:
    - **Set API key** (password input + "Save"; success "Key saved.") — write-only, never shows the stored key.
    - **Account controls:** "Reset password" and (for invited) "Re-issue invite" — both return a **one-time set-password link** to copy and email manually (shown as a click-to-copy mono URL); "Disable"/"Enable" toggle.
    - When a candidate is `invited`, their set-password link is shown for the admin to copy.
- **States:** the list should have a **loading** and **empty** state (currently neither exists — load errors are silently swallowed; please design both, and an error state). Per-row busy/disabled while an action runs; per-row success/error messages.
- **Design intent:** dense, scannable management table; the "copy this invite link to email the candidate" action should be obvious (since the app sends no email, this is the admin's core workflow).

### 9.9 Admin Slots — `/admin/slots`
- **Purpose:** create/edit/delete slots and manage bookings.
- **Content:**
  - Heading "Manage Slots"; back to admin.
  - **Create Slot:** Date/Time (`datetime-local`) + Capacity (number, default 1) + "Create".
  - **Slots table** — columns: ID, Starts At, Capacity, **Status**, Actions.
    - Status: "Open (n/cap)" or "Booked by {candidate IDs}".
    - Actions for **unbooked** slots: Edit (inline edit of time/capacity → Save/Cancel) and Delete.
    - Actions for **booked** slots: per booking, show "{candidate ID} ({first name})" with a "New slot ID" input + **Reassign** and **Release**. (Booked slots can't be deleted/edited until released/reassigned — communicate this constraint clearly, e.g. disabled Delete with a tooltip.)
  - Per-row error display (e.g. "slot is booked; reassign or release first").
- **States:** empty ("No slots yet."); per-row editing; per-row busy; per-row error.
- **Design note:** the reassign control (typing a target slot ID) is clunky — a designer could propose a better pattern (e.g. a dropdown of open slots). Flagging as an improvement opportunity.

### 9.10 Admin Questions Queue — `/admin/questions`
- **Purpose:** the assessor answers candidate questions. **Unanswered first.**
- **Content:**
  - Back to admin; heading "Questions Queue".
  - **Unanswered section** — heading "Unanswered" with a **red count badge**; each question in a red-bordered card showing asker (first name + `cand-id` chip), "asked {date}", the question body, and an inline **answer textarea** + "Save" (busy "Saving…", disabled when empty).
  - **Answered section** — heading "Answered"; grey cards with the question and a green **Answer** box ("answered {date}").
- **States:** loading; error; empty for each section ("No unanswered questions." / "No answered questions yet.").
- **Design intent:** a triage queue — the assessor should immediately see how many need attention and answer quickly inline. Make the unanswered count and cards prominent.

### 9.11 Admin Activity Overview — `/admin/activity`
- **Purpose:** an at-a-glance monitoring matrix of every candidate's progress (fairness/audit view).
- **Content:** a **wide table**, one row per candidate. Columns: Candidate (name + `cand-id`), Status, Booked Slot, Unlock At, **Logged In** (✓/—), **one column per content file** (✓/— = downloaded or not), **Key Revealed** (✓/—), **#Questions**.
- **States:** loading; error; empty ("No activity data.").
- **Design challenge:** this is the widest screen — many file columns. Design a **responsive/scrollable matrix** that stays readable (sticky first column, clear tick/cross treatment that isn't colour-only, compact density). This is a power-user monitoring tool; prioritise scannability.

### 9.12 Admin Settings & Data — `/admin/config`
Two distinct zones with very different emotional weight.

- **Configuration zone** ("Configuration"): four settings, each with its own labelled input + Save (busy "Saving…") + inline success/error:
  - **Prep window (days)** — number.
  - **Retention reminder date** — date, with the helper text "Retention reminder — NOT enforced; the system never auto-deletes. Leave blank to keep unset." + a "Clear" button. (This is a manual reminder only — never triggers deletion. Make that unambiguous.)
  - **Q&A SLA text** — textarea (this is the text shown in the candidate Q&A banner).
  - **Display timezone** — text (e.g. "Europe/London").
- **Danger zone** ("Danger zone — Purge all candidate data"): a strongly-treated, visually-separated red section:
  - A clear list of **what is deleted** ("All candidates", "All bookings", "All candidate questions", "All download events", "All candidate audit rows") and **what is kept** ("admin account, config, slots, admin audit log").
  - If a retention date is set, show it as a reminder; if not, a muted note.
  - A confirmation input: "To confirm, type exactly: `PURGE ALL CANDIDATE DATA`". The **purge button stays disabled** (greyed) until the typed text exactly matches, then turns red/active; clicking also fires a browser confirm ("This will permanently delete all candidate data. This cannot be undone. Proceed?").
  - **Post-purge success panel** listing the deleted record counts; and a purge **error** state.
- **States:** loading; load error; per-field saving/success/error; purge disabled vs armed; purge success; purge error.
- **Design intent:** the config zone should feel routine and safe; the danger zone should feel **serious and final** — unmistakably different from everything else in the app.

---

## 10. Cross-cutting states checklist (design all of these)

For the system and each relevant screen:
- **Loading** (initial fetch) — replace bare "Loading…" with a consistent skeleton/spinner.
- **Empty** — friendly, instructive empty states (several exist; some are missing, e.g. admin candidate list).
- **Error** — inline `role="alert"` styling; distinguish validation (422) from auth (401/403) from server errors.
- **Success** — save confirmations (currently terse green text); consider a consistent toast/inline pattern.
- **Disabled / busy** — buttons during async actions ("Saving…", "Booking…", "Sending…", "Purging…").
- **Conditional content** — locked/unlocked (dashboard), booked/not (booking), answered/awaiting (Q&A), open/booked (slots), invited/active/disabled (accounts).

---

## 11. Microcopy library (current strings — refine tone, preserve meaning)

**Privacy notice (3 paragraphs, verbatim — legal meaning must be preserved):**
1. "This assessment platform deliberately holds the minimum personal data. About you we store only your **first name** and a system-generated ID (e.g. `cand-07`), together with your assessment booking, file downloads, questions you ask, and an Anthropic API key stored **encrypted**."
2. "We do **not** store your email, surname, phone number, IP-based analytics, or any marketing data. We use a single essential session cookie to keep you logged in; it is removed when you log out or it expires. Because it is strictly necessary, no cookie-consent banner is required."
3. "Your data is held only for the duration of the assessment process and is then permanently deleted. You may ask the assessor to erase your data at any time."

**Q&A banner:** "**Human-answered:** {SLA text}" — default SLA text: "Questions are answered by a person, usually within 1 working day."

**Booking preview (two variants):**
- "If you choose this slot, your exercise data unlocks immediately, giving you **{prep_days} days** to work on it before your assessment on **{assessment date}**."
- "If you choose this slot, your exercise data unlocks on **{unlock date}**, giving you **{prep_days} days** to work on it before your assessment on **{assessment date}**."

**Dashboard:** "Your assessment is scheduled for **{date}**." · "Your exercise data unlocks in: {countdown}" · "Your exercise data is now unlocked. Good luck!" · "Book your assessment" · "Ask the assessor a question" · "Log out"

**Countdown expiry:** "Unlocking your data…" (+ Refresh button)

**API key:** "Reveal API key" · "Your assessor hasn't added your API key yet." · "Try again" · "Show"/"Hide" · "Copy"/"Copied!" · usage note (server-provided, e.g. "This key is for the LLM features your application uses at runtime. It has a fixed budget; track your own spend from the token usage returned in API responses.")

**Booking states:** "Book your assessment slot" · "No slots currently available." · "Already booked" · "You already have an assessment booking." · "Confirm"/"Booking…" · "that slot was just taken, please pick another"

**Q&A:** "Ask the Assessor" · "Your question" · "Type your question here…" · "Send question"/"Sending…" · "Your questions" · "No questions yet. Ask one above." · "Awaiting answer" · "Asked {date}" · "Answered {date}"

**Admin — candidates:** "Candidates" · "Create" · "Set API key"/"Save"/"Saving…"/"Key saved." · "Reset password" · "Re-issue invite" · "Disable"/"Enable" · status values `invited`/`active`/`disabled`

**Admin — slots:** "Manage Slots" · "Create Slot" · "Date/Time" · "Capacity" · "Open (n/cap)" · "Booked by {ids}" · "Edit"/"Save"/"Cancel"/"Delete" · "New slot ID"/"Reassign"/"Release" · "No slots yet." · "slot is booked; reassign or release first"

**Admin — questions:** "Questions Queue" · "Unanswered" (+ count) · "Answered" · "Type your answer…" · "Save"/"Saving…" · "No unanswered questions." · "No answered questions yet."

**Admin — activity:** "Activity Overview" · columns: Candidate, Status, Booked Slot, Unlock At, Logged In, {file names}, Key Revealed, #Questions · "No activity data."

**Admin — settings & data:** "Settings & data" · "Configuration" · "Prep window (days)" · "Retention reminder date" + "Retention reminder — NOT enforced; the system never auto-deletes. Leave blank to keep unset." · "Clear" · "Q&A SLA text" · "Display timezone" (placeholder "e.g. Europe/London") · "Saved." · **Danger zone:** "Danger zone — Purge all candidate data" · "This action permanently deletes:" + [All candidates / All bookings / All candidate questions / All download events / All candidate audit rows] · "This action keeps: admin account, config, slots, admin audit log." · "To confirm, type exactly: `PURGE ALL CANDIDATE DATA`" · "Purge all candidate data"/"Purging…" · browser confirm "This will permanently delete all candidate data. This cannot be undone. Proceed?" · "Purge complete. Records deleted:"

---

## 12. Component inventory (for the design system)

A non-exhaustive list the system needs to cover:
- **Navigation:** candidate top bar; admin nav (sidebar or top bar); footer with Privacy link; logged-in identity + Log out.
- **Buttons:** primary, secondary, destructive; sizes; default/hover/focus/disabled/busy.
- **Inputs:** text, password (with show/hide), number, date, datetime-local, textarea; label + helper + error; click-to-copy code/URL field; masked credential field.
- **Badges/pills:** status (invited/active/disabled), question (awaiting/answered), slot (open/booked), boolean tick (✓/—), count badge.
- **Cards:** question card (candidate & admin variants), info/preview box.
- **Tables:** standard (slots), wide matrix (activity) with sticky column + responsive scroll.
- **Banners:** info, warning, **danger**; success/error inline alerts; toast (optional).
- **Feedback:** loading skeleton/spinner; empty state; success/error messages.
- **Feature components:** Countdown; prep-window preview (ideally a small timeline); unlock reveal; purge confirmation pattern.

---

## 13. Deliverables requested

To let us rebuild efficiently, please provide:
1. **Design tokens** — colour palette (with semantic roles: text, heading, bg, surface, border, accent/primary, success, warning, danger, info), typography scale (families, sizes, weights, line-heights, letter-spacing), spacing scale, border-radius, shadow/elevation. **Light mode required; dark mode optional — tell us if in scope.** (Map to the existing CSS-variable scaffold where sensible.)
2. **Component specs** — the components in §12, with all states and measurements, ideally as a small component library/page in the design tool.
3. **High-fidelity screens** — all 12 screens in §9, including the major **states** (loading/empty/error/success and the conditional variants: dashboard locked/unlocked, booking/already-booked/empty, Q&A answered/awaiting, etc.).
4. **Responsive specs** — desktop + tablet + mobile for candidate screens; desktop-first for admin, with a stated strategy for the wide tables.
5. **The four "moment" interactions** (§8) designed with care — booking preview/timeline, lock→countdown→unlock, gated key reveal, purge danger flow.
6. **Accessibility annotations** — focus states, contrast, labels, non-colour status cues.
7. **Microcopy** — keep or improve §11 (preserve privacy meaning and the exact purge phrase).

**Format:** Figma (or similar) with named components and tokens is ideal; annotated PNG/PDF specs are acceptable. We will translate to React + CSS variables.

**Implementation guardrails (so designs are buildable here):** React/Vite/TS front end; prefer CSS variables + plain/utility CSS over heavy UI libraries; keep new dependencies minimal; the content column is currently ~1126px max — feel free to change. Icons: please specify a set (e.g. a lightweight open-source icon library) rather than bespoke SVGs unless necessary.

---

## 14. Open questions (please answer or assume sensible defaults)

1. **Brand assets** — is there a hiring-organisation logo, wordmark, colour palette, or existing style guide to apply? If yes, share them; if no, the designer proposes a clean trustworthy direction.
2. **Dark mode** — in scope? (The codebase currently auto-switches on `prefers-color-scheme`.)
3. **Tone** — how formal/warm should the candidate voice be? Any phrases the organisation does/doesn't use?
4. **Naming** — should the product have a visible name/title (e.g. in the header), or stay generic ("Assessment")?
5. **Iconography** — preferred icon set/style?
6. **Reassign UX** — open to replacing the "type a slot ID" reassign control with a slot picker?
7. **Candidate mobile priority** — how important is a polished mobile experience vs desktop-only?

---

## 15. Current implementation notes (context for the designer)

- **Tech:** React (Vite + TypeScript) SPA; FastAPI backend; everything talks over the same origin with a session cookie.
- **Styling today:** a single global `index.css` (defines unused design tokens + base typography, with auto dark mode) plus **per-element inline styles** with hardcoded colours. No component library, no Tailwind, no CSS modules. Browser-default form controls and buttons throughout. No shared header/nav.
- **What this means for you:** there's effectively a blank canvas with a token scaffold. You're not fighting an existing design system — you're creating the first one. We will replace the inline styles with your token-driven components on rebuild.

---

*Once the designs are ready, we'll rebuild the front end screen-by-screen against them in this same repository, reusing all the existing working API endpoints (so only the presentation layer changes).*
