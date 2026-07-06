# Jack OS Phase 1

This branch starts a safe personal adaptation layer.

## Current change set

- Add a standalone draft tool registry.
- Add standalone rule helpers.
- Add a small helper API under `/api/jack-os`.
- Add standalone rule tests.
- Add a manual GitHub Actions workflow for the rule tests.
- Keep the original app behavior mostly unchanged.

## Files

- backend_api_python/app/services/jack_personal_os_registry.py
- backend_api_python/app/services/jack_personal_os_rules.py
- backend_api_python/app/routes/jack_os_api.py
- backend_api_python/tests/test_jack_personal_os_rules.py
- .github/workflows/jack-os-tests.yml

## Helper endpoints

- GET `/api/jack-os/tools`
- POST `/api/jack-os/grade-setup`
- POST `/api/jack-os/risk-decision`

These endpoints require the existing login guard.

## Phase 1 goal

Create a personal decision-support layer that can be tested separately before deeper integration.

## Not in scope

- UI rewrite
- deployment change
- broker connection changes
- database schema changes

## Next safe step

Run the manual GitHub Actions workflow, then test the helper API locally after `git pull` and a backend restart.
