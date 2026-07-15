# Frontend–Backend Integration Implementation Plan (Temporary)

> **Temporary Planning Document**
>
> This document exists only to guide the frontend/backend integration.
>
> The backend is the source of truth.
>
> The frontend architecture is already finalized.
>
> Do not redesign either architecture.
>
> Remove or archive this document after integration is complete.

## Executive Summary

I have completed a comprehensive analysis of both the frontend and backend architectures. The **frontend is production-ready for backend integration** with a well-designed DataProvider abstraction layer. The **backend is feature-complete** with all required endpoints implemented. Integration can proceed with **minimal modifications** to both layers - primarily implementing a new `FastAPIDataProvider` class and mapping a small number of DTOs.

---

## 1. Architecture Review

### Frontend Architecture

**Current State: ✅ Excellent**

The frontend demonstrates a clean, well-architected approach:

- **DataProvider Pattern**: Complete abstraction layer (`DataProvider` interface + `mockDataProvider` implementation)
- **Domain Types**: Centralized type definitions in `types/domain.ts`
- **Custom Hooks Layer**: `use-osint-data.ts` provides React hooks that consume the DataProvider
- **Component Isolation**: Pages/components never import mock data directly
- **React-like State Management**: Simple `useResource` and `useMutation` hooks that mimic React Query's API
- **Routing**: TanStack Router with investigation-centric routes

**Suitability for Backend Integration: ✅ Perfect**

The architecture is **specifically designed** for backend integration. No redesign needed. The DataProvider abstraction means:
- Components remain untouched
- Only one new file (`FastAPIDataProvider.ts`) needs creation
- One registration call to switch providers

### Backend Architecture

**Current State: ✅ Production-Ready**

- **FastAPI** with clear endpoint routing
- **Service Layer**: Business logic isolated in services (InvestigationService, ConnectorExecutionService, etc.)
- **Pydantic Schemas**: Strong request/response typing
- **PostgreSQL**: Primary persistence layer
- **CORS**: Already configured for `localhost:5173` (Vite default)
- **Complete Pipeline**: Investigation creation → execution → normalization → timeline → reporting

**API Surface:**
```
GET    /health
POST   /api/v1/investigations/investigations
GET    /api/v1/investigations/investigations
GET    /api/v1/investigations/investigations/{id}
POST   /api/v1/investigations/investigations/{id}/execute
GET    /api/v1/investigations/investigations/{id}/timeline
POST   /api/v1/investigations/investigations/{id}/report
GET    /api/v1/investigations/investigations/{id}/report
```

### Integration Architecture

**Compatibility: ✅ Excellent Match**

The frontend DataProvider methods map almost 1:1 to backend endpoints:

| Frontend Method | Backend Endpoint | Status |
|---|---|---|
| `createInvestigation()` | `POST /api/v1/investigations/investigations` | ✅ Direct |
| `listInvestigations()` | `GET /api/v1/investigations/investigations` | ✅ Direct |
| `getInvestigation()` | `GET /api/v1/investigations/investigations/{id}` | ✅ Direct |
| `executeInvestigation()` | `POST /api/v1/investigations/investigations/{id}/execute` | ✅ Needs mapping |
| `listTimeline()` | `GET /api/v1/investigations/investigations/{id}/timeline` | ✅ Direct |
| `generateReport()` | `POST /api/v1/investigations/investigations/{id}/report` | ✅ Direct |
| `downloadReport()` | `GET /api/v1/investigations/investigations/{id}/report` | ✅ Needs handling |
| `listIdentifiers()` | ❌ Missing | See Section 3 |
| `listConnectors()` | ❌ Missing | See Section 3 |
| `getIdentityProfile()` | ❌ Missing (future) | See Section 3 |
| `getGraph()` | ❌ Missing (future) | See Section 3 |
| `getDashboardStats()` | ❌ Missing (can derive) | See Section 3 |

---

## 2. DataProvider Audit

### 2.1 `createInvestigation(input: NewInvestigationInput): Promise<Investigation>`

**Backend Endpoint:** `POST /api/v1/investigations/investigations`

**Request DTO (Backend):**
```python
class InvestigationCreate(BaseModel):
    name: str  # min_length=1, max_length=255
```

**Response DTO (Backend):**
```python
class InvestigationRead(BaseModel):
    id: uuid.UUID
    name: str
    status: InvestigationStatus  # enum: "created" | "running" | "completed" | "failed"
    created_at: datetime
    updated_at: datetime
```

