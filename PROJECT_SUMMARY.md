# Stratcon Project Summary

## Project Overview

Stratcon is an electricity consumption reporting system that generates detailed reports for building tenants. The system tracks electricity consumption data from multiple sources, applies complex cutoff date/time logic to group data into billing periods, and generates HTML reports with charts and analytics.

### Current Status

- ✅ Backend API fully functional
- ✅ Frontend UI operational
- ✅ Database schema implemented
- ✅ Report generation working
- ✅ Email delivery working
- ✅ Cutoff logic implemented
- ✅ Settings service integrated
- 🚧 Authentication pending (next phase)

---

## Architecture

### Technology Stack

**Backend:**

- FastAPI (Python) - REST API
- SQLite - Database
- Pandas - Data manipulation
- AWS SES - Email delivery
- Uvicorn - ASGI server

**Frontend:**

- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS v4
- React

**Infrastructure:**

- Conda environment: `datascience`
- Python 3.x
- Node.js/npm

---

## Directory Structure

```
stratcon/
├── backend/
│   ├── api.py                    # FastAPI application
│   ├── services/
│   │   ├── config.py             # Configuration constants
│   │   ├── db_schema.py          # Database schema definition
│   │   ├── settings.py            # Settings service (cutoff management)
│   │   ├── data_preparation.py   # Cutoff logic & data processing
│   │   ├── reporting.py          # Report generation
│   │   ├── report_generation.py  # Report orchestration
│   │   ├── utils.py              # Logging utilities
│   │   └── data_extract_and_compilation/
│   │       └── compile_floor_data.py  # CSV data aggregation
│   ├── scripts/
│   │   ├── launch_servers.sh     # Server launcher (compiles data + starts servers)
│   │   ├── stop_servers.sh       # Server stopper
│   │   ├── populate_database.py  # Initial DB population
│   │   └── migrate_csv_to_db.py  # CSV to DB migration (for cutoff settings)
│   ├── data/
│   │   └── settings.db            # SQLite database
│   └── logs/                      # Application logs
├── website/
│   ├── app/
│   │   ├── layout.tsx             # Root layout
│   │   ├── page.tsx               # Home (redirects to /login)
│   │   ├── login/page.tsx         # Login page (Cognito placeholder)
│   │   └── reports/page.tsx       # Report generation form
│   ├── components/
│   │   └── Logo.tsx               # Logo component
│   └── lib/
│       └── api-client.ts          # API client utilities
└── downloads/
    └── NEO/                       # CSV data files
        ├── NEO3_0708/
        ├── NEO3_0910/
        └── ...
```

---

## Database Schema

### Overview

SQLite database (`backend/data/settings.db`) with comprehensive schema for managing EPCs, clients, buildings, units, tenants, users, and contacts.

### Key Tables

#### Core Entities

- **`epcs`** - Electricity Producing Companies (Stratcon, Aboitiz Power, etc.)
- **`clients`** - Building Managers (e.g., NEO)
- **`buildings`** - Physical buildings (e.g., Neo3, Neo5)
- **`units`** - Individual units/spaces within buildings
- **`tenants`** - Tenants occupying units
- **`loads`** - Electrical loads (meters/MCBs)

#### People Management

- **`users`** - System users with login credentials and permissions
  - `user_group`: `super_admin`, `client_admin`, `client_manager`, `viewer`, `tenant_user`
  - `email` (unique) - used for login
- **`contacts`** - Business contacts (can be linked to users via `user_id`)
- **`epc_contact_assignments`** - Links contacts to EPCs
- **`client_contact_assignments`** - Links contacts to clients
- **`user_client_assignments`** - Assigns users to clients with permissions

#### History & Tracking

- **`unit_tenants_history`** - Historical tenant occupancy
- **`unit_loads_history`** - Historical load assignments

### Cutoff Settings Hierarchy

Settings cascade down with priority (most specific wins):

1. Unit-level cutoff (if unit has settings)
2. Client-level cutoff
3. EPC-level cutoff
4. System default (26, 23:59:59)

