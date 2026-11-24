# DownloadYTLocalWeb

## Convenciones

- Identificadores del código (variables, funciones, clases, endpoints) en inglés, siguiendo la convención de cada lenguaje (snake_case en Python, camelCase en TypeScript).
- Comentarios y docstrings en español: el proyecto también sirve para aprender, y el autor lee mejor en español.
- Interfaz, glosario, ADRs y documentación en español.
- Usa el vocabulario de `GLOSSARY.md` también en el código (p. ej. Análisis → `analysis`, Descarga → `download`, Opción de calidad → `quality_option`).
- Mantén `docs/arquitectura.md` al día cuando un cambio altere las piezas, el recorrido o los estados que describe.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for Kokon4/DonwloadYTLocalWeb, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