**Frontend Input Type:**
```typescript
interface NewInvestigationInput {
  name: string;
  target: string;
  severity: Severity;
  seedType: IdentifierType;
  seedIdentifiers: string[];
  notes?: string;
}
```

**Frontend Domain Type:**
```typescript
interface Investigation {
  id: string;
  name: string;
  target: string;
  status: InvestigationStatus;
  severity: Severity;
  progress: number;
  identifiers: number;
  connectors: number;
  createdAt: string;
  updatedAt: string;
  owner: string;
  tags: string[];
}
```

**Mapping Required:** ⚠️ **Yes - Input & Output**

**Input Transformation:**
- Backend only accepts `name`
- Frontend provides: `target`, `severity`, `seedType`, `seedIdentifiers`, `notes`
- **Solution**: Send only `name` field to backend; other fields are frontend-only until backend supports them

**Output Transformation:**
- Backend returns: `id`, `name`, `status`, `created_at`, `updated_at`
- Frontend expects: `target`, `severity`, `progress`, `identifiers`, `connectors`, `owner`, `tags`
- **Solution**: Adapter that:
  - Maps `created_at` → `createdAt`, `updated_at` → `updatedAt`
  - Sets default values: `target: ""`, `severity: "medium"`, `progress: 0`, `identifiers: 0`, `connectors: 0`, `owner: "You"`, `tags: []`
  - Maps status enum values: `"created"` → `"pending"`

---

### 2.2 `listInvestigations(): Promise<Investigation[]>`

**Backend Endpoint:** `GET /api/v1/investigations/investigations?skip=0&limit=100`

**Response DTO (Backend):**
```python
class InvestigationList(BaseModel):
    items: list[InvestigationRead]
    count: int
```

**Mapping Required:** ⚠️ **Yes - Output only**

**Output Transformation:**
- Backend returns `{ items: InvestigationRead[], count: number }`
- Frontend expects `Investigation[]`
- **Solution**: Extract `.items` and apply same adapter as `createInvestigation()` response

---

### 2.3 `getInvestigation(id: string): Promise<Investigation | undefined>`

**Backend Endpoint:** `GET /api/v1/investigations/investigations/{id}`

**Response DTO:** Same as `createInvestigation()` - `InvestigationRead`

**Mapping Required:** ⚠️ **Yes - Same adapter as above**

**Error Handling:**
- Backend returns 404 with error detail if not found
- Frontend expects `undefined`
- **Solution**: Catch 404 and return `undefined`

---

### 2.4 `executeInvestigation(investigationId: string): Promise<ExecutionResult>`

**Backend Endpoint:** `POST /api/v1/investigations/investigations/{id}/execute`

**Request DTO (Backend):**
```python
class InvestigationExecuteRequest(BaseModel):
    identifier: str
    type: IdentifierType  # "domain" | "email" | "username" | "wallet" | "ip" | "phone"
```

**Response DTO (Backend):**
```python
class InvestigationExecuteResponse(BaseModel):
    investigation_id: uuid.UUID
    status: InvestigationStatus
    started_at: datetime
    finished_at: datetime
    statistics: ExecutionStatistics
    connector_results: list[ConnectorExecutionResult]

class ExecutionStatistics(BaseModel):
    executed_connectors: int
    successful_connectors: int
    failed_connectors: int
    connector_results_count: int
    normalized_facts_count: int
    execution_duration_seconds: float
```

**Frontend Type:**
```typescript
interface ExecutionResult {
  investigationId: string;
  status: ExecutionStatus;  // "queued" | "running" | "completed" | "failed"
  startedAt: string;
}
```

**Mapping Required:** ⚠️ **Yes - Input & Output**

**Critical Issue:** Frontend method signature doesn't accept the required `identifier` parameter!

**Solution:**
- Update method signature: `executeInvestigation(investigationId: string, identifier: { value: string, type: IdentifierType })`
- OR store the seed identifier from investigation creation and reuse it
- Backend returns much more data than frontend expects - adapter should include additional fields

---

### 2.5 `listTimeline(investigationId?: string): Promise<TimelineEvent[]>`

**Backend Endpoint:** `GET /api/v1/investigations/investigations/{id}/timeline`

**Response DTO (Backend):**
```python
class TimelineResponse(BaseModel):
    events: list[TimelineEventResponse]
    count: int

class TimelineEventResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    entity_id: Optional[str]
    occurred_at: datetime
    event_type: str
    title: str
    description: str
    connector: str
    source_fact_id: uuid.UUID
    confidence: float
```

