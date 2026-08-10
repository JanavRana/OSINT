# Username OSINT Display and False Positive Fix Summary

## Problems Fixed

### Problem 1: Missing Platform Names in UI
**Symptom**: All username results displayed as generic "Social" type instead of actual platform names (GitHub, Reddit, Instagram, etc.)

**Root Cause**: 
- Backend: `IdentifierRead` schema lacked `platform` and `platform_display_name` fields
- Frontend: Identifier table displayed generic type instead of platform-specific information
- API: Platform information stored in `fact_payload` but not exposed through `/identifiers` endpoint

**Solution**:
1. Added `platform` and `platform_display_name` to `IdentifierRead` schema
2. Updated `/investigations/{id}/identifiers` API to extract platform info from fact metadata
3. Modified frontend `Identifier` type to include platform fields
4. Updated identifier table to display platform name for username results

### Problem 2: False Positive Profile Links
**Symptom**: "View Profile" links generated for non-existent accounts, leading to 404 pages

**Root Cause**:
- Normalizer created facts for ALL detection outcomes (`exists=True`, `exists=False`, `exists="unknown"`)
- Profile URLs generated even when account didn't exist
- Not-found and unknown results became identifiers in the UI

**Solution**:
1. Modified `normalize_username_result()` to only create facts for `exists=True`
2. Not-found (`exists=False`) results are logged but don't create identifiers
3. Unknown (`exists="unknown"`) results are logged but don't create identifiers
4. Profile URLs only generated for confirmed accounts
5. API filters out `exists=False` results before returning identifiers

## Files Changed

### Backend

#### Core Logic
1. **`backend/app/identity/username/normalizer.py`**
   - Changed `normalize_username_result()` to return `None` for `exists != True`
   - Added explicit check: only `exists=True` creates facts
   - Updated docstring to clarify behavior
   - Profile URL only built for confirmed accounts

2. **`backend/app/schemas/investigation.py`**
   - Added `platform: str | None` field to `IdentifierRead`
   - Added `platform_display_name: str | None` field to `IdentifierRead`

3. **`backend/app/api/v1/investigations.py`**
   - Updated `list_identifiers()` to extract platform info from fact metadata
   - Added `"platform_account_found"` to `IDENTIFIER_FACT_TYPES` mapping
   - Filter out `exists=False` results from identifier list
   - Populate platform fields in `IdentifierRead` response

#### Tests
4. **`backend/tests/identity/test_username_normalizer.py`**
   - Updated `test_normalize_not_found_detection()` - now expects `None`
   - Updated `test_normalize_unknown_detection()` - now expects `None`
   - Updated `test_batch_normalization()` - expects only found accounts
   - All 7 tests pass

5. **`backend/tests/identity/test_username_integration.py`**
   - Updated `TestFalsePositiveProtection` class
   - Renamed tests to reflect new behavior
   - `test_explicit_not_found_no_identifier()` - verifies no fact created
   - `test_ambiguous_results_no_identifier()` - verifies no fact created
   - All 12 tests pass

### Frontend

6. **`frontend/src/types/domain.ts`**
   - Added `platform?: string` to `Identifier` interface
   - Added `platformDisplayName?: string` to `Identifier` interface

7. **`frontend/src/routes/investigations.$id.tsx`**
   - Updated `IdentifierTable` component
   - Display `platformDisplayName` for username types instead of generic "username"
   - Maintains username value display
   - Profile links only shown for identifiers with `profileUrl`

## Behavior Changes

### Before
```
Type: Social
Value: testuser
Profile: View Profile (→ 404 if account doesn't exist)
```

### After
```
Type: GitHub
Value: testuser
Profile: View Profile (only shown if account confirmed to exist)

Type: Reddit  
Value: testuser
Profile: View Profile (only shown if account confirmed to exist)
```

## Test Results

### Backend Tests
```bash
$ python -m pytest tests/identity/ -v
===================== 108 passed, 73 warnings in 33.75s ======================
```

Key test coverage:
- ✅ Only `exists=True` creates facts
- ✅ `exists=False` returns `None` (no identifier)
- ✅ `exists="unknown"` returns `None` (no identifier)
- ✅ Batch normalization filters correctly
- ✅ Platform metadata extracted
- ✅ Profile URLs only for confirmed accounts
- ✅ All existing tests still pass

### Frontend Tests
```bash
$ npx tsc --noEmit
Exit Code: 0
```

TypeScript compilation successful with no errors.

## API Contract Changes

### GET /api/v1/investigations/{id}/identifiers

**Before**:
```json
{
  "items": [
    {
      "id": "uuid",
      "type": "username",
      "value": "testuser",
      "confidence": 0.85,
      "sources": 1,
      "first_seen": "2026-08-09T...",
      "profile_url": "https://github.com/testuser"
    }
  ]
}
```

**After** (with platform info):
```json
{
  "items": [
    {
      "id": "uuid",
      "type": "username",
      "value": "testuser",
      "confidence": 0.85,
      "sources": 1,
      "first_seen": "2026-08-09T...",
      "profile_url": "https://github.com/testuser",
      "platform": "github",
      "platform_display_name": "GitHub"
    }
  ]
}
```

**Note**: Not-found and unknown results are no longer included in response.

## Detection Strategy Correctness

The detection strategies already correctly determine `exists` status:

1. **status_code**: `200` = exists, `404` = not found, other = unknown
2. **json_api**: Field present = exists, 404 or field missing = not found
3. **graphql**: Data present = exists, errors or null = not found
4. **HTTP errors**: Timeouts, 403, 503 = unknown (not false positives)

The fix ensures these correct detection outcomes are properly reflected:
- ✅ Confirmed accounts (`exists=True`) → become identifiers with profile links
- ✅ Not found (`exists=False`) → logged but not shown as identifiers
- ✅ Unknown (`exists="unknown"`) → logged but not shown as identifiers

## Impact on Existing Features

### Preserved ✅
- Domain identifier display unchanged
- Email identifier display unchanged  
- Phone identifier display unchanged
- Other connector execution unchanged
- Detection strategies unchanged
- Platform definitions unchanged
- Confidence calculation unchanged
- Graph integration unchanged
- Timeline integration unchanged

### Enhanced ✅
- Username results now show actual platform names
- False positive profile links eliminated
- Cleaner identifier list (only confirmed accounts)
- Better user experience - no 404 links

## Limitations & Future Work

1. **Multiple platform occurrences**: If same username found on multiple platforms, each creates separate identifier row (current behavior, acceptable)

2. **Platform metadata**: Requires PlatformDefinition during normalization for display names. Falls back to plugin_id if not available.

3. **Historical data**: Existing facts with `exists=False` in database won't automatically disappear (migration could clean up if needed)

4. **API versioning**: No breaking change - added optional fields, backward compatible

## Manual Testing Checklist

To manually verify the fix:

1. **Create investigation** with username identifier
2. **Execute investigation** - run username OSINT
3. **Check identifier table**:
   - ✅ Platform names visible (GitHub, Reddit, etc.)
   - ✅ Username value preserved  
   - ✅ Only confirmed accounts have "View Profile"
   - ✅ No false positive 404 links
4. **Click "View Profile"** - should load actual profile page
5. **Check logs** - should see not-found results logged but not persisted
6. **Test with real username** - e.g., a known public GitHub username

## Conclusion

Both issues are now resolved:
- **Problem 1 (Platform Names)**: Fixed by adding platform fields to API and frontend
- **Problem 2 (False Positives)**: Fixed by only creating facts for `exists=True`

All tests pass, TypeScript compiles, and the solution maintains backward compatibility while improving accuracy and user experience.
