# Implementation Questions for Meter Logging (Option 2)

This document lists all questions that need to be answered before implementing the meter logging feature.

## ✅ Already Answered

- [x] **Camera + OCR:** No OCR in first release (manual entry only)
- [x] **Camera + OCR:** timestamp from image metadata (can trust phone)
- [x] **Camera + OCR:** Both digital and analog dials expected
- [x] **Architecture:** Option 2 (web app with mobile-first layout)

---

## 1. User Role Management

### Q1.1: User Role Storage

**Question:** Are `encoder` and `tenant_approver` new `user_group` values in the `users` table, or a separate `user_role` field?

**Options:**

- A) Add as new `user_group` values (e.g., `user_group = 'encoder'` or `'tenant_approver'`)
- B) Create separate `user_role` field in `users` table
- C) Use `contacts` table with role assignments

**Recommendation:** Option A (add to `user_group`) - simpler, consistent with existing system

**Your Answer:** A

---

### Q1.2: Multiple Roles

**Question:** Can a user have multiple roles? (e.g., both `encoder` and `tenant_approver`?)

**Options:**

- A) Yes, users can have multiple roles
- B) No, one role per user

**Recommendation:** Option B (one role per user) - simpler for first release

**Your Answer:** B - and we manage access with permissions

---

### Q1.3: Super Admin Access

**Question:** Should `super_admin` have access to meter logging for oversight?

**Options:**

- A) Yes, super_admin can access meter logging
- B) No, only encoder and tenant_approver can access

**Recommendation:** Option A (yes) - useful for oversight and troubleshooting

**Your Answer:** A - Yes

---

## 2. Access Control & Data Filtering

### Q2.1: Encoder Meter Access

**Question:** Which meters can an `encoder` see? (All meters for their client? Specific buildings/units?)

**Options:**

- A) All meters for their assigned client(s)
- B) Only meters for specific buildings/units (need assignment table)
- C) All meters (no filtering)

**Recommendation:** Option A (all meters for assigned client) - simpler, uses existing `user_client_assignments`

**Your Answer:** Lets prepare an assignment table at building level, we may use it as well for the other client_roles as some roles are building specific. Lets fill up the values to all by default so we have the structure and code ready without having to prepare the full front end settings functionnalities. It can be added later

---

### Q2.2: Tenant Approver Meter Access

**Question:** Which meters can a `tenant_approver` see? (Only meters for their tenant's units?)

**Options:**

- A) Only meters for their tenant's units (via `unit_tenants_history`)
- B) All meters for their client
- C) Specific assignment (need new assignment table)

**Recommendation:** Option A (only tenant's units) - makes sense for approval workflow

**Your Answer:** Option A

---

### Q2.3: User-Meter Linking

**Question:** How do we link users to their allowed meters?

**Options:**

- A) Via `user_client_assignments` (for encoders)
- B) Via `contacts` table (if contacts are linked to users)
- C) Via `unit_tenants_history` (for tenant_approvers)
- D) New assignment table

**Recommendation:**

- Encoders: Option A (`user_client_assignments`)
- Tenant Approvers: Option C (`unit_tenants_history` via tenant)

## **Your Answer:** user_client_building_assignments that include clients and buildings. if building row is none then all the building of the client are assigned- does that make sense (this clarifies q2.1)

### Q2.4: Active Assignments Only

**Question:** Should encoders see all meters for their client, or only active assignments?

**Options:**

- A) All meters (including inactive assignments)
- B) Only active assignments (`is_active = 1` in `unit_meters_history`)

**Recommendation:** Option B (only active) - more relevant for current work

**Your Answer:** Option B - Only active

---

## 3. Workflow & Permissions

### Q3.1: Encoder Edit/Delete

**Question:** Can encoders edit/delete their own records, or only create?

**Options:**

- A) Only create (no edit/delete)
- B) Can edit/delete their own records (within time limit, e.g., 24 hours)
- C) Can edit/delete anytime

**Recommendation:** Option B (edit/delete within time limit) - allows corrections, prevents abuse

**Your Answer:** Option A - The workflow will request a confirmation of the number entered by the encoder and verified by the tenant_manager before being sent to db. After modifications will be done by different users in a workflow that we wont integrate here.

