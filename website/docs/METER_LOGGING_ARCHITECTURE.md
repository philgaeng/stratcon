# Meter Logging Feature - Architecture Discussion

## Overview

This document outlines architecture options for implementing a meter record logging feature that will be used by two distinct user types:

- **Encoders** (`user_role: encoder`) - Client contacts who log meter readings
- **Tenant Approvers** (`user_role: tenant_approver`) - Tenant contacts who approve/verify meter readings

These users should be completely separated from the reporting functionality.

## Executive Summary: Revised for Manual Entry (No OCR in First Release)

### 🎯 Updated Requirements (First Release)

- ✅ **Manual entry only** - No OCR in first release
- ✅ **timestamp from image metadata OR manual entry** - User can choose
- ✅ **Offline capability preferred** - For queuing submissions when offline
- ✅ **Mobile-first design** - 100% mobile-optimized
- ⏳ **OCR in future release** - Will be added later

### ✅ Your Analysis - Critical Review

**✅ What You Got Right:**

1. **Backend sharing** - Absolutely correct, backend API is shared, no duplication
2. **Cognito config** - You're right this is a consideration, but actually simpler than you think (see below)
3. **No OCR = simpler** - Manual entry is just forms, works fine in Option 2
4. **Migration is manageable** - If designed well, migration is straightforward

**⚠️ What You Might Be Missing:**

1. **Cognito setup is simpler than you think** - Can reuse same User Pool and Client ID
2. **Offline queuing still valuable** - PWA with Option 2 can handle this
3. **Migration complexity** - Still 1-2 weeks even if designed well
4. **Future OCR considerations** - Will need to migrate eventually if OCR requires native features

### 📊 Migration Complexity

| Migration Path          | Complexity       | Estimated Effort | Backend Changes              |
| ----------------------- | ---------------- | ---------------- | ---------------------------- |
| **Option 2 → Option 3** | Medium ⚠️        | 1-2 weeks        | ✅ None (API works for both) |
| **Option 2 → Option 4** | Medium-High ⚠️⚠️ | 2-3 weeks        | ✅ None                      |
| **Option 3 → Option 4** | Low-Medium ✅    | 1 week           | ✅ None                      |

**Key Insight:** Backend API doesn't need changes - same endpoints work for both web app and separate app.

### 🎯 Final Recommendation (REVISED FOR MANUAL ENTRY)

**Based on updated requirements (NO OCR in first release, manual entry only):**

**✅ RECOMMENDED: Option 2 (Web App with Mobile-First Layout)**

**Rationale:**

1. **No OCR = No native camera requirement** - Manual entry is just forms
2. **Faster to market** - Single codebase, reuse existing auth
3. **Offline queuing works in PWA** - Service workers can queue submissions
4. **Cognito setup is minimal** - Can reuse same User Pool/Client ID (just different redirect URI)
5. **Migration is manageable** - When OCR is added, can migrate to Option 3 if needed
6. **Backend is shared anyway** - No duplication

**Cognito Configuration Reality Check:**

- ✅ **Same User Pool** - No change needed
- ✅ **Same Client ID** - Can reuse (just different redirect_uri)
- ⚠️ **OR New Client ID** - 5 minutes to create, minimal config
- ✅ **Same user groups** - No change needed
- **Cognito config difference: ~15-30 minutes** (not days)

**⚠️ IMPORTANT CLARIFICATION:**
The 15-30 minutes is ONLY for Cognito configuration difference, NOT the total implementation difference.

**Total Implementation Difference:**

- **Option 2:** Add `/meters` route to existing app (~1-2 days)
- **Option 3:** Create separate Next.js app + set up project + extract code + separate deployment (~1-2 weeks)
- **Actual difference: ~1-2 weeks of development time**

**When to Consider Option 3:**

- When OCR is added and requires native camera features
- When offline capabilities need to be more robust
- When you want complete separation for deployment

**Migration Path:**

- Design `/meters` as self-contained module
- Minimize dependencies on reporting code
- Use same API client pattern (easy to extract)
- Migration when OCR is added: 1-2 weeks

## Database Schema (Already Implemented)

The following tables are available:

- `meters` - Manual meters (meter_ref, description)
- `unit_meters_history` - History of meter assignments to units
- `meter_records` - Manual meter readings (meter_id, timestamp_record, meter_kWh)

## Architecture Options

### Option 1: Separate Route with Role-Based Access Control (RBAC)

**Structure:**

```
/app
  /reports          # Existing reporting page (accessible to: super_admin, client_admin, client_manager, viewer)
  /meters           # New meter logging page (accessible to: encoder, tenant_approver)
  /login            # Shared login
```

**Implementation:**

- Single Next.js app
- Route-level protection based on user roles
- Shared authentication (Cognito)
- Separate navigation/menus based on role
- Conditional rendering in AppShell based on user role

**Pros:**

- ✅ Simple to implement
- ✅ Shared authentication infrastructure
- ✅ Easy to maintain (single codebase)
- ✅ Can share common components (Logo, AuthButtons, etc.)
- ✅ Single deployment
- ✅ Easy to migrate to separate app later if needed

**Cons:**

- ⚠️ All users access same domain (potential confusion)
- ⚠️ Larger bundle size (includes both features)
- ⚠️ Less isolation between features

**Access Control:**

```typescript
// Middleware or route guard
const allowedRoles = {
  "/reports": ["super_admin", "client_admin", "client_manager", "viewer"],
  "/meters": ["encoder", "tenant_approver"],
};
```

---

### Option 2: Separate Routes with Completely Different Layouts (Mobile-First)

