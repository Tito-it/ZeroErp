# Brief DB — Allegati su documento generato: tipo file `ALLEGATO` + parametro size

> **Branch**: `dev/db-tid`. **Tipo**: seed-only (nessun DDL, nessun trigger,
> nessuna funzione). **Tempo stimato**: 5 minuti.
> **Contesto**: building block "genera documento + allegati" all'emissione
> (offerta commerciale prima, poi preventivi/contratti). Lo schema
> `documenti_generati_file` ammette già file secondari (`is_principale`
> default `false`; UNIQUE su `(documento_generato_id, file_tipo_id,
> ordinamento)`; il trigger `trgfn_documenti_generati_file_protect_file`
> blocca solo gli UPDATE, **non** gli INSERT). Quindi NON serve modificare
> tabelle o trigger. Manca solo:
> 1. un tipo file `ALLEGATO` attivo (oggi esiste solo `PDF_FINALE`; il
>    trigger `trgfn_child_requires_active_parent` su `file_tipo_id` richiede
>    un tipo file **attivo** all'INSERT);
> 2. un parametro per il limite di dimensione del singolo allegato.

---

## Perché serve

Il BE genererà il PDF principale come `documenti_generati_file` con
`file_tipo = PDF_FINALE`, `is_principale = true`. Gli allegati caricati
dall'utente (PDF + immagini jpg/png) verranno persistiti come file
**secondari** dello stesso `documento_generato`: `is_principale = false`,
`ordinamento >= 2`, `file_tipo = ALLEGATO`. Senza il tipo file `ALLEGATO`
attivo, l'INSERT del file secondario fallisce sul guard
`trgfn_child_requires_active_parent('documenti','tipi_file_documento',...)`.

## Fix richiesto (2 righe CSV)

Entrambi i changeset di seed sono `runOnChange: true` con
`validCheckSums: ANY`: basta **aggiungere le righe ai CSV esistenti**,
nessuna nuova migration.

### 1. `db/changelog/migrations_v2/80_data/sql/documenti/tipi_file_documento.csv`

Header attuale:
`id,codice,codice_interno,descrizione,attivo,meta,storicizza,data_insert,user_insert,data_update,user_update,tx_id`

Riga da aggiungere:

```csv
2,ALLEGATO,ALLEGATO,Allegato documento,true,{},"true",2026-05-27 00:00:00,titodb,2026-05-27 00:00:00,titodb,NULL
```

Caricato dal changeset `20260429-58-upsert-documenti-seed-base`
(loadUpdateData su `documenti.tipi_file_documento`, primaryKey `id`).

### 2. `db/changelog/migrations_v2/80_data/sql/config/parameters_documenti_storage.csv`

Header attuale:
`id,code,default_value,description,data_insert,user_insert,data_update,user_update,tx_id,storicizza`

Riga da aggiungere:

```csv
38,documenti_allegato_upload_max_mb,25,Limite massimo in MB per singolo allegato caricato su un documento generato.,2026-05-27 00:00:00,titodb,2026-05-27 00:00:00,titodb,NULL,t
```

Caricato dal changeset `20260429-59-upsert-parameters-documenti-storage`
(loadUpdateData su `config.parameters`, primaryKey `id`). Nota: l'ultimo id
usato nel CSV è `37` (`documenti_pdf_generato_max_mb`), quindi `38` è libero.

## Lato BE (in sviluppo su dev/backend-tid, nessun blocco reciproco)

- `DocumentGenerationService` esteso per persistere allegati come file
  secondari (`ALLEGATO`, `is_principale=false`, `ordinamento` progressivo)
  nella stessa transazione del documento principale.
- Validazione MIME (whitelist `application/pdf`, `image/jpeg`, `image/png`)
  e size (`documenti_allegato_upload_max_mb`), mirror del pattern già usato
  in `template_asset_admin_service.upload_asset`.
- Lookup tipo file per codice `ALLEGATO` (no ID hardcoded), come già fatto
  per `PDF_FINALE`.

Il BE può essere scritto e testato (mock) prima del merge: il test
end-to-end di persistenza allegati richiede solo che questo seed sia
applicato.

---

*Brief DB seed-only — tipo file ALLEGATO + parametro size allegato.
Speculare al pattern asset (`documenti_asset_upload_max_mb`). Pronto per
`dev/db-tid`.*
