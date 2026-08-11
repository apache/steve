# TODO: Review and Fixes for v3/server/pages.py

Based on a review of `v3/server/pages.py` (and related templates like `voter.ezt`), here are the identified issues, errors, and areas for improvement. These focus on correctness, logic, security, and completeness, while adhering to project conventions (minimal changes, no unsolicited refactors). Prioritized by impact.

## 1. Missing Endpoints for Date Saving (Critical) - RESOLVED
- **Issue**: The `manage.ezt` template includes JavaScript that makes POST requests to `/do-set-open_at/<eid>` and `/do-set-close_at/<eid>` for auto-saving open/close dates. These endpoints were not defined in `pages.py`, causing the auto-save functionality to fail (likely with 404 errors).
- **Impact**: Users won't be able to save dates via the UI, breaking the intended workflow.
- **Resolution**: Added the two endpoints with a refactored helper function `_set_election_date` to handle common logic (auth, JSON parsing, validation, setting dates, logging, and response). Endpoints now require authentication, validate dates, and log actions. CSRF handling remains a TODO (placeholder token in use). Test for proper date-setting and error handling. Added supporting methods `set_open_at` and `set_close_at` to the Election class in `election.py`, and corresponding cursors in `queries.yaml`.

## 2. Upcoming Elections Not Populated in `voter_page()` - RESOLVED
- **Issue**: The `voter.ezt` template checks for `[if-any upcoming]` and loops over `upcoming` elections, but `voter_page()` only sets `result.election` (for open elections). `result.upcoming` is never defined, so the "Upcoming Elections" section will always be empty.
- **Impact**: Upcoming elections (e.g., those in 'editable' state with a future open date) won't display, confusing users.
- **Resolution**: Added a new Election class method `upcoming_to_pid` to return editable elections for a given PID with voting eligibility. Added corresponding query `q_upcoming_to_me` in `queries.yaml`. Updated `voter_page()` to fetch and post-process upcoming elections into `result.upcoming`. Updated `voter.ezt` to include a dedicated "Upcoming Elections" section with similar card layout, a "Preview Ballot" link, and subtle visual distinction (lighter background, "Upcoming" badge). No filtering on `open_at` (all editable elections included).

## 3. Hardcoded `vtype` in `do_add_issue_endpoint()`
- **Issue**: `vtype` is hardcoded to `'yna'`, and `kv = None`. The comment mentions handling SEATS for STV, but it's not implemented. If users try to add STV issues, it will fail or behave incorrectly.
- **Impact**: Limits issue types; STV issues can't be added properly.
- **Suggested Fix**: Make `vtype` dynamic (e.g., from form data). For STV, parse `seats` from the form and set `kv = {'seats': int(form.seats)}` or similar. Update the template's form to include a vtype selector and STV-specific fields.

## 4. Debug Prints in Endpoints
- **Issue**: `print('FORM:', form)` in `do_add_issue_endpoint()` and `do_edit_issue_endpoint()` is leftover debug code.
- **Impact**: Clutters logs/output; not production-ready.
- **Suggested Fix**: Remove these `print` statements.

## 5. Temporary `issue_count` Hack in `postprocess_election()`
- **Issue**: `if 'issue_count' not in e: e.issue_count = 5` is a hardcoded placeholder.
- **Impact**: Incorrect counts; should be removed once the query is fixed.
- **Suggested Fix**: Ensure the Election query/class includes `issue_count` properly, then remove this.

## 6. CSRF Token Placeholder
- **Issue**: `basic.csrf_token = 'placeholder'` is not secure.
- **Impact**: CSRF protection is bypassed.
- **Suggested Fix**: Implement real CSRF tokens (e.g., generate a random token per session and verify in POST endpoints).

## 7. Other Minor Notes
- **Authz Checks**: Many endpoints have `### check authz` comments but no implementation. If authorization beyond basic auth is needed, add it (e.g., ensure the user owns the election).
- **Error Handling**: Endpoints like `do_open_endpoint()` assume success; add try/except for potential Election class errors.
- **Logging**: Consistent and useful; no issues.
- **Imports/Constants**: All seem correct and follow conventions.
- **No Obvious Syntax/Logic Errors**: The code parses and runs logically, but the above are functional gaps.

If you'd like to implement any of these fixes (e.g., add the date endpoints or fix upcoming elections), provide confirmation and details. Let me know if you have more context or want to check specific sections!

## 8. CSRF Checking
- **Issue**: CSRF tokens are placeholders and not validated in POST endpoints.
- **Impact**: Vulnerable to CSRF attacks.
- **Suggested Fix**: Implement a decorator to check CSRF tokens on POST endpoints (e.g., compare form/session token). Generate real tokens per session.

## 9. Error Handling in `submitFormWithLoading`
- **Issue**: If the server returns an error during form submission via `submitFormWithLoading`, the page doesn't reload, and the button stays disabled, potentially confusing users.
- **Impact**: Poor UX on submission failures.
- **Suggested Fix**: Investigate and add client-side error handling (e.g., re-enable button on failure, show error message).
