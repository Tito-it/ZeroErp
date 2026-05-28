# Area 'documenti' (Backend)

## API

- [api_documenti_templates](manual/api_documenti_templates.md) — Esporre via HTTP il motore documentale parametrico per operatori e responsabili: lista/dettaglio template, lista/dettaglio versioni, e mutazioni sulla testata template (create + update).

## Building block

- [api_documenti_helpers](manual/api_documenti_helpers.md) — Helper condivisi `apps/documenti/api/` (`resolve_contesto_documentale`, `extract_allegati`) riusati dalle view documentali per sorgente (offerta, preventivo, contratto, ...). Centralizzano guard contesto + estrazione multipart.