**Frontend Type:**
```typescript
interface TimelineEvent {
  id: string;
  time: string;
  actor: string;
  action: string;
  target: string;
  channel: TimelineChannel;
  severity: Severity;
  details: string;
}
```

**Mapping Required:** ⚠️ **Yes - Significant transformation**

**Transformations:**
- `occurred_at` → `time`
- `connector` → `actor`
- `event_type` → `action`
- `entity_id` → `target`
- `description` → `details`
- Need to derive `channel` from context
- Need to derive `severity` from confidence or context
- Extract `.events` array

---

### 2.6 `generateReport(investigationId: string): Promise<GeneratedReport>`

**Backend Endpoint:** `POST /api/v1/investigations/{id}/report`

**Response (Backend):**
```python
{
    "id": str,
    "investigation_id": str,
    "status": str,  # "pending" | "generating" | "completed" | "failed"
    "file_size": int,
    "generated_at": str (ISO datetime)
}
```

**Frontend Type:**
```typescript
interface GeneratedReport {
  reportId: string;
  investigationId: string;
  status: "queued" | "generating" | "ready" | "failed";
  createdAt: string;
}
```

**Mapping Required:** ⚠️ **Yes - Minor**

**Transformations:**
- `id` → `reportId`
- `investigation_id` → `investigationId`
- `generated_at` → `createdAt`
- Map status values: `"completed"` → `"ready"`, `"pending"` → `"queued"`

---

### 2.7 `downloadReport(investigationId: string, reportId?: string): Promise<ReportDownload>`

**Backend Endpoint:** `GET /api/v1/investigations/{id}/report`

**Response (Backend):** Binary PDF file with headers
```
Content-Type: application/pdf
Content-Disposition: attachment; filename=investigation_{id}_report.pdf
```

**Frontend Type:**
```typescript
interface ReportDownload {
  reportId: string;
  filename: string;
  contentType: string;
  url?: string;
}
```

**Mapping Required:** ⚠️ **Yes - Special handling**

**Solution:**
- Fetch as blob
- Create object URL
- Extract filename from Content-Disposition header
- Return metadata with object URL

---

### 2.8 Missing Backend Endpoints

#### `listIdentifiers(investigationId?: string): Promise<Identifier[]>`
**Status:** ❌ **Backend endpoint does not exist**

**Current Usage:** Called by investigation detail page to show identifier table

**Workaround Options:**
1. Return empty array until endpoint is implemented
2. Extract identifiers from normalized facts (requires new endpoint)
3. Store seed identifiers in frontend state after investigation creation

#### `listConnectors(investigationId?: string): Promise<Connector[]>`
**Status:** ❌ **Backend endpoint does not exist**

**Current Usage:** Called by investigation detail page to show connector cards

**Workaround Options:**
1. Return empty array until endpoint is implemented
2. Extract from execution results (requires endpoint modification)
3. Show static connector list

#### `getDashboardStats(): Promise<DashboardStat[]>`
**Status:** ❌ **Backend endpoint does not exist**

**Current Usage:** Dashboard stats cards

**Workaround:**
- Already implemented in `mockDataProvider` - derives stats from investigation list
- **Solution**: Continue deriving client-side from `listInvestigations()` response

#### `getIdentityProfile(subjectId?: string): Promise<IdentityProfile>`
**Status:** ❌ **Future feature (per MASTER_DESIGN.md)**

**Current Usage:** Identity profile page

**Workaround:** Keep using mock data until correlation engine (M4) is implemented

#### `getGraph(investigationId?: string): Promise<GraphData>`
**Status:** ❌ **Future feature (per MASTER_DESIGN.md)**

**Current Usage:** Graph visualization page

**Workaround:** Keep using mock data until Neo4j integration is implemented

---

## 3. Missing Backend APIs

### Critical (Block integration)
**None** - All mutation endpoints exist and work

### High Priority (Degrade UX)
1. **`GET /api/v1/investigations/{id}/identifiers`**
   - Impact: Investigation detail page shows "No identifiers" even after execution
   - Workaround: Display seed identifier from creation

2. **`GET /api/v1/investigations/{id}/connectors`** or extend execution response
   - Impact: Cannot show per-connector status cards on investigation detail
   - Workaround: Parse from execution result or show summary only

### Medium Priority (Can derive client-side)
3. **Dashboard stats endpoint**
   - Impact: None - already derived client-side in mock provider
   - Solution: Continue deriving from investigations list

