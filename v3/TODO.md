# TODO: Review and Fixes for v3/server/pages.py

Based on a review of `v3/server/pages.py` (and related templates like `voter.ezt`), here are the identified issues, errors, and areas for improvement. These focus on correctness, logic, security, and completeness, while adhering to project conventions (minimal changes, no unsolicited refactors). Prioritized by impact.

## 1. Missing Endpoints for Date Saving (Critical) - RESOLVED
- **Issue**: The `manage.ezt` template includes JavaScript that makes POST requests to `/do-set-open_at/<eid>` and `/do-set-close_at/<eid>` for auto-saving open/close dates. These endpoints were not defined in `pages.py`, causing the auto-save functionality to fail (likely with 404 errors).
- **Impact**: Users won't be able to save dates via the UI, breaking the intended workflow.
- **Resolution**: Added the two endpoints with a refactored helper function `_set_election_date` to handle common logic (auth, JSON parsing, validation, setting dates, logging, and response). Endpoints now require authentication, validate dates, and log actions. CSRF handling remains a TODO (placeholder token in use). Test for proper date-setting and error handling. Added supporting methods `set_open_at` and `set_close_at` to the Election class in `election.py`, and corresponding cursors in `queries.yaml`.

## 2. Upcoming Elections Not Populated in `voter_page()`
- **Issue**: The `voter.ezt` template checks for `[if-any upcoming]` and loops over `upcoming` elections, but `voter_page()` only sets `result.election` (for open elections). `result.upcoming` is never defined, so the "Upcoming Elections" section will always be empty.
- **Impact**: Upcoming elections (e.g., those in 'editable' state with a future open date) won't display, confusing users.
- **Suggested Fix**: Modify `voter_page()` to separate elections into `upcoming` and `election` (open ones). Assuming `steve.election.Election.open_to_pid()` returns all relevant elections, filter them:
  - `upcoming`: Elections where `state == 'editable'` and `open_at` is in the future (within `SOON_CUTOFF`).
  - `election`: The rest (open or closed, but template seems to handle closed via `(closed)` text).
  - Add: `result.upcoming = [postprocess_election(e) for e in election if e.state == steve.election.Election.S_EDITABLE and (e.open_at and e.open_at > datetime.datetime.now().timestamp())]`
  - Then, `result.election = [postprocess_election(e) for e in election if e not in result.upcoming]`
  - Update `result.len_election` accordingly.

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

If you'd like to implement any of these fixes (e.g., add the date endpoints or fix upcoming elections), provide confirmation and details. Let me know if you have more context or want me to check specific sections!