**Structure:**

```
/app
  /reports          # Reporting (desktop-first, full AppShell with Explorer)
  /meters           # Meter logging (mobile-first, minimal layout, no Explorer)
  /login            # Shared login
```

**Implementation:**

- Single Next.js app
- **Completely different layouts** for different sections
- `/meters` uses **mobile-first design** (touch-optimized, minimal UI, no sidebar)
- `/reports` uses desktop-first design (full AppShell with Explorer sidebar)
- Route-based code splitting (lazy load reporting code for meter users)
- Role-based redirects after login
- Different CSS strategies (mobile-first Tailwind for `/meters`)

**Pros:**

- ✅ Clear visual separation (completely different UI paradigms)
- ✅ Optimized layouts per use case (mobile vs desktop)
- ✅ Encoders don't see reporting UI elements
- ✅ Still single codebase/deployment
- ✅ Can optimize bundles per route (code splitting)
- ✅ Mobile-first design doesn't conflict with desktop reporting
- ✅ Easy to extract to separate app later if needed

**Cons:**

- ⚠️ More complex layout logic (two different design systems)
- ⚠️ Still same domain (URL-based separation)
- ⚠️ Need to ensure mobile styles don't leak to desktop reporting
- ⚠️ Bundle size still includes both (mitigated by code splitting)

**Mobile-First Considerations:**

- Touch-optimized buttons and inputs
- Large tap targets (min 44x44px)
- Bottom navigation or floating action buttons
- Camera access for photo uploads (future)
- Offline-first architecture (PWA capabilities)
- Responsive images and lazy loading

---

### Option 3: Separate Next.js Application

**Structure:**

```
/website           # Reporting app (existing Next.js web app)
/meter-app         # New meter logging app (separate Next.js web app)
```

**Implementation:**

- Two separate Next.js web applications (both are web apps, not native mobile apps)
- Shared authentication (same Cognito User Pool)
- Separate deployments
- Separate domains/subdomains (e.g., `app.stratcon.ph` vs `meters.stratcon.ph`)

**⚠️ IMPORTANT: Option 3 is still a WEB APP, not a native mobile app**

- Option 3 = Separate Next.js web app (runs in browser)
- Native mobile app = React Native, Flutter, etc. (runs on iOS/Android)
- These are different things!

**Pros:**

- ✅ Complete isolation
- ✅ Independent deployments
- ✅ Smaller bundle sizes per app
- ✅ Can use different tech stacks if needed
- ✅ Better foundation for future native mobile app (can share API layer)
- ✅ Clear separation of concerns

**Cons:**

- ⚠️ More complex setup (two repos or monorepo)
- ⚠️ Code duplication (auth, common components)
- ⚠️ Two deployments to manage
- ⚠️ More infrastructure overhead

---

### Option 4: Monorepo with Shared Packages

**Structure:**

```
/workspace
  /packages
    /auth          # Shared authentication
    /ui            # Shared UI components
    /api-client    # Shared API client
  /apps
    /website       # Reporting app
    /meter-app     # Meter logging app
```

**Implementation:**

- Monorepo (Turborepo, Nx, or pnpm workspaces)
- Shared packages for common code
- Separate apps for reporting and meter logging
- Independent deployments

**Pros:**

- ✅ Best of both worlds (isolation + code sharing)
- ✅ Scalable architecture
- ✅ Easy to extract mobile app later
- ✅ Shared types/interfaces
- ✅ Independent deployments

**Cons:**

- ⚠️ More complex initial setup
- ⚠️ Requires monorepo tooling knowledge
- ⚠️ More moving parts

---

## Recommended Approach: **Option 2 (Mobile-First Separate Layouts)**

**Decision:**

- Use **Option 2** with completely different layouts
- `/meters` is **100% mobile-first** design
- `/reports` remains desktop-first
- Route-based code splitting to optimize bundles

**Rationale:**

1. **Mobile-first requirement** - `/meters` must be optimized for mobile use
2. **Clear separation** - Completely different UI paradigms (mobile vs desktop)
3. **Single codebase** - Easier to maintain than separate apps initially
4. **Easy migration** - Can extract to separate app later if needed
5. **Future-proof** - Mobile-first design sets foundation for PWA/mobile app
6. **Code splitting** - Can lazy-load reporting code for meter users (smaller mobile bundle)

**Implementation Strategy:**

- Create separate layout component for `/meters` route
- Use mobile-first Tailwind classes (default mobile, `md:` for desktop)
- Implement route-based code splitting
- Consider PWA features for offline capability (future)

**When to Consider Migrating to Option 3 (Separate App):**

- If mobile bundle size becomes too large despite code splitting
- If mobile app needs native features (push notifications, background sync)
- If you want to deploy meter app as standalone PWA on different domain
- If mobile and desktop features diverge significantly
- If you need independent deployment cycles for mobile vs desktop
- **⚠️ CRITICAL: If camera + OCR requirements are too complex for web app** (see Camera + OCR Analysis below)

---

## Camera + OCR Feature Analysis

### Requirement

- Use phone camera to take picture of physical meter
- Extract meter reading value from image (OCR)
- Extract timestamp from image (or use photo metadata)

### Option 2 (Web App) - Camera + OCR Capabilities

**✅ What's Possible:**

1. **Camera Access:**

   - ✅ `getUserMedia()` API works on mobile browsers (iOS Safari 11+, Chrome Android)
   - ✅ Can capture photos directly in browser
   - ✅ Can access front/back camera
   - ✅ Works in PWA (Progressive Web App)