---

### Q3.2: Approval Workflow

**Question:** What is the approval workflow?

**Options:**

- A) Encoder submits → Tenant approver approves/rejects
- B) Encoder submits → Auto-approved (no approval needed)
- C) Encoder submits → Optional approval (can be skipped)

**Recommendation:** Option A (encoder submits → approver approves) - matches your description

**Your Answer:** Auto approves, but it should be done on the same screen. at the beginning, we may just add a simple signing box where the approvers signs and his id is just used to provide the name in the record. We will see later for more complex workflows (using OTP for instance).
To clarify, the webapp will be only on the encoder phone, who will enter the value then ask the approver to sign on this phone. The tenant_approver will not use the app at all in v1. I prepared this role for future workflows.

---

### Q3.3: Tenant Approver Edit

**Question:** Can tenant_approvers edit records, or only approve/reject?

**Options:**

- A) Only approve/reject (no edit)
- B) Can edit before approving
- C) Can edit anytime

**Recommendation:** Option A (only approve/reject) - keeps workflow clear

**Your Answer:** Option A

---

### Q3.4: Approval Status Field

**Question:** Do we need an approval status field in `meter_records`?

**Options:**

- A) Yes, add `status` field (pending, approved, rejected)
- B) No, use separate `meter_record_approvals` table
- C) No approval status (all records are approved)

**Recommendation:** Option A (add status field) - simpler for first release

**Your Answer:** I think we need Option C to enable bulk approvals. The encoder enters the values for different meters with their respective timestamps, then the tenant approver approves in bulk and we record that timestamp for all the records.

---

### Q3.5: Unapproved Records in Reports

**Question:** What happens to unapproved records in reporting?

**Options:**

- A) Include unapproved records in reports (with status indicator)
- B) Exclude unapproved records from reports
- C) Include only approved records

**Recommendation:** Option C (include only approved) - ensures data quality

**Your Answer:** Option C

---

## 4. UI/UX Requirements (Mobile-First)

### Q4.1: Meter List Display

**Question:** Should encoders see a list of all meters, or search/filter by building/unit?

**Options:**

- A) List all meters (with search/filter)
- B) Search/filter required (no full list)
- C) Grouped by building/unit

**Recommendation:** Option A (list all with search/filter) - flexible for users

**Your Answer:** Option D - The workflow will be to search first for a tenant (by building - floor (we will add floor to the units table)). Once the tenant is chosen, then the user will see all the meters for this tenant, then he has the option to approve meters one by one or to approve them all (bulk edit below)

---

### Q4.2: Bulk Entry

**Question:** Do we need bulk entry (multiple meters at once)?

**Options:**

- A) Yes, bulk entry needed
- B) No, one meter at a time

**Recommendation:** Option B (one at a time) - simpler for first release, can add later

**Your Answer:** Option A - it may be much easier for the approvers if they have to sign the form only once for all tenants. The workflow will be 1. Select tenant 2. Select bulk edit 3. choose meter 4. enter value 5. choose meter 5. enter value etc until all the meters are recorded. Once all the meters are recorded, the user can decide to skip the remaining ones (this will avoid to block the recordings because one meter is not accessible or is marked as active in db while its not). Then we generate a form with all the records for all the meters that is to be signed by the approver.
To be noted, we timestamp the records at each encoding time. that will be the timestamp used in the db

---

### Q4.3: Validation Rules

**Question:** Should there be validation (e.g., prevent decreasing readings)?

**Options:**

- A) Yes, prevent decreasing readings (warn user)
- B) Yes, prevent decreasing readings (block submission)
- C) No validation (allow any value)
- D) Warn but allow (user can override)

**Recommendation:** Option D (warn but allow) - prevents errors but allows corrections

**Your Answer:** Option A - especially at the begining there may be bugs in DB - we should build an alert system for those cases though

---

### Q4.4: History View

**Question:** Should there be a history view of past readings?

**Options:**

- A) Yes, show history for each meter
- B) No, only current/last reading
- C) Yes, but only for tenant_approvers

**Recommendation:** Option A (yes, show history) - useful for verification

**Your Answer:** Option A - when encoding, the user should see the last value above the encoding field - this way he will be aware of the warnings already.

