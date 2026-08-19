# Area 'documenti' (Backend)

## API
- [api_documenti_helpers](manual/api_documenti_helpers.md) — Helper condivisi apps/documenti/api/ riusabili dalle view documentali "per sorgente" (offerta, preventivo, contratto, ...) per:
- [api_documenti_per_sorgente](manual/api_documenti_per_sorgente.md) — Dire **quale URL chiamare** per stampare, scaricare e ristampare il documento di una sorgente — preventivo, offerta, contratto, ordine, DDT, fattura — e cosa cambia da un dominio all'altro.
- [api_documenti_templates](manual/api_documenti_templates.md) — Esporre via HTTP il motore documentale parametrico per operatori e responsabili: lista/dettaglio template, lista/dettaglio versioni, e mutazioni sulla testata template (create + update).
- [api_ristampa_fedele](manual/api_ristampa_fedele.md) — Riprodurre un documento **com'era**: con la versione di template con cui nacque e il contesto congelato di allora. È il terzo dei tre percorsi documentali, e l'unico che mantiene la promessa di riproducibilità sui docum…
