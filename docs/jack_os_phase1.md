# Jack OS Phase 1

This branch starts a safe personal adaptation layer.

## Current change set

- Add a standalone draft tool registry.
- Add standalone rule helpers.
- Add a small helper API under `/api/jack-os`.
- Add standalone rule tests.
- Add helper API tests.
- Add a manual GitHub Actions workflow for the rule and API tests.
- Keep the original app behavior mostly unchanged.

## Files

- backend_api_python/app/services/jack_personal_os_registry.py
- backend_api_python/app/services/jack_personal_os_rules.py
- backend_api_python/app/routes/jack_os_api.py
- backend_api_python/tests/test_jack_personal_os_rules.py
- backend_api_python/tests/test_jack_os_api.py
- .github/workflows/jack-os-tests.yml

## Helper endpoints

- GET `/api/jack-os/tools`
- POST `/api/jack-os/grade-setup`
- POST `/api/jack-os/risk-decision`

These endpoints require the existing login guard.

## Safety checks

- No broker connection changes.
- No auto-trading path.
- No database schema changes.
- No deployment change.
- New API returns planning/risk helper output only.
- Tool registry entries stay disabled by default.

## Phase 1 goal

Create a personal decision-support layer that can be tested separately before deeper integration.

## Next UI plan

1. Add a simple Jack OS page/card that reads `/api/jack-os/tools`.
2. Show tools as disabled modules first: Market Data, Abu Setup Engine, Risk Checker, Journal, Learning Engine.
3. Add a setup score form that calls `/api/jack-os/grade-setup`.
4. Add a risk decision form that calls `/api/jack-os/risk-decision`.
5. Keep all actions read-only until manual approval rules are designed.

## Next Agent Registry plan

1. Keep `jack_personal_os_registry.py` as the single source of truth for tool/module status.
2. Add fields later for required inputs, output schema, and manual approval requirement.
3. Only expose enabled read-only tools first.
4. Never expose broker/order tools until a separate safety review.

## Not in scope

- UI rewrite
- deployment change
- broker connection changes
- database schema changes
- live trading execution

## Next safe step

Run the manual GitHub Actions workflow, then test the helper API locally after `git pull` and a backend restart.