---

### Q4.5: Navigation Pattern

**Question:** Navigation pattern: Bottom tabs, hamburger menu, or swipe gestures?

**Options:**

- A) Bottom tabs (most common on mobile)
- B) Hamburger menu (top left)
- C) Swipe gestures
- D) Combination

**Recommendation:** Option A (bottom tabs) - most mobile-friendly, easy to use

**Your Answer:** Option A

---

### Q4.6: Offline Mode

**Question:** Should we support offline mode from the start? (PWA with service workers)

**Options:**

- A) Yes, offline mode from start
- B) No, online only for first release
- C) Basic offline (queue submissions, sync when online)

**Recommendation:** Option C (basic offline) - queue submissions, sync when online

**Your Answer:** Option C - we need to make sure that the timestamp is the timestamp of the mobile then and not of db.

---

### Q4.7: Barcode/QR Scanning

**Question:** Do we need barcode/QR code scanning for meter identification?

**Options:**

- A) Yes, barcode/QR scanning needed
- B) No, manual selection only
- C) Future feature

**Recommendation:** Option B (no, manual selection) - simpler for first release

**Your Answer:** Option B

---

## 5. API Design

### Q5.1: New vs Existing Endpoints

**Question:** Do we need new endpoints, or can we extend existing ones?

**Options:**

- A) New endpoints (separate from reporting API)
- B) Extend existing endpoints
- C) Mix of both

**Recommendation:** Option A (new endpoints) - cleaner separation, easier to maintain

**Your Answer:** Option A

---

### Q5.2: API Separation

**Question:** Should meter records API be separate from reporting API?

**Options:**

- A) Yes, separate API routes (`/meters/*`)
- B) No, same API routes
- C) Separate service but same API

**Recommendation:** Option A (separate routes) - clear separation, easier to maintain

**Your Answer:** A

---

### Q5.3: Real-time Updates

**Question:** Do we need real-time updates (WebSockets) for approval workflow?

**Options:**

- A) Yes, real-time updates needed
- B) No, polling is fine
- C) No, manual refresh

**Recommendation:** Option C (manual refresh) - simpler for first release

**Your Answer:** C - I dont think we need to refresh the data at all

---

## 6. Integration with Reporting

### Q6.1: Manual vs Digital Meter Data

**Question:** How are manual meter readings used in reports? (merged with digital meter data?)

**Options:**

- A) Merged with digital meter data (same report)
- B) Separate reports for manual meters
- C) Both options available

**Recommendation:** Option A (merged) - unified view for users

**Your Answer:** B - at the time being we will not use the record data in the available reports

---

### Q6.2: Manual vs Digital Indicator

**Question:** Should reports show which readings are manual vs digital?

**Options:**

- A) Yes, clearly indicate manual vs digital
- B) No, treat them the same
- C) Optional indicator

**Recommendation:** Option A (yes, indicate) - transparency for users

**Your Answer:** Option A - however we are not going to implement yet

---

### Q6.3: Unapproved Records in Reports

**Question:** Do unapproved readings appear in reports?

**Options:**

- A) Yes, include unapproved (with status)
- B) No, exclude unapproved
- C) Only approved readings

**Recommendation:** Option C (only approved) - ensures data quality

**Your Answer:** C

---

## 7. Database Schema

### Q7.1: Table Names

**Question:** Confirm table names - legacy schema used `load_metering` and `unit_loads_metering_history`; do we standardize on `meters` and `unit_meters_history`?

**Options:**

- A) Keep legacy names (`load_metering`, `unit_loads_metering_history`)
- B) Rename to match your terminology
- C) Use aliases in API

**Recommendation:** Option A (use existing names) - no database changes needed

**Your Answer:** Option B. lets rename everywhere the tables to meters and unit_meters_history (I think I have used unit_meters_history in db_queries.py)

---

## Next Steps

1. Answer all questions above
2. Review answers with team
3. Update database schema if needed
4. Create API specification
5. Start implementation

---

## Notes

- Questions marked with "Recommendation" have suggested answers based on best practices
- You can override recommendations based on your specific needs
- Some questions may need discussion with stakeholders
- Answers can be updated as requirements evolve
