# Jack OS Phase 1

This branch starts a safe personal adaptation layer.

## Current change set

- Add a standalone draft tool registry.
- Add standalone rule helpers.
- Do not import the new modules into the running app yet.
- Do not change existing app behavior.

## Files

- backend_api_python/app/services/jack_personal_os_registry.py
- backend_api_python/app/services/jack_personal_os_rules.py

## Phase 1 goal

Create a personal decision-support layer that can be tested separately before integration.

## Not in scope

- UI rewrite
- deployment change
- broker connection changes
- existing route changes
- existing database changes

## Next safe step

Add unit tests for the standalone rule helpers, then decide whether to expose them through a read-only API route.