2. **Image Processing:**

   - ✅ Can upload images to backend via `multipart/form-data`
   - ✅ FastAPI supports file uploads (`File`, `UploadFile`)
   - ✅ Can process images server-side (Python: OpenCV, Tesseract, ML models)

3. **Client-Side OCR (Optional):**
   - ✅ Tesseract.js (JavaScript OCR library) - works in browser
   - ✅ ML models (TensorFlow.js) - can run in browser
   - ⚠️ Performance: Slower than native, larger bundle size
   - ⚠️ Accuracy: May be lower than server-side processing

**⚠️ Limitations:**

1. **Camera Quality:**

   - ⚠️ Web camera API has less control than native (focus, flash, zoom)
   - ⚠️ iOS Safari has stricter permissions/UX
   - ⚠️ No advanced camera features (HDR, night mode)

2. **Performance:**

   - ⚠️ Client-side OCR adds significant bundle size (Tesseract.js ~2MB)
   - ⚠️ Processing may be slower on mobile devices
   - ⚠️ Battery drain from intensive processing

3. **Offline Capability:**
   - ⚠️ Client-side OCR can work offline (if bundled)
   - ⚠️ Server-side OCR requires internet connection
   - ⚠️ Need to queue images for upload when offline

**✅ Recommended Approach for Option 2:**

- **Hybrid:** Capture photo in browser → Upload to backend → Server-side OCR
- **Why:** Better accuracy, no client bundle bloat, can use advanced ML models
- **Backend:** Use Python OCR libraries (Tesseract, EasyOCR, or cloud APIs like AWS Textract)
- **Offline:** Queue photos locally, upload when online
- **⚠️ Limitation:** Requires internet for OCR (not ideal for field work with tenant rep)

**✅ Alternative for Option 2 (PWA with Client-Side OCR):**

- **Client-side OCR:** Use Tesseract.js or TensorFlow.js in browser
- **Why:** Works offline, no server dependency
- **⚠️ Challenge:** Analog dial OCR is harder, may need specialized models
- **⚠️ Challenge:** Bundle size increases (~2-5MB for OCR libraries)
- **⚠️ Challenge:** Performance may be slower on older phones
- **Backend:** Optional server-side OCR for validation/improvement (when online)

**Implementation for Option 2:**

```typescript
// Frontend: Camera capture
const stream = await navigator.mediaDevices.getUserMedia({ video: true });
// Capture photo, convert to blob
const formData = new FormData();
formData.append("image", imageBlob);
formData.append("meter_id", meterId);
formData.append("timestamp", timestamp);

// Upload to backend
await fetch("/api/meters/ocr", {
  method: "POST",
  body: formData,
});
```

```python
# Backend: OCR processing
from fastapi import File, UploadFile
import pytesseract  # or EasyOCR, AWS Textract

@app.post("/meters/ocr")
async def process_meter_image(
    image: UploadFile = File(...),
    meter_id: int,
    timestamp: datetime
):
    # Read image
    image_bytes = await image.read()

    # OCR processing
    reading = extract_meter_reading(image_bytes)  # OCR logic
    timestamp = extract_timestamp(image_bytes) or timestamp

    # Save to database
    create_meter_record(meter_id, reading, timestamp)
```

### Option 3 (Separate App) - Camera + OCR Capabilities

**✅ Advantages:**

1. **Native Camera:**

   - ✅ Full access to native camera APIs
   - ✅ Better control (focus, flash, zoom, HDR)
   - ✅ Better UX (native camera UI)
   - ✅ Can use device-specific optimizations

2. **Performance:**

   - ✅ Can use native OCR libraries (iOS Vision, Android ML Kit)
   - ✅ Faster processing (native code)
   - ✅ Better battery efficiency

3. **Offline:**
   - ✅ Native apps handle offline better
   - ✅ Can bundle OCR models locally
   - ✅ Better sync capabilities

**⚠️ Trade-offs:**

- ⚠️ More complex development (native code or React Native)
- ⚠️ Separate codebase to maintain
- ⚠️ App store deployment process

**✅ Recommended Approach for Option 3:**

- **React Native or PWA with native plugins:**
  - React Native: Use `react-native-camera` + `react-native-vision-camera`
  - PWA: Use Capacitor/Ionic for native camera access
- **Hybrid OCR:** Client-side for speed, server-side for accuracy fallback

### Comparison: Option 2 vs Option 3 for Camera + OCR

| Feature              | Option 2 (Web App)        | Option 3 (Separate App)          |
| -------------------- | ------------------------- | -------------------------------- |
| **Camera Access**    | ✅ Yes (getUserMedia)     | ✅✅ Yes (Native APIs)           |
| **Camera Quality**   | ⚠️ Good                   | ✅✅ Excellent                   |
| **OCR Accuracy**     | ✅ Good (server-side)     | ✅✅ Excellent (native + server) |
| **Offline OCR**      | ⚠️ Limited                | ✅✅ Full support                |
| **Bundle Size**      | ⚠️ Larger (if client OCR) | ✅ Smaller (native)              |
| **Development Time** | ✅ Faster                 | ⚠️ Slower                        |
| **Maintenance**      | ✅ Single codebase        | ⚠️ Two codebases                 |
| **Deployment**       | ✅ Simple (web)           | ⚠️ App stores                    |

### Recommendation for Camera + OCR

**Based on Requirements:**

- ✅ **Offline OCR preferred** - Tenant rep is with encoder, checks validity
- ✅ **Analog dials expected** - Need robust OCR (harder than digital displays)
- ✅ **Human verification** - Perfect accuracy not critical (user can adjust)
- ✅ **timestamp from metadata** - Phone can be trusted

