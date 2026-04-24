# src

Shared Python code used across request folders.

## Folders

- `common/`: generic utilities reused by multiple requests.
- `connectors/`: API/system clients (Mixpanel today, extensible for other sources).

## Notes

- Keep request-specific business logic in `projects/<request>/`.
- Keep reusable, source-agnostic helpers in `src/common/`.
- Add new upstream integrations as separate modules in `src/connectors/`.
