---
description: Safe release process: Check errors/warnings, run tests, bump version, and push to GitHub.
---

Follow this process EXACTLY when the user asks to "push" or "release" changes.

1. **Pre-Flight Checks (Static Analysis)**
   Run checks to identify potential errors or warnings.
   ```bash
   # CI uses strict mode on all files, so we must too:
   ./.venv/bin/mypy --strict incode.py src/
   ```
   *Fix any errors found before proceeding.*

2. **Run Tests (Verification)**
   Ensure logic is correct and no regressions were introduced.
   ```bash
   ./.venv/bin/pytest
   ```
   *If tests fail, STOP and fix them.*

3. **Check Runtime Health**
   Quickly verify the app creates its help menu without crashing.
   ```bash
   ./.venv/bin/python3 incode.py --help
   ```

4. **Bump Version**
   If all checks pass:
   - Read `src/config.py` to see the current `VERSION`.
   - Increment the patch version (e.g., 2.17.0 -> 2.17.1) or minor version as appropriate for the changes.
   - Update the `VERSION` variable in `src/config.py`.
   - **Update README.md**:
     - Find the badge URL: `https://img.shields.io/badge/version-X.Y.Z-blue.svg`
     - Update the version number to match `src/config.py`.

5. **Push to GitHub**
   Commit and push the changes properly.
   ```bash
   git add .
   git commit -m "feat: <Meaningful description of changes>"
   git push
   ```

6. **Notification**
   Inform the user that checks passed, version was bumped, and code is live.
