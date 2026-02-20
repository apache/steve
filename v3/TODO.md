# TODO: Review and Fixes for v3/server/pages.py

Based on a review of `v3/server/pages.py` (and related templates like `voter.ezt`), here are the identified issues, errors, and areas for improvement. These focus on correctness, logic, security, and completeness, while adhering to project conventions (minimal changes, no unsolicited refactors). Prioritized by impact.

## 1. Missing Endpoints for Date Saving (Critical)
- **Issue**: The `manage.ezt` template includes JavaScript that makes POST requests to `/do-set-open_at/<eid>` and `/do-set-close_at/<eid>` for auto-saving open/close dates. These endpoints are not defined in `pages.py`, causing the auto-save functionality to fail (likely with 404 errors).
- **Impact**: Users won't be able to save dates via the UI, breaking the intended workflow.
- **Suggested Fix**: Add these two endpoints. They should:
  - Require authentication (e.g., `@asfquart.auth.require({R.committer})`).
  - Use the `@load_election` decorator to load the election.
  - Parse the JSON body for a 'date' field (expecting a string like 'YYYY-MM-DD').
  - Validate the date (e.g., ensure it's a valid date string and in the future for open_at/close_at).
  - Update the election's `open_at` or `close_at` via the Election class (assuming it has methods like `set_open_at(date)` or direct attribute setting).
  - Handle CSRF (the JS sends 'X-CSRFToken' header; verify it matches the session's token).
  - Return 204 on success (no content, as it's auto-save). On failure, return 400/500 with an error message.
  - Log the action (e.g., `_LOGGER.info(f'User[U:{result.uid}] updated {field} for election[E:{election.eid}]')`).
  - No flash messages needed for auto-save, but consider error handling in the JS (already partially done).
- **Example Implementation Sketch** (add near the other `/do-*` endpoints; keep it minimal):
  ```python
  @APP.post('/do-set-open_at/<eid>')
  @asfquart.auth.require({R.committer})
  @load_election
  async def do_set_open_at_endpoint(election):
      result = await basic_info()
      # TODO: Check authz if needed
      data = await quart.request.get_json()
      date_str = data.get('date')
      if not date_str:
          quart.abort(400, 'Missing date')
      # Validate date (basic check)
      try:
          dt = datetime.datetime.fromisoformat(date_str).date()
      except ValueError:
          quart.abort(400, 'Invalid date format')
      # Assume Election has a method to set it
      election.set_open_at(dt)  # Or direct: election.open_at = dt.timestamp()
      _LOGGER.info(f'User[U:{result.uid}] set open_at for election[E:{election.eid}] to {date_str}')
      return '', 204

  @APP.post('/do-set-close_at/<eid>')
  @asfquart.auth.require({R.committer})
  @load_election
  async def do_set_close_at_endpoint(election):
      # Similar to above, but for close_at
      result = await basic_info()
      # TODO: Check authz
      data = await quart.request.get_json()
      date_str = data.get('date')
      if not date_str:
          quart.abort(400, 'Missing date')
      try:
          dt = datetime.datetime.fromisoformat(date_str).date()
      except ValueError:
          quart.abort(400, 'Invalid date format')
      election.set_close_at(dt)
      _LOGGER.info(f'User[U:{result.uid}] set close_at for election[E:{election.eid}] to {date_str}')
      return '', 204
  ```
- **Notes**: 
  - Confirm if the Election class supports setting dates (check `steve.election.Election`). If not, you may need to add methods there.
  - For editable elections, ensure open_at/close_at can be set; for open elections, only close_at.
  - Test CSRF: The `basic_info()` sets `csrf_token = 'placeholder'`, so implement real CSRF generation/verification (e.g., via a library or session) before deploying.

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