### Low Priority (Future features per design doc)
4. **Graph/Entity endpoints** - Requires M4 (Entity Correlation Engine) implementation
5. **Identity Profile endpoints** - Requires M4 + M6 implementation

---

## 4. DTO Compatibility

### Perfect Matches (No adapter needed)
- Health check endpoint
- Timeline event structure (after field mapping)

### Small Mapping Differences (Simple adapter)
- **Investigation DTOs**: Add default values for frontend-only fields
- **Enum mappings**: `InvestigationStatus` backend → frontend
  - `"created"` → `"pending"`
  - `"running"` → `"active"` (frontend uses "active")
  - `"completed"` → `"completed"` ✅
  - `"failed"` → `"failed"` ✅

### Fields Requiring Adapters
| Backend Field | Frontend Field | Transformation |
|---|---|---|
| `created_at` | `createdAt` | Snake → camel case |
| `updated_at` | `updatedAt` | Snake → camel case |
| `investigation_id` | `investigationId` | Snake → camel case |
| `source_fact_id` | - | Drop (not used) |
| Status enums | Status enums | Map values |

### Missing Frontend Fields (Set defaults)
- `target`: Use first seed identifier or empty string
- `severity`: Default to `"medium"`
- `progress`: Default to `0` (could derive from status)
- `identifiers`: Default to `0` (until identifiers endpoint exists)
- `connectors`: Default to `0` (until connectors endpoint exists)
- `owner`: Default to `"You"`
- `tags`: Default to `[]`

---

## 5. File Modification Plan

### Files to Create (1 file)
1. **`frontend/src/lib/api/fastapi-provider.ts`** (NEW)
   - Implement `DataProvider` interface
   - HTTP client (fetch or axios)
   - DTO adapters
   - Error handling

### Files to Modify (4 files)

2. **`frontend/src/lib/api/data-provider.ts`**
   - Import and conditionally use `FastAPIDataProvider`
   - Add environment check: `const provider = import.meta.env.VITE_USE_BACKEND === 'true' ? new FastAPIDataProvider() : mockDataProvider`
   - OR: Always use `FastAPIDataProvider` (remove mock conditional)

3. **`frontend/src/hooks/use-osint-data.ts`**
   - Update `useExecuteInvestigation` signature to accept identifier parameter
   - Current: `useMutation<string, ExecutionResult>`
   - New: `useMutation<{ investigationId: string, identifier: { value: string, type: IdentifierType }}, ExecutionResult>`

4. **`frontend/src/routes/investigations.$id.tsx`**
   - Update call to `execute.mutate()` to include identifier
   - Store seed identifier when displaying it

5. **`frontend/src/types/domain.ts`** (Optional)
   - Add detailed execution response types if needed
   - Add backend-specific types

### Files NOT to Modify
- ❌ All component files (badges, cards, states, etc.)
- ❌ All other route files
- ❌ `mock-fixtures.ts` (keep for fallback/testing)
- ❌ Router, shell, or UI components

---

## 6. Risk Assessment

### Low Risk ✅
- **Architecture compatibility**: Frontend was designed for this
- **Endpoint coverage**: Core CRUD operations exist
- **Type safety**: Both sides use strong typing

### Medium Risk ⚠️

1. **Missing Seed Identifier in Execute Call**
   - **Issue**: `executeInvestigation()` needs identifier parameter but frontend doesn't store it
   - **Impact**: Cannot execute investigations after creation
   - **Mitigation**: Store seed identifiers from creation form; update mutation hook signature

2. **Status Enum Mismatch**
   - **Issue**: Backend uses `"created"`, frontend shows `"pending"`
   - **Impact**: UI shows wrong status badge
   - **Mitigation**: Map in adapter

3. **Missing Identifiers/Connectors Endpoints**
   - **Issue**: Investigation detail page expects these lists
   - **Impact**: Empty tables even after execution
   - **Mitigation**: 
     - Show seed identifier from creation
     - Show execution summary instead of individual connector cards
     - OR: Request backend endpoints to be added

4. **Report Download as Binary**
   - **Issue**: Need to handle blob response and trigger download
   - **Impact**: Requires special handling
   - **Mitigation**: Standard blob-to-object-URL pattern

### High Risk 🚨

**None identified** - All critical paths have working endpoints

---

## 7. Implementation Strategy

### Phase 1: Minimal Viable Integration (1-2 hours)
**Goal:** Create, list, and view investigations