**✅ Option 2 with PWA + Client-Side OCR:**

- Can work with Tesseract.js or TensorFlow.js in browser
- ⚠️ **Challenge:** Analog dial OCR is harder, may need specialized models
- ⚠️ **Challenge:** Client-side OCR adds significant bundle size (~2-5MB)
- ⚠️ **Challenge:** Performance may be slower on older phones
- ✅ **Benefit:** Still single codebase, can migrate later

**✅✅ Option 3 (Separate App) - RECOMMENDED:**

- ✅ Native camera APIs (better for analog dial photography)
- ✅ Can use native OCR libraries (iOS Vision, Android ML Kit)
- ✅ Can bundle specialized OCR models for analog dials
- ✅ Better offline performance
- ✅ Better battery efficiency
- ✅ Can use device-specific optimizations
- ⚠️ **Trade-off:** More complex development, separate codebase

**💡 Revised Recommendation:**

Given the **offline OCR requirement** and **analog dials**, we recommend:

**Option A: Start with Option 3 (Separate App)**

- Best for offline OCR with analog dials
- Native camera + OCR from the start
- No migration needed later
- Better user experience for field work

**Option B: Option 2 with PWA + Hybrid OCR (If timeline is tight)**

- Start with server-side OCR (faster development)
- Add client-side OCR later (Tesseract.js or TensorFlow.js)
- Migrate to Option 3 when ready
- Accept that analog dial OCR may be less accurate initially

---

## Analog Dial OCR: Challenges & Solutions

### Challenge: Analog Dials are Harder for OCR

**Why Analog Dials are Difficult:**

- ⚠️ Circular/rotating dials (not linear text)
- ⚠️ Multiple dials with different scales
- ⚠️ Need to interpret pointer position, not just read numbers
- ⚠️ Lighting conditions affect visibility
- ⚠️ Camera angle matters (parallax error)
- ⚠️ Old/dirty meters may have unclear markings

### Solutions

**1. Image Pre-Processing:**

- ✅ Contrast enhancement
- ✅ Brightness adjustment
- ✅ Rotation correction
- ✅ Noise reduction
- ✅ Edge detection for dial boundaries

**2. Specialized OCR Models:**

- ✅ Train custom model on analog dial images
- ✅ Use computer vision for dial pointer detection
- ✅ Combine multiple techniques (OCR + CV)

**3. Hybrid Approach:**

- ✅ OCR attempts to read numbers
- ✅ Computer vision detects pointer position
- ✅ Manual entry fallback (user adjusts if needed)

**4. Best Practices for Photography:**

- ✅ Use flash in low light
- ✅ Ensure camera is perpendicular to meter
- ✅ Fill frame with meter (minimize background)
- ✅ Ensure all dials are visible
- ✅ Take multiple photos if needed

### Recommended OCR Stack for Analog Dials

**Option 3 (Separate App) - Recommended:**

- **Primary:** Custom TensorFlow.js model trained on analog dials
- **Fallback:** Tesseract.js for text extraction
- **Backup:** Manual entry (always available)

**Option 2 (Web App) - Alternative:**

- **Primary:** Server-side OCR (EasyOCR or custom Python model)
- **Fallback:** Tesseract.js client-side
- **Backup:** Manual entry

**Cloud Services (Optional):**

- AWS Textract (general OCR)
- Google Cloud Vision API
- Azure Computer Vision
- **Note:** May need custom training for analog dials

---

## Migration Complexity Analysis

### Option 2 → Option 3 (Separate App)

**Complexity: Medium** ⚠️

**What Needs to Change:**

1. **Frontend Structure:**

   - ⚠️ Create new Next.js app project (`/meter-app`)
   - ⚠️ Set up project structure (package.json, tsconfig, etc.)
   - ⚠️ Extract `/meters` route to separate Next.js app
   - ⚠️ Copy mobile-first components
   - ⚠️ Update routing (remove `/meters` from main app)
   - ⚠️ Need to handle shared code (auth, API client)

2. **Shared Code:**

   - ⚠️ Authentication logic (can copy, or extract to shared package)
   - ⚠️ API client (can copy, or extract to shared package)
   - ⚠️ Types/interfaces (can copy, or extract to shared package)
   - ✅ UI components (meter-specific, no sharing needed)

3. **Backend API:**

   - ✅ **No changes needed** - API works for both apps
   - ✅ Same endpoints, same authentication

4. **Deployment:**

   - ⚠️ Set up separate deployment pipeline
   - ⚠️ Configure separate domain/subdomain
   - ⚠️ Update CORS settings in backend
   - ⚠️ Set up separate CI/CD

5. **Configuration:**

   - ⚠️ Separate environment variables
   - ⚠️ Separate Cognito app client (optional, 15-30 min)
   - ✅ Same Cognito User Pool

6. **Development Setup:**
   - ⚠️ Separate dev server
   - ⚠️ Separate build process
   - ⚠️ Update development scripts

**Estimated Effort:**

- **Small team (1-2 devs):** 1-2 weeks
- **Larger team:** 3-5 days
- **Key factor:** How much code is shared vs meter-specific

**Breakdown:**

- Create new Next.js app: 1 day
- Extract/copy code: 2-3 days
- Set up deployment: 1 day
- Testing & refinement: 2-3 days
- **Total: ~1-2 weeks**

**Mitigation Strategies:**

