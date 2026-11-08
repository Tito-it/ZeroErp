---
search:
  exclude: true
---

# Schema `documenti`

## 📚 Tabelle (manuale)
- [documenti_generati](manual/documenti_generati.md) — `documenti.documenti_generati` è il **registro storico delle generazioni persistite** del motore documentale. Ogni riga rappresenta un documento prodotto, con snapshot del contesto, hash di audit e collegamento alla versione template usata.
- [documenti_generati_eventi](manual/documenti_generati_eventi.md) — (introdotta 03-05-2026, anticipo Fase B → v1)
- [documenti_generati_file](manual/documenti_generati_file.md) — (latest review 29-04-2026) `documenti.documenti_generati_file` conserva i **file persistiti** collegati a un documento già generato, separando il record storico logico dalla memorizzazione fisica del file.
- [render_engine_documento](manual/render_engine_documento.md) — (latest review 29-04-2026) `documenti.render_engine_documento` definisce il catalogo dei motori di rendering ammessi per la trasformazione del template in documento finale.
- [template_asset](manual/template_asset.md) — (latest review 29-04-2026) `documenti.template_asset` è il catalogo degli **asset documentali riusabili** associati a un emittente fiscale: logo, firme, immagini, CSS o altri file di supporto usati nella resa dei template.
- [template_documenti](manual/template_documenti.md) — (latest review 29-04-2026) `documenti.template_documenti` rappresenta il **contenitore logico** di un template documentale. Non contiene ancora il contenuto renderizzabile del template: definisce l'identità funzionale del template per tipo output, sorgente applicativa ed emittente fiscale.
- [template_documenti_versioni](manual/template_documenti_versioni.md) — (latest review 30-09-2026) `documenti.template_documenti_versioni` contiene le **versioni renderizzabili** del template documentale, con stato di pubblicazione e finestra temporale di validità.
- [tipi_asset_documento](manual/tipi_asset_documento.md) — (latest review 29-04-2026) `documenti.tipi_asset_documento` definisce la tipologia funzionale degli asset riusabili nei template documentali: logo, firma, immagine, PDF di supporto, CSS e altre risorse statiche.
- [tipi_documento_output](manual/tipi_documento_output.md) — (latest review 29-04-2026) `documenti.tipi_documento_output` definisce il catalogo dei **tipi di output** producibili dal motore documentale. Serve a separare il "che cosa genero" dalla sorgente applicativa e dal template usato per la resa PDF.
- [tipi_file_documento](manual/tipi_file_documento.md) — (latest review 29-04-2026) `documenti.tipi_file_documento` definisce il catalogo dei **tipi di file persistiti** a valle della generazione di un documento.

## ⚙️ Funzioni (manuale)
- [fn_crea_bozza_da_versione](manual/fn_crea_bozza_da_versione.md)
- [fn_guard_versione_contesto](manual/fn_guard_versione_contesto.md)
- [fn_personalizza_template_standard](manual/fn_personalizza_template_standard.md)
- [fn_pubblica_template_documento_versione](manual/fn_pubblica_template_documento_versione.md) — (latest review 30-09-2026 — il patto versione/forma dei dati: brief-db-documenti-versione-contesto-template)
- [fn_risolvi_template_applicabile](manual/fn_risolvi_template_applicabile.md)
- [fn_template_esito_risoluzione](manual/fn_template_esito_risoluzione.md)
- [fn_template_motivo_non_coerente](manual/fn_template_motivo_non_coerente.md)
- [trgfn_documenti_generati_block_delete](manual/trgfn_documenti_generati_block_delete.md)
- [trgfn_documenti_generati_check_coerenza](manual/trgfn_documenti_generati_check_coerenza.md)
- [trgfn_documenti_generati_eventi_block_delete](manual/trgfn_documenti_generati_eventi_block_delete.md)
- [trgfn_documenti_generati_eventi_block_update](manual/trgfn_documenti_generati_eventi_block_update.md)
- [trgfn_documenti_generati_file_protect_file](manual/trgfn_documenti_generati_file_protect_file.md)
- [trgfn_documenti_generati_guard_versione_contesto](manual/trgfn_documenti_generati_guard_versione_contesto.md)
- [trgfn_documenti_generati_protect_snapshot](manual/trgfn_documenti_generati_protect_snapshot.md) — Trigger function `BEFORE UPDATE` su `documenti.documenti_generati` che blocca la modifica di **tutti i campi snapshot** del record di generazione.
- [trgfn_template_asset_block_delete](manual/trgfn_template_asset_block_delete.md)
- [trgfn_template_asset_protect_file](manual/trgfn_template_asset_protect_file.md)
- [trgfn_template_documenti_versioni_block_delete](manual/trgfn_template_documenti_versioni_block_delete.md)
- [trgfn_template_documenti_versioni_protect_pubblicata](manual/trgfn_template_documenti_versioni_protect_pubblicata.md)

## 🔍 Views (manuale)
- [vw_template_personalizzati_scarto](manual/vw_template_personalizzati_scarto.md)
- [vw_template_risoluzione_emittente](manual/vw_template_risoluzione_emittente.md)
- [vw_template_versioni_stampabili](manual/vw_template_versioni_stampabili.md)