All cutoff settings include: `cutoff_day`, `cutoff_hour`, `cutoff_minute`, `cutoff_second`

### Current Data

- **EPCs**: Stratcon, Aboitiz Power
- **Clients**: NEO (under Stratcon)
- **Buildings**: Neo3, Neo5
- **Tenants**: 8 tenants (Floor 07-08 through 22-23-24)
- **Users**: 7 users with various permissions
- **Contacts**: 8 contacts (users + NEO contact)

See `backend/docs/DATABASE_SCHEMA.md` for complete schema documentation.

---

## Backend Services

### API Endpoints (`backend/api.py`)

**Report Generation:**

- `GET /` - API info
- `GET /clients` - List available clients
- `GET /tenants?client_token=NEO` - List tenants for a client
- `POST /reports/tenant` - Generate reports for a tenant
  - Body: `{tenant_token, client_token, month, cutoff_date, cutoff_time, user_email}`
- `POST /reports/client` - Generate reports for all tenants

**Settings Management:**

- `GET /settings/client/{client_token}` - Get all settings for a client
- `POST /settings/client` - Update client settings
- `POST /settings/tenant` - Update tenant settings
- `GET /settings/cutoff?client_token=X&tenant_token=Y&load_name=Z` - Get cutoff datetime

**CORS:** Configured for `localhost:3000`, `localhost:3001`

### Key Services

#### `services/settings.py`

Manages cutoff settings with database integration:

- `get_cutoff_datetime(client_token, tenant_token, load_name)` - Retrieves cutoff with fallback hierarchy
- `set_client_settings()` - Updates client defaults
- `set_tenant_settings()` - Updates tenant/unit settings
- Auto-creates clients/EPCs if missing (for backward compatibility)

#### `services/data_preparation.py`

Core cutoff logic:

- `generate_cutoff(date, cutoff_datetime)` - Maps dates to cutoff months
- `generate_cutoff_hourly()` - Applies hourly adjustments before day logic
- `select_full_months()` - Validates complete cutoff months (spans multiple calendar months)
- Handles cutoff days before/after 15th with complex date mapping

**Cutoff Logic Rules:**

- **Hourly adjustment first**: Based on cutoff time (before/after 12:00)
- **Day-based mapping**:
  - If cutoff_day ≤ 15: Cutoff month spans from cutoff_day to (cutoff_day-1) of next month
  - If cutoff_day > 15: Cutoff month spans from start of month to (cutoff_day-1) plus dates from previous month from cutoff_day onwards

#### `services/reporting.py`

Generates HTML reports with charts:

- `generate_onepager_report_values_and_charts()` - Main report generator
- Uses Plotly for charts
- Integrates with settings service for cutoff retrieval
- Filters by cutoff month (not calendar month)

#### `services/report_generation.py`

Orchestrates report generation:

- `generate_reports_for_tenant()` - Main entry point
- Handles email sending with attachments
- Only sends email if reports are generated

### Email Delivery

- AWS SES integration
- Sends reports as HTML attachments
- Recipients from contacts with `receive_reports_email = true`

---

## Frontend

### Pages

#### `/login` (`website/app/login/page.tsx`)

- Login form with Cognito placeholder
- Currently has temporary redirect
- **TODO**: Implement AWS Cognito authentication

#### `/reports` (`website/app/reports/page.tsx`)

- Report generation form
- Features:
  - Client dropdown (auto-loads from API)
  - Tenant dropdown (loads based on client selection)
  - Month selector (optional)
  - Cutoff date/time inputs (optional, defaults from settings)
  - Email input (required)
  - Submit button
- Uses `api-client.ts` for API communication
- Shows success/error messages

### API Client (`website/lib/api-client.ts`)

- Wrapper for backend API calls
- Handles errors and loading states
- Base URL: `http://localhost:8000`

### Styling

- Tailwind CSS v4
- Custom green color scheme (`#4CAF50` primary)
- Geist fonts (sans and mono)