- ✅ Design `/meters` as self-contained module from start
- ✅ Minimize dependencies on reporting code
- ✅ Extract shared code to separate files (easy to copy later)
- ✅ Use same API client pattern (easy to extract)

### Option 2 → Option 4 (Monorepo)

**Complexity: Medium-High** ⚠️⚠️

**What Needs to Change:**

1. **Project Structure:**

   - ⚠️ Set up monorepo tooling (Turborepo, Nx, or pnpm workspaces)
   - ⚠️ Restructure codebase into packages/apps
   - ⚠️ Extract shared code to packages
   - ⚠️ Update build/deploy scripts

2. **Shared Packages:**

   - ⚠️ Create `@stratcon/auth` package
   - ⚠️ Create `@stratcon/api-client` package
   - ⚠️ Create `@stratcon/types` package
   - ⚠️ Update imports across codebase

3. **Build System:**

   - ⚠️ Configure monorepo build pipeline
   - ⚠️ Set up dependency management
   - ⚠️ Configure code sharing

4. **Deployment:**
   - ⚠️ Update deployment pipelines
   - ⚠️ Configure independent builds
   - ✅ Can still deploy separately

**Estimated Effort:**

- **Small team:** 2-3 weeks
- **Larger team:** 1-2 weeks
- **Key factor:** Team familiarity with monorepo tools

**Mitigation Strategies:**

- ✅ Start with Option 2, design for extraction
- ✅ Use consistent patterns (easy to extract later)
- ✅ Consider monorepo from start if team is familiar

### Option 3 → Option 4 (Monorepo)

**Complexity: Low-Medium** ✅

**What Needs to Change:**

1. **Project Structure:**
   - ⚠️ Set up monorepo tooling
   - ⚠️ Move existing apps into monorepo
   - ✅ Extract shared code to packages
   - ⚠️ Update build/deploy scripts

**Estimated Effort:**

- **Small team:** 1 week
- **Larger team:** 3-5 days

**Why Easier:**

- ✅ Apps already separated
- ✅ Just need to extract shared code
- ✅ Less restructuring needed

---

## Final Recommendation: Revised for Manual Entry (No OCR)

### Requirements Summary (First Release):

- ✅ **Manual entry only** - No OCR in first release
- ✅ **timestamp from image metadata OR manual entry** - User can choose
- ✅ **Offline capability preferred** - For queuing submissions
- ✅ **Mobile-first design** - 100% mobile-optimized
- ⏳ **OCR in future release** - Will be added later

### 🎯 Recommended Strategy: **Option 2 (Web App) for First Release**

**Rationale:**

1. **No OCR = No native camera requirement** - Manual entry is just forms, works fine in web app
2. **Faster to market** - Single codebase, reuse existing auth setup
3. **Offline queuing works in PWA** - Service workers can queue submissions offline
4. **Cognito setup is minimal** - Can reuse same User Pool/Client ID (just different redirect URI)
5. **Backend is shared** - No duplication, same API endpoints
6. **Migration is manageable** - When OCR is added, can migrate to Option 3 if needed

**Cognito Configuration - Reality Check:**

```typescript
// Option 2: Same app, just different redirect
redirect_uri: "http://localhost:3000/meters"; // or "/reports" based on role

// Option 3: Separate app, can still use same User Pool and Client ID
// OR create new Client ID (5 minutes, minimal config)
// Same User Pool = same users, same groups
```

**Time Investment Breakdown:**

**Cognito Configuration:**

- **Option 2:** 0 minutes (reuse existing)
- **Option 3:** 15-30 minutes (create new Client ID if desired, or reuse existing)
- **Difference: 15-30 minutes** (Cognito only)

**Total Implementation Time:**

- **Option 2:**
  - Create `/meters` route: 1-2 days
  - Mobile-first layout: 1 day
  - Forms + offline support: 2-3 days
  - **Total: ~1 week**
- **Option 3:**
  - Create separate Next.js app: 1 day
  - Set up project structure: 1 day
  - Extract/copy code: 2-3 days
  - Set up separate deployment: 1 day
  - Mobile-first layout: 1 day
  - Forms + offline support: 2-3 days
  - **Total: ~2 weeks**

**Actual Difference: ~1 week of development time** (not 30 minutes!)

**Implementation Approach (Option 2):**

1. **Create `/meters` route in existing Next.js app**

   - Mobile-first layout (separate from AppShell)
   - PWA capabilities (offline support via service workers)
   - Manual entry forms (meter reading, timestamp)

2. **Offline Strategy:**

   - Use IndexedDB or localStorage for offline queue
   - Service worker for offline capability
   - Sync queue when online

3. **Future OCR Migration:**
   - Design `/meters` as self-contained module
   - Minimize dependencies on reporting code
   - Easy to extract to separate app when OCR is added

**Why Option 2 Makes Sense Now:**

- ✅ No OCR = no need for native camera APIs
- ✅ Manual entry is simple forms (works great in web app)
- ✅ Offline queuing works in PWA (service workers)
- ✅ Faster development (single codebase)
- ✅ Reuse existing auth (minimal Cognito config)
- ✅ Backend is shared anyway
- ✅ **Online OCR is already supported** - Can add server-side OCR later without architecture changes
- ✅ Can migrate to Option 3 when offline OCR is needed (if needed)

**When to Migrate to Option 3:**

- When **offline OCR** is required (Option 2 supports online OCR only)
- When you want complete separation for deployment (independent release cycles)
- When you want separate teams to work on each app
- When you want different tech stacks (if needed)
- **NOT necessarily for native mobile app** - Native mobile app can be built from Option 2 OR Option 3

