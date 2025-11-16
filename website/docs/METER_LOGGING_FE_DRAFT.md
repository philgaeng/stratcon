# Meter Logging Frontend – Draft Design

## Key Decisions & Constraints

- Single Next.js application hosts both `/reports` and `/meters`, sharing a common settings area while keeping feature-specific layouts.
- User flow follows building → tenant → floor (if multiple) → meter hierarchy. In v1, one session equals one building.
- Users select from buildings they are assigned to, then choose a tenant within that building.
- If a tenant occupies multiple floors, the user selects a floor before choosing a meter reference.
- Meters are shown by their last 6 digits only with the format \*last6digit
- Offline queue synchronises automatically when connectivity returns; the status surface must show successes, in-progress syncs, and errors.
- No compliance constraints on temporarily storing signatures locally; capture consists of free-text approver name plus drawn signature persisted to the database.
- History views surface only approved readings.
- Printable PDFs are emailed to tenant contacts after approval; a client-wide CSV export runs server-side on demand or on scheduled dates.
- Skipped meters are omitted (no reason capture in v1).
- One photo per reading is collected (for future OCR), without thumbnail review in the approval screen.
- Manual timestamp edits overwrite the stored value; database insert time remains available for audit trails.

## Proposed User Flow

1. **Login & Routing**  
   Encoder authenticates; role detection routes them to `/meters/home`.
2. **Building Selection**  
   User selects a building from their assigned buildings list. A search box filters buildings by name (matching from the start of the building name). Default focus to the encoder's last building if available.
3. **Tenant Selection**  
   After selecting a building, user chooses a tenant from that building. A search box filters tenants by name (matching from the start of the tenant name). Display shows tenant context, units, and active meter count.
4. **Floor Selection (if applicable)**  
   If the selected tenant occupies multiple floors, user selects a floor before proceeding to meter selection. A search box filters floors by floor number (matching from the start of the floor number).
5. **Meter Selection & Entry**  
   `GET /meters/v1/tenants/{tenant_id}/meters` returns active meter assignments for the chosen floor. A search box filters meters by meter ID (matching from the start of the displayed meter ID, e.g., \*last6digit format). Encoder records readings meter-by-meter (optionally attaching notes or a photo) or skips as needed.
6. **Review & Approval**  
   Summary table highlights new readings, deltas, and validation warnings. Approver name (free text) and signature canvas are captured. Submission executes `POST /meters/v1/records` then `POST /meters/v1/approvals`.
7. **Confirmation & History**  
   Completion screen confirms sync status, notes that PDFs/emails were queued, and links to recent approved history via `GET /meters/v1/meter-records`.
8. **Notifications & Settings**  
   Top-level status button surfaces offline queue progress and errors. A consolidated `/settings` area (shared with `/reports`) exposes diagnostics, manual sync trigger, and sign-out.

## Wireframe Sketches (Text)

```text
[Building Selection]
┌────────────────────────────┐
│ Stratcon Meter Logging     │
├────────────────────────────┤
│ Select Building            │
│ [ Search buildings...  🔍] │
│ ────────────────────────── │
│ Building A                 │
│   Last used: Feb 7 08:42   │
│   ▶ Select                 │
│                            │
│ Building B                 │
│   ▶ Select                 │
│ …                          │
└─ Buildings │ History │ ⚙  ─┘
```

```text
[Tenant Selection]
┌────────────────────────────┐
│ ← Building A               │
├────────────────────────────┤
│ Select Tenant              │
│ [ Search tenants...     🔍] │
│ ────────────────────────── │
│ Tenant A                   │
│   Units: 18A, 18B          │
│   Active meters: 4         │
│   Last approved: Feb 2     │
│   ▶ Select                 │
│                            │
│ Tenant B                   │
│   Units: 19A, 19B          │
│   Active meters: 2         │
│   ▶ Select                 │
└─ Buildings │ History │ ⚙  ─┘
```

```text
[Floor Selection (if multiple)]
┌────────────────────────────┐
│ ← Tenant A                 │
├────────────────────────────┤
│ Select Floor               │
│ [ Search floors...    🔍] │
│ ────────────────────────── │
│ Floor 18                   │
│   Units: 18A, 18B          │
│   Meters: 4                │
│   ▶ Select                 │
│                            │
│ Floor 19                   │
│   Units: 19A, 19B          │
│   Meters: 2                │
│   ▶ Select                 │
└─ Buildings │ History │ ⚙  ─┘
```

```text
[Meter Selection]
┌────────────────────────────┐
│ ← Tenant A · Floor 18      │
├────────────────────────────┤
│ Select Meter               │
│ [ Search meters...     🔍] │
│ ────────────────────────── │
│ Meter MTR-1                │ Units 18A, 18B
│ Last: 1420 kWh (Feb 2)     │
│ [ Enter Reading ]          │
│                            │
│ Meter MTR-2                │
│ Last: 875 kWh (Feb 2) ⚠    │
│ [ Enter Reading ]          │
│                            │
│ Skipped (0)                │
│ [ Review & Submit ] (ghost)│
└─ Buildings │ History │ ⚙  ─┘
```

```text
[Enter Reading Modal]
┌────────────────────────────┐
│ ← Meter MTR-1              │
├────────────────────────────┤
│ Last reading: 1420 kWh     │
│ Last time: Feb 2 11:08     │
│                            │
│ Reading (kWh)              │
│ [ 1425.0           ]       │
│ Timestamp                  │
│ [ Feb 7 • 08:45 AM ▾ ]     │
│ Notes (optional)           │
│ [ … ]                      │
│ Photo                      │
│ [ 📷 Capture reading ]     │
│                            │
│ [ Save ]   [ Skip Meter ]  │
└────────────────────────────┘
```

```text
[Review & Approval]
┌────────────────────────────┐
│ ← Review                   │
├────────────────────────────┤
│ Meter   Last    New   Δ    │
│ MTR-1   1420    1425  +5   │
│ MTR-2   875     900   +25  │
│ Skipped: MTR-3             │
├────────────────────────────┤
│ Approver Name              │
│ [ Jane D. (Tenant Rep) ]   │
│ Signature                  │
│ [ touch canvas here ]      │
│ Notes (optional)           │
│                            │
│ [ Submit ]                 │
└─ Buildings │ History │ ⚙  ─┘
```

```text
[Status & Sync Panel]
┌────────────────────────────┐
│ Notifications & Status     │
├────────────────────────────┤
│ Sync Status: Offline ⚠     │
│ Pending submissions: 2     │
│ Last success: Feb 7 08:42  │
│ [ Retry Now ]              │
│                            │
│ Diagnostics                │
│ - Last sync: Feb 6 18:12   │
│ - App version: 0.1.0       │
│                            │
│ [ Sign Out ]               │
└────────────────────────────┘
```

## Implementation Backlog (Draft)

- Scaffold `/meters` route with dedicated layout and bottom navigation.
- Build building selection page showing encoder's assigned buildings.
- Implement tenant selection page filtered by selected building.
- Add floor selection step (conditional, only if tenant has multiple floors).
- Create meter selection list with inline status badges and entry triggers.
- Implement state store backed by IndexedDB for offline support (building-level sessions).
- Develop reading entry modal with validation and timestamp controls.
- Assemble review/approval screen including signature capture and bulk submission workflow.
- Implement offline queue worker to retry stored submissions and surface status in settings.
- Add history panels pulling from `GET /meters/v1/meter-records` for building-level context.
- Add server-side routines for tenant-level PDF emails post-approval and scheduled/on-demand client CSV exports.