---

## Critical Business Logic

### Cutoff Month Calculation

**Example with cutoff_day = 26:**

- September cutoff month includes:
  - Aug 25-31 (from previous calendar month)
  - Sept 1-24 (from current calendar month)
  - Total: 31 days spanning 2 calendar months

**For report generation:**

- Must compile data from multiple calendar months to get complete cutoff month
- `select_full_months()` validates completeness by counting unique dates across calendar months
- Month filtering uses `Year-Month-cut-off` column, not calendar month

### Data Flow

1. **CSV Files** → Raw electricity consumption data
2. **Compile** → `compile_floor_data.py` merges CSVs into consolidated files
3. **Load** → Backend reads compiled CSV files
4. **Cutoff Mapping** → Dates mapped to cutoff months based on cutoff_day/time
5. **Filter** → By cutoff month (not calendar month)
6. **Generate** → Reports with charts and analytics
7. **Email** → Send to contacts with `receive_reports_email = true`

---

## Server Management

### Launch Script (`backend/scripts/launch_servers.sh`)

**Features:**

1. Compiles floor data first (always fresh)
2. Checks for existing servers (port + response test)
3. Auto-restart mode (`--restart` flag)
4. Interactive mode (default, prompts before killing)

**Usage:**

```bash
# Interactive mode
./backend/scripts/launch_servers.sh

# Auto-restart mode
./backend/scripts/launch_servers.sh --restart
```

**What it does:**

- Compiles all tenant data for specified client (default: NEO)
- Checks ports 8000 (backend) and 3000 (frontend)
- Tests if servers are responding
- Kills unresponsive/zombie processes
- Starts backend: `uvicorn api:app --host 0.0.0.0 --port 8000 --reload`
- Starts frontend: `npm run dev` (in website directory)
- Saves logs to `/tmp/stratcon_*.log`

### Stop Script (`backend/scripts/stop_servers.sh`)

- Kills backend and frontend processes
- Cleans up PID files

---

## Authentication Requirements (For Next Agent)

### Current State

- Login page exists but is placeholder
- No authentication middleware
- No user session management
- No protected routes

### What Needs Implementation

1. **AWS Cognito Integration**

   - User pool setup
   - Sign in/up flows
   - Token management
   - Session handling

2. **Backend Authentication**

   - JWT token validation
   - User context injection
   - Permission checking based on `user_group`
   - Protected API endpoints

3. **Frontend Authentication**

   - Cognito SDK integration
   - Auth state management
   - Protected routes (redirect to /login if not authenticated)
   - User profile/role display

4. **Permission System**
   Based on `users.user_group`:

   - `super_admin`: Full system access
   - `client_admin`: Manage assigned clients
   - `client_manager`: View/manage assigned clients (no user creation)
   - `viewer`: Read-only access
   - `tenant_user`: Tenant-specific access

5. **User-Client Access**
   - Users assigned via `user_client_assignments` table
   - Check user's assigned clients for filtering
   - `super_admin` sees all clients

### Database Support

- ✅ `users` table with `email`, `user_group`, `active`
- ✅ `user_client_assignments` table for client access
- ✅ Contacts can link to users via `user_id`
- ✅ All users/contacts already populated in database

### API Changes Needed

- Add authentication middleware to FastAPI
- Extract user from JWT token
- Filter clients/tenants based on user permissions
- Return user info endpoint: `GET /auth/me`

### Frontend Changes Needed

- Replace placeholder login with Cognito
- Add auth context/provider
- Protect `/reports` route
- Show user name/role in UI
- Add logout functionality

---

## Configuration Files

### Environment Variables

- Backend uses `.env.local` (if exists, loaded via `load_env.py`)
- Frontend uses `.env.local` (in website directory)
- **TODO**: Add Cognito config (user pool ID, client ID, region)

### Backend Config (`backend/services/config.py`)