**⚠️ Important Distinction:**

- **Option 3 = Separate web app** (still runs in browser, just separate Next.js project)
- **Native mobile app = React Native/Flutter** (runs on iOS/Android, completely different project)
- **You can build a native mobile app from Option 2 OR Option 3** - both share the same backend API

**Important: Option 2 Already Supports Online OCR**

- ✅ Web camera API (`getUserMedia`) works in browsers
- ✅ Can capture photos and upload to backend
- ✅ Backend can process OCR (Python: Tesseract, EasyOCR, AWS Textract)
- ✅ Return OCR results to frontend
- ✅ User can adjust if OCR is wrong (manual entry fallback)
- ⚠️ **Requires internet connection** - OCR processing happens on server
- ✅ **No architecture changes needed** - Just add OCR endpoint to backend

---

## Native Mobile App vs Option 3: Important Distinction

### Clarification

**Option 3 is NOT a native mobile app:**

- Option 3 = Separate Next.js web app (runs in browser)
- Native mobile app = React Native, Flutter, etc. (runs on iOS/Android)

**These are different things:**

- **Option 2:** Single Next.js web app with `/meters` route
- **Option 3:** Two separate Next.js web apps (both web, just separated)
- **Native Mobile App:** React Native/Flutter app (completely different, runs on device)

### Building a Native Mobile App

**You can build a native mobile app from Option 2 OR Option 3:**

- Both share the same backend API
- Both can use the same authentication (Cognito)
- Native app would be a separate project (React Native, Flutter, etc.)

**Recommended Approach for Native Mobile App:**

1. **Start with Option 2** (web app with `/meters` route)
2. **Build native mobile app later** (React Native, Flutter, etc.)
3. **Share backend API** (same endpoints work for both web and mobile)
4. **Optionally migrate to Option 3** if you want separate web apps, but this is NOT required for native mobile app

**Why Option 2 is fine for native mobile app:**

- Backend API is shared anyway
- Native app is a separate project regardless
- Option 2 vs Option 3 doesn't affect native mobile app development
- Native app can call the same API endpoints

### Decision Framework

**For Web App:**

- **Option 2:** Single web app (faster, simpler)
- **Option 3:** Separate web apps (isolation, independent deployment)

**For Native Mobile App:**

- **Can be built from Option 2 OR Option 3** - doesn't matter
- **Native app is separate project anyway** (React Native, Flutter, etc.)
- **Shares backend API** with web app(s)

**Recommendation:**

- **Start with Option 2** (web app)
- **Build native mobile app later** (separate project, shares API)
- **Migrate to Option 3 only if** you need separate web app deployments/isolation
- **Option 3 is NOT a prerequisite for native mobile app**

### Strategic Decision: Native Mobile App vs Option 3 (Separate Web App)

**If you had resources to do only ONE, which should you choose?**

**For THIS specific use case (meter logging in the field), I would recommend: Native Mobile App**

**Why Native Mobile App is Better for This Use Case:**

1. **Field Work Context:**

   - ✅ Better offline capability (works without internet)
   - ✅ Native camera access (better quality, focus, flash)
   - ✅ Better performance on mobile devices
   - ✅ Can work in areas with poor connectivity

2. **User Experience:**

   - ✅ Feels like a "real app" (better for field workers)
   - ✅ Faster, more responsive
   - ✅ Better battery efficiency
   - ✅ Can use device features (GPS, haptics, notifications)

3. **Future OCR:**

   - ✅ Native OCR libraries (iOS Vision, Android ML Kit)
   - ✅ Better for analog dials (can use specialized models)
   - ✅ Works offline (critical for field work)

4. **Deployment:**
   - ✅ App store distribution (easy updates)
   - ✅ Can push updates without user action
   - ⚠️ App store approval process (but manageable)

**Why Option 3 (Separate Web App) is Less Ideal:**

1. **Field Work Limitations:**

   - ⚠️ Requires internet connection (or PWA with limitations)
   - ⚠️ Web camera API has less control
   - ⚠️ Performance may be slower on mobile
   - ⚠️ Battery drain from web processing

2. **User Experience:**
   - ⚠️ Feels like a website (less "native" feel)
   - ⚠️ May be slower than native app
   - ⚠️ Limited access to device features

**Trade-offs:**

| Factor               | Native Mobile App     | Option 3 (Web App) |
| -------------------- | --------------------- | ------------------ |
| **Offline**          | ✅✅ Excellent        | ⚠️ Limited (PWA)   |
| **Camera**           | ✅✅ Native APIs      | ⚠️ Web API         |
| **Performance**      | ✅✅ Fast             | ⚠️ Slower          |
| **Development Time** | ⚠️ Longer (2-3 weeks) | ✅ Faster (1 week) |
| **Maintenance**      | ⚠️ Two platforms      | ✅ Single platform |
| **Deployment**       | ⚠️ App stores         | ✅ Simple (web)    |
| **Field Work**       | ✅✅ Better           | ⚠️ Less ideal      |

**Final Recommendation:**

**If resources allow only ONE:**

- **Choose Native Mobile App** for meter logging (field work use case)
- **Keep Option 2** for reporting (desktop use case)
- **Share backend API** (same endpoints for both)

**Why:**

- Field work needs offline capability (native app is better)
- Camera quality matters for future OCR (native is better)
- User experience matters for field workers (native feels better)
- Reporting can stay as web app (desktop use case)

**If resources are limited:**

- **Start with Option 2** (web app) - faster to market
- **Add native mobile app later** - when resources allow
- **Both share same backend API** - no duplication

---