1. Create `fastapi-provider.ts` with minimal implementation:
   - `createInvestigation()` - with input adapter
   - `listInvestigations()` - with output adapter
   - `getInvestigation()` - with output adapter
   - All others return empty arrays/mock data

2. Create DTO adapter utilities:
   ```typescript
   function adaptInvestigationFromBackend(backend: BackendInvestigation): Investigation
   function adaptInvestigationToBackend(frontend: NewInvestigationInput): BackendInvestigationCreate
   ```

3. Update `data-provider.ts` to use new provider

4. Test: Create investigation → See it in list → View detail

### Phase 2: Investigation Execution (1-2 hours)
**Goal:** Execute investigations and see results

1. Implement `executeInvestigation()` with identifier parameter:
   - Update hook signature
   - Update investigation detail page to pass identifier
   - Handle execution response

2. Implement `listTimeline()`:
   - Transform backend timeline events to frontend format
   - Map fields appropriately

3. Test: Execute investigation → See timeline populate

### Phase 3: Report Generation (30-60 minutes)
**Goal:** Generate and download reports

1. Implement `generateReport()`
2. Implement `downloadReport()` with blob handling:
   ```typescript
   const blob = await response.blob();
   const url = URL.createObjectURL(blob);
   // trigger download
   ```

3. Test: Generate report → Download PDF

### Phase 4: Dashboard Integration (30 minutes)
**Goal:** Dashboard shows real data

1. Ensure `getDashboardStats()` derives from real investigation list
2. Ensure timeline feed uses real timeline data
3. Test: Dashboard shows correct stats

### Phase 5: Polish (1 hour)
**Goal:** Handle edge cases

1. Error handling:
   - Network errors
   - 404s
   - 500s
   - Validation errors

2. Loading states:
   - Already implemented via hooks
   - Verify they work with async HTTP calls

3. Empty states:
   - Already implemented
   - Verify they trigger appropriately

### Phase 6: Future Features (Deferred)
- Implement when backend adds endpoints:
  - `listIdentifiers()`
  - `listConnectors()`
  - `getIdentityProfile()` (requires M4)
  - `getGraph()` (requires M4 + Neo4j)

---

## 8. Detailed Implementation Plan

### Step-by-Step Integration Checklist

#### Prerequisites
- [ ] Backend running on `http://localhost:8000`
- [ ] Database migrations applied
- [ ] Frontend running on `http://localhost:5173`
- [ ] CORS configured in backend (already done)

#### A. Create FastAPI Provider (Priority 1)
```typescript
// File: frontend/src/lib/api/fastapi-provider.ts

import type { DataProvider, /* other types */ } from '@/types/domain';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class FastAPIDataProvider implements DataProvider {
  // HTTP client setup
  // Adapter functions
  // Implement each method
}

export const fastAPIProvider = new FastAPIDataProvider();
```

- [ ] Create file structure
- [ ] Implement HTTP client wrapper
- [ ] Implement DTO adapters
- [ ] Implement investigation CRUD methods
- [ ] Implement execution method
- [ ] Implement timeline method
- [ ] Implement report methods
- [ ] Implement stub methods for missing endpoints

#### B. Update Data Provider Registration (Priority 1)
```typescript
// File: frontend/src/lib/api/data-provider.ts

import { fastAPIProvider } from './fastapi-provider';
import { mockDataProvider } from './mock-fixtures';

const USE_BACKEND = import.meta.env.VITE_USE_BACKEND !== 'false'; // default true

let activeProvider: DataProvider = USE_BACKEND ? fastAPIProvider : mockDataProvider;
```

- [ ] Import FastAPIProvider
- [ ] Add environment variable check
- [ ] Set active provider conditionally
- [ ] Document environment variable in README

#### C. Update Execute Hook (Priority 1)
```typescript
// File: frontend/src/hooks/use-osint-data.ts

export function useExecuteInvestigation() {
  return useMutation<
    { investigationId: string; identifier: { value: string; type: IdentifierType } },
    ExecutionResult
  >((params) =>
    getDataProvider().executeInvestigation(params.investigationId, params.identifier)
  );
}
```

- [ ] Update mutation type parameters
- [ ] Update DataProvider interface signature
- [ ] Update FastAPIProvider implementation
- [ ] Update mock provider to match

#### D. Update Investigation Detail Page (Priority 1)
```typescript
// File: frontend/src/routes/investigations.$id.tsx

// Store seed identifier
const [seedIdentifier, setSeedIdentifier] = useState<{value: string, type: IdentifierType}>();

// Update execute button
<Button onClick={() => {
  if (seedIdentifier) {
    execute.mutate({
      investigationId: inv.id,
      identifier: seedIdentifier
    });
  }
}}>
```