- `PHILIPPINES_TZ` - Timezone for all date operations
- `DEFAULT_CLIENT` - Default client token ("NEO")
- `MAX_MISSING_DAYS_PER_MONTH` - Data quality threshold
- Paths for reports, logos, data files

---

## Logging

### Log Files (`backend/logs/`)

- `db_manager.log` - Main application log
- `error.txt` - Error messages only
- `info.txt` - Info messages
- `debug.txt` - Debug messages
- `warning.txt` - Warning messages

All logs use `ReportLogger` utility which formats and categorizes messages.

---

## Testing

### Manual Testing

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Report generation tested and working
- Email delivery tested and working
- Cutoff month logic verified (September 2025 reports working)

### Test Data

- Client: NEO
- Tenants: 8 tenants (NEO3_0708 through NEO3_222324)
- Data range: May 2025 - November 2025 (varies by tenant)

---

## Known Issues & TODOs

### Completed ✅

- ✅ Cutoff month logic fixed (spans multiple calendar months)
- ✅ Settings service integrated with database
- ✅ Launch script with data compilation
- ✅ Database population

### Pending 🚧

- 🚧 Authentication (assigned to next agent)
- 🚧 Units and loads mapping (need load names)
- 🚧 Frontend settings page for cutoff management
- 🚧 Better error handling in frontend

---

## Key Files for Authentication Agent

1. **Database Schema**: `backend/services/db_schema.py`
2. **API Entry**: `backend/api.py`
3. **Login Page**: `website/app/login/page.tsx`
4. **Reports Page**: `website/app/reports/page.tsx`
5. **API Client**: `website/lib/api-client.ts`
6. **Schema Docs**: `backend/docs/DATABASE_SCHEMA.md`

---

## Development Workflow

### Starting Development

```bash
# Compile data and start servers
./backend/scripts/launch_servers.sh --restart

# Or manually:
conda activate datascience
cd backend && uvicorn api:app --host 0.0.0.0 --port 8000 --reload
cd website && npm run dev
```

### Database Operations

```bash
# Populate database
conda run -n datascience python3 backend/scripts/populate_database.py

# Query database
conda run -n datascience sqlite3 backend/data/settings.db
```

### Compiling Data

```bash
# Compile all tenants for a client
conda run -n datascience python3 backend/services/data_extract_and_compilation/compile_floor_data.py --client NEO

# Compile single tenant
conda run -n datascience python3 backend/services/data_extract_and_compilation/compile_floor_data.py --tenant NEO/NEO3_0708
```

---

## Important Notes for Authentication

1. **User Login**: Users authenticate with `email` (unique in database)
2. **Permissions**: Check `users.user_group` after authentication
3. **Client Access**: Filter by `user_client_assignments` table
4. **Super Admin**: `user_group = 'super_admin'` has access to all clients
5. **Backend Port**: 8000 (CORS configured for localhost:3000)
6. **Frontend Port**: 3000
7. **Database**: SQLite at `backend/data/settings.db`

---

## Contact Information (For Reference)

### Stratcon EPC

- Address: 22-4F Madison Galeries, Don Jesus Blvd., Cupang, Muntinlupa City
- Contacts: Colin Steley, Jovs Carcido, Sam Suppiah, Mark Nania (client_admin)
- Philippe Gaeng (super_admin)

### Aboitiz Power EPC

- Address: 10F, NAC Tower, 32nd St, Taguig, 1229 Metro Manila
- Contacts: Jherald Casipit, Mary Antonette Torres (client_manager)

### NEO Client

- Address: NEO3, 30th St, Taguig, Metro Manila
- Contact: Richard De Borja (richard.deborja@neooffice.ph)

---

## Next Steps

1. **Authentication Implementation** (assigned to next agent)
2. **Load Names Mapping** (when provided)
3. **Units & Loads Assignment** (link units to tenants and loads)
4. **Settings UI** (manage cutoff settings in frontend)
5. **Enhanced Reporting** (additional report types/features)

---

_Last Updated: 2025-11-03_
_Document Version: 1.0_