## Key Questions to Answer Before Implementation

### 1. User Role Management

- [ ] **Q:** Are `encoder` and `tenant_approver` new `user_group` values in the `users` table, or separate `user_role` field?
- [ ] **Q:** Can a user have multiple roles? (e.g., both `encoder` and `tenant_approver`?)
- [ ] **Q:** Should `super_admin` have access to meter logging for oversight?

### 2. Access Control & Data Filtering

- [ ] **Q:** Which meters can an `encoder` see? (All meters for their client? Specific buildings/units?)
- [ ] **Q:** Which meters can a `tenant_approver` see? (Only meters for their tenant's units?)
- [ ] **Q:** How do we link users to their allowed meters? (via `user_client_assignments`? via `contacts` table?)
- [ ] **Q:** Should encoders see all meters for their client, or only active assignments?

### 3. Workflow & Permissions

- [ ] **Q:** Can encoders edit/delete their own records, or only create?
- [ ] **Q:** What is the approval workflow? (encoder submits → tenant_approver approves?)
- [ ] **Q:** Can tenant_approvers edit records, or only approve/reject?
- [ ] **Q:** Do we need an approval status field in `meter_records`? (pending, approved, rejected)
- [ ] **Q:** What happens to unapproved records in reporting?

### 4. UI/UX Requirements (Mobile-First)

- [ ] **Q:** Should encoders see a list of all meters, or search/filter by building/unit?
- [ ] **Q:** Do we need bulk entry (multiple meters at once)?
- [ ] **Q:** Should there be validation (e.g., prevent decreasing readings)?
- [x] **Q:** **CRITICAL - Camera + OCR:** Do we need offline OCR, or is server-side OCR acceptable?
  - **✅ ANSWERED: Ideally offline** - Can be backed up by manual entry if failed. Tenant representative is with encoder and checks validity, so offline is a plus.
- [x] **Q:** **CRITICAL - Camera + OCR:** What's the expected accuracy requirement? (90%? 95%? 99%?)
  - **✅ ANSWERED: As good as possible** - User can adjust if error (human checking/verification)
- [x] **Q:** **CRITICAL - Camera + OCR:** Should we extract timestamp from image metadata or require manual entry?
  - **✅ ANSWERED: Image metadata** - Can trust phone for timestamp
- [x] **Q:** **CRITICAL - Camera + OCR:** What types of meters? (digital displays, analog dials, both?)
  - **✅ ANSWERED: Both, but expect old analog dials** - This is important for OCR model selection
- [ ] **Q:** Should there be a history view of past readings?
- [ ] **Q:** Navigation pattern: Bottom tabs, hamburger menu, or swipe gestures?
- [ ] **Q:** Should we support offline mode from the start? (PWA with service workers)
- [ ] **Q:** Do we need barcode/QR code scanning for meter identification?
- [ ] **Q:** Should we use native mobile features? (camera, geolocation, push notifications)

### 5. Offline Capability (Future)

- [ ] **Q:** What data needs to be cached for offline use? (meter list, recent readings?)
- [ ] **Q:** How do we handle sync conflicts? (last-write-wins? manual resolution?)
- [ ] **Q:** Should offline be a Progressive Web App (PWA) or native mobile app?

### 6. API Design

- [ ] **Q:** Do we need new endpoints, or can we extend existing ones?
- [ ] **Q:** Should meter records API be separate from reporting API?
- [ ] **Q:** Do we need real-time updates (WebSockets) for approval workflow?
- [ ] **Q:** **CRITICAL - OCR API:** Should OCR be synchronous (wait for result) or asynchronous (queue + callback)?
- [ ] **Q:** **CRITICAL - OCR API:** What's the expected processing time? (affects UX design)
- [ ] **Q:** **CRITICAL - OCR API:** Do we need image storage? (for audit trail, re-processing)

### 7. Integration with Reporting

- [ ] **Q:** How are manual meter readings used in reports? (merged with digital meter data?)
- [ ] **Q:** Should reports show which readings are manual vs digital?
- [ ] **Q:** Do unapproved readings appear in reports?

---

## Potential Issues & Considerations

### 1. **Authentication & Authorization**

- **Issue:** Need to map Cognito user groups to database `user_group` values
- **Solution:** Backend API should validate user role from JWT token claims
- **Action:** Ensure Cognito groups match database `user_group` values

### 2. **Data Access Control**

- **Issue:** Encoders/approvers need filtered data (only their meters)
- **Solution:** Backend API must filter based on user's client/tenant assignments
- **Action:** Create API endpoints that respect user permissions

### 3. **Navigation Confusion**

- **Issue:** Users might accidentally access wrong section
- **Solution:**
  - Clear role-based redirects after login
  - Hide navigation items user can't access
  - Show clear "You don't have access" messages

### 4. **URL Sharing**

- **Issue:** Users might share URLs to sections they shouldn't access
- **Solution:** Server-side or middleware route protection
- **Action:** Implement route guards that check user role

### 5. **Mobile-First Design & PWA**

- **Issue:** Mobile-first design needs different considerations than desktop
- **Solution:**
  - Use mobile-first Tailwind approach (default mobile, `md:` breakpoint for desktop)
  - Implement PWA features (service workers, offline storage)
  - Design for touch interactions (large tap targets, swipe gestures)
  - Consider camera access for photo uploads
  - Implement offline-first architecture from the start
- **Action:**
  - Create separate layout component for `/meters`
  - Use IndexedDB or localStorage for offline data
  - Implement sync queue for offline submissions

### 6. **Code Splitting & Bundle Size**

- **Issue:** Mobile users shouldn't download desktop reporting code
- **Solution:**
  - Route-based code splitting (Next.js dynamic imports)
  - Lazy load reporting components for meter users
  - Separate CSS bundles per route if possible
- **Action:** Use Next.js `dynamic()` imports for reporting components

### 7. **Database Schema**

- **Status:** Schema now uses `meters` and `unit_meters_history` consistently
- **Solution:** Clarify naming - use actual table names from schema
- **Action:** Verify table names match user's expectations

---

## Implementation Phases

### Phase 1: Foundation & Mobile Layout (Week 1)

1. Add new user roles to database (`encoder`, `tenant_approver`)
2. Update Cognito groups to include new roles
3. Create route protection middleware
4. Create `/meters` route with **mobile-first layout** (separate from AppShell)
5. Implement role-based redirects after login
6. Set up route-based code splitting
7. Design mobile-first UI components (buttons, inputs, navigation)

### Phase 2: Backend API (Week 1-2)

1. Create API endpoints for meter data:
   - `GET /meters` - List meters (filtered by user role)
   - `GET /meters/:id` - Get meter details
   - `POST /meters/records` - Create meter record
   - `GET /meters/records` - List meter records
   - `PUT /meters/records/:id` - Update record (if allowed)
   - `POST /meters/records/:id/approve` - Approve record (tenant_approver)
   - `POST /meters/ocr` - Process meter image (server-side OCR, **for future release**)
2. Implement data filtering based on user role
3. Add validation (e.g., prevent negative readings, validate meter exists)
4. **OCR Endpoint (Future):**
   - Accept image upload (multipart/form-data)
   - Process OCR (Python: Tesseract, EasyOCR, AWS Textract)
   - Return OCR results (reading value, confidence score)
   - Store image for audit trail
   - **Note:** Option 2 already supports this - just add endpoint when needed

### Phase 3: Frontend - Mobile Meter List (Week 2)

1. Create mobile-first meter list page
2. Implement touch-optimized filtering/search (by building, unit, meter_ref)
3. Show meter details (description, current unit, last reading) in mobile-friendly cards
4. Add large, touch-friendly "Log Reading" button/action
5. Implement swipe gestures if needed
6. Add pull-to-refresh functionality

### Phase 4: Frontend - Mobile Record Entry (Manual Entry, No OCR) (Week 2-3)

1. Create mobile-first meter record entry form
2. **Manual Entry Fields:**
   - Meter reading (numeric input, large touch-friendly)
   - timestamp (date/time picker, or extract from image metadata if photo taken)
3. **Optional: Photo Capture (for future OCR, not processed in v1):**
   - Add camera button (optional, for reference photos)
   - Use web camera API (`getUserMedia`) - already supported in Option 2
   - Store photo with record (for audit trail)
   - Extract timestamp from image metadata (EXIF data)
   - Photo is NOT processed for OCR in v1
4. Add validation (timestamp, reading value, prevent negative readings)
5. Implement submit and error handling
6. Show success/error messages (mobile-friendly notifications)
7. **Offline Support:**
   - Implement offline queue for submissions (IndexedDB/localStorage)
   - Service worker for offline capability
   - Sync queue when online
8. Add haptic feedback for mobile interactions
9. **Future OCR Preparation:**
   - Design form to easily add OCR results later
   - Store photos for future OCR processing
   - Keep manual entry as fallback
   - **Note:** Online OCR can be added later without architecture changes (just add backend endpoint)

### Phase 5: Frontend - Approval Workflow (Week 3)

1. Create approval interface for tenant_approvers
2. Show pending records
3. Implement approve/reject actions
4. Add approval status indicators

### Phase 6: Testing & Refinement (Week 4)

1. Test with real users
2. Refine UI/UX based on feedback
3. Add any missing features
4. Performance optimization

---

## Next Steps

1. **✅ Critical questions answered** (manual entry, no OCR in v1, timestamp from metadata)
2. **✅ Architecture decision: Option 2 (Web App)** - Recommended for manual entry
3. **Confirm table names** (`meters`, `unit_meters_history`, etc.)
4. **Cognito Configuration:**
   - ✅ Reuse existing User Pool (no change)
   - ✅ Reuse existing Client ID OR create new one (15-30 min)
   - ✅ Set redirect URI based on user role
5. **Create detailed API specification:**
   - `GET /meters` - List meters (filtered by user role)
   - `POST /meters/records` - Create meter record (manual entry)
   - `GET /meters/records` - List meter records
   - `PUT /meters/records/:id` - Update record
   - `POST /meters/records/:id/approve` - Approve record (tenant_approver)
6. **Design mobile-first UI mockups** for meter logging interface
7. **Set up development environment:**
   - Create `/meters` route in existing Next.js app
   - Set up PWA capabilities (service workers, offline support)
   - Set up mobile testing (real devices)
8. **Plan for future OCR:**
   - Design form to easily add OCR later
   - Store photos with records (for future OCR)
   - Keep manual entry as fallback
9. **Plan for future native mobile app (if needed):**
   - Design API to work for both web and mobile
   - Keep backend API separate from frontend
   - Native app can be built later (React Native, Flutter, etc.)
   - Option 2 vs Option 3 doesn't affect native mobile app development
10. **Start Phase 1 implementation**

---

## References

- Database Schema: `backend/docs/DATABASE_SCHEMA.md`
- Current Auth: `website/app/providers/OidcProvider.tsx`
- Current API: `backend/api.py`
- Current Reports Page: `website/app/reports/page.tsx`