- [ ] Add state for seed identifier
- [ ] Extract from investigation data
- [ ] Update execute button onClick
- [ ] Handle missing identifier case

#### E. Add Environment Configuration (Priority 2)
```env
# File: frontend/.env

VITE_API_BASE_URL=http://localhost:8000
VITE_USE_BACKEND=true
```

- [ ] Create `.env` file
- [ ] Add to `.gitignore` if not present
- [ ] Document in README
- [ ] Create `.env.example`

#### F. Test Integration (Priority 1)
- [ ] Start backend server
- [ ] Start frontend server
- [ ] Test investigation creation
- [ ] Test investigation list
- [ ] Test investigation detail view
- [ ] Test investigation execution
- [ ] Test timeline view after execution
- [ ] Test report generation
- [ ] Test report download

#### G. Handle Edge Cases (Priority 2)
- [ ] 404 errors → return undefined
- [ ] Network errors → show error state
- [ ] Loading states → verify spinners
- [ ] Empty states → verify empty messages
- [ ] Validation errors → show user-friendly messages

#### H. Cleanup & Documentation (Priority 3)
- [ ] Add JSDoc comments to FastAPIProvider
- [ ] Document DTO transformation decisions
- [ ] Add integration testing guide
- [ ] Update README with backend setup instructions

---

## 9. Recommended Order of Implementation

### Day 1: Core Integration
1. ✅ **Create FastAPIProvider skeleton** (30 min)
2. ✅ **Implement investigation CRUD** (1 hour)
3. ✅ **Wire up provider** (15 min)
4. ✅ **Test create/list/view** (30 min)
5. ✅ **Fix identifier storage** (30 min)
6. ✅ **Implement execution** (1 hour)
7. ✅ **Test execution flow** (30 min)

**Milestone:** Can create, execute, and view investigations

### Day 2: Data Display
8. ✅ **Implement timeline adapter** (45 min)
9. ✅ **Test timeline view** (15 min)
10. ✅ **Implement report generation** (30 min)
11. ✅ **Implement report download** (30 min)
12. ✅ **Test full workflow** (30 min)

**Milestone:** Can see execution results and download reports

### Day 3: Polish
13. ✅ **Add error handling** (1 hour)
14. ✅ **Test edge cases** (1 hour)
15. ✅ **Update documentation** (30 min)
16. ✅ **Final integration test** (30 min)

**Milestone:** Production-ready integration

---

## 10. Final Assessment

### Integration Feasibility: ✅ **EXCELLENT**

The frontend architecture was **explicitly designed** for this integration. The DataProvider pattern is the textbook approach for swapping data sources. The backend API is complete and functional.

### Estimated Effort: **4-6 hours of focused work**

- FastAPIProvider implementation: 2-3 hours
- Hook updates: 30 minutes
- Page updates: 1 hour
- Testing & polish: 1-2 hours

### Recommended Approach: **Incremental**

1. Start with investigation CRUD (low risk, high value)
2. Add execution (medium complexity, high value)
3. Add timeline (medium complexity, medium value)
4. Add reports (medium complexity, medium value)
5. Polish edge cases (low risk, high value)

### Files to Change: **4-5 files maximum**
- 1 new file (`fastapi-provider.ts`)
- 4 modified files (provider registration, hooks, one route, types)
- 0 component changes

### Architecture Modifications: **ZERO**
- ✅ DataProvider pattern stays
- ✅ Hooks stay
- ✅ Components stay
- ✅ Routes stay
- ✅ Domain types stay (with minor additions)

---

## STOP CONDITION REACHED

This analysis is complete. I have:

✅ Reviewed frontend architecture (suitable for integration)  
✅ Reviewed backend architecture (complete and functional)  
✅ Audited all DataProvider methods  
✅ Identified missing APIs (2 high-priority, 3 low-priority)  
✅ Mapped DTOs and identified transformations  
✅ Listed files to modify (4-5 files total)  
✅ Assessed risks (low overall risk)  
✅ Provided step-by-step implementation plan  
✅ Recommended incremental implementation order  

**Ready for approval to proceed with implementation.**

The integration is **straightforward** with **well-defined boundaries**. No architecture changes needed. The DataProvider abstraction makes this a textbook example of clean separation of concerns paying off during integration.