---
search:
  exclude: true
---

# Schema `documenti`

## 📚 Tabelle
- [documenti_generati](tabelle/documenti_generati.md) — `documenti.documenti_generati` è il **registro storico delle generazioni persistite** del motore documentale. Ogni riga rappresenta un documento prodotto, con snapshot del contesto, hash di audit e collegamento alla versione template usata.
- [documenti_generati_eventi](tabelle/documenti_generati_eventi.md) — (introdotta 03-05-2026, anticipo Fase B → v1)
- [documenti_generati_file](tabelle/documenti_generati_file.md) — (latest review 29-04-2026) `documenti.documenti_generati_file` conserva i **file persistiti** collegati a un documento già generato, separando il record storico logico dalla memorizzazione fisica del file.
- [formati_pagina](tabelle/formati_pagina.md)
- [formati_template](tabelle/formati_template.md)
- [orientamenti_pagina](tabelle/orientamenti_pagina.md)
- [render_engine_documento](tabelle/render_engine_documento.md) — (latest review 29-04-2026) `documenti.render_engine_documento` definisce il catalogo dei motori di rendering ammessi per la trasformazione del template in documento finale.
- [template_asset](tabelle/template_asset.md) — (latest review 29-04-2026) `documenti.template_asset` è il catalogo degli **asset documentali riusabili** associati a un emittente fiscale: logo, firme, immagini, CSS o altri file di supporto usati nella resa dei template.
- [template_documenti](tabelle/template_documenti.md) — (latest review 29-04-2026) `documenti.template_documenti` rappresenta il **contenitore logico** di un template documentale. Non contiene ancora il contenuto renderizzabile del template: definisce l'identità funzionale del template per tipo output, sorgente applicativa ed emittente fiscale.
- [template_documenti_versioni](tabelle/template_documenti_versioni.md) — (latest review 14-11-2026) `documenti.template_documenti_versioni` contiene le **versioni renderizzabili** del template documentale, con stato di pubblicazione e finestra temporale di validità.
- [tipi_asset_documento](tabelle/tipi_asset_documento.md) — (latest review 29-04-2026) `documenti.tipi_asset_documento` definisce la tipologia funzionale degli asset riusabili nei template documentali: logo, firma, immagine, PDF di supporto, CSS e altre risorse statiche.
- [tipi_documento_output](tabelle/tipi_documento_output.md) — (latest review 29-04-2026) `documenti.tipi_documento_output` definisce il catalogo dei **tipi di output** producibili dal motore documentale. Serve a separare il "che cosa genero" dalla sorgente applicativa e dal template usato per la resa PDF.
- [tipi_file_documento](tabelle/tipi_file_documento.md) — (latest review 29-04-2026) `documenti.tipi_file_documento` definisce il catalogo dei **tipi di file persistiti** a valle della generazione di un documento.

## ⚙️ Funzioni
- [fn_crea_bozza_da_versione](funzioni/fn_crea_bozza_da_versione.md)
- [fn_guard_versione_contesto](funzioni/fn_guard_versione_contesto.md)
- [fn_personalizza_template_standard](funzioni/fn_personalizza_template_standard.md)
- [fn_pubblica_template_documento_versione](funzioni/fn_pubblica_template_documento_versione.md) — (latest review 14-11-2026 — che cosa stampa dopo la pubblicazione: lo decide la validità)
- [fn_risolvi_template_applicabile](funzioni/fn_risolvi_template_applicabile.md)
- [fn_template_esito_risoluzione](funzioni/fn_template_esito_risoluzione.md)
- [fn_template_motivo_non_coerente](funzioni/fn_template_motivo_non_coerente.md)
- [trgfn_documenti_generati_block_delete](funzioni/trgfn_documenti_generati_block_delete.md)
- [trgfn_documenti_generati_check_coerenza](funzioni/trgfn_documenti_generati_check_coerenza.md)
- [trgfn_documenti_generati_eventi_block_delete](funzioni/trgfn_documenti_generati_eventi_block_delete.md)
- [trgfn_documenti_generati_eventi_block_update](funzioni/trgfn_documenti_generati_eventi_block_update.md)
- [trgfn_documenti_generati_file_protect_file](funzioni/trgfn_documenti_generati_file_protect_file.md)
- [trgfn_documenti_generati_guard_versione_contesto](funzioni/trgfn_documenti_generati_guard_versione_contesto.md)
- [trgfn_documenti_generati_protect_snapshot](funzioni/trgfn_documenti_generati_protect_snapshot.md) — Trigger function `BEFORE UPDATE` su `documenti.documenti_generati` che blocca la modifica di **tutti i campi snapshot** del record di generazione.
- [trgfn_template_asset_block_delete](funzioni/trgfn_template_asset_block_delete.md)
- [trgfn_template_asset_protect_file](funzioni/trgfn_template_asset_protect_file.md)
- [trgfn_template_documenti_versioni_block_delete](funzioni/trgfn_template_documenti_versioni_block_delete.md)
- [trgfn_template_documenti_versioni_guard_derivata_da](funzioni/trgfn_template_documenti_versioni_guard_derivata_da.md)
- [trgfn_template_documenti_versioni_protect_pubblicata](funzioni/trgfn_template_documenti_versioni_protect_pubblicata.md)
- [trgfn_template_standard_guard_sola_lettura](funzioni/trgfn_template_standard_guard_sola_lettura.md)

## 🔍 Views
- [vw_template_personalizzati_scarto](views/vw_template_personalizzati_scarto.md)
- [vw_template_risoluzione_emittente](views/vw_template_risoluzione_emittente.md)
- [vw_template_versioni_stampabili](views/vw_template_versioni_stampabili.md)
