# Refactor E_GENERICO — Deprecazione e sostituzione con codici errore specifici

> **Stato**: COMPLETATO
> **Inizio**: 31 marzo 2026
> **FINE**: 02 Aprile 2026

> **Approccio**: per schema, senza retrocompatibilita' (no produzione attiva)

---

## Motivazione

Il codice errore `E_GENERICO` (id 128, messaggio `%s`) e' stato usato storicamente come
fallback generico in molte funzioni PL/pgSQL. Questo rende impossibile:

1. **Identificare l'errore dal codice** — il frontend/backend riceve sempre `E_GENERICO`
   e deve parsare il messaggio testuale per capire cosa e' successo
2. **Centralizzare la gestione** — `error_policies.py` non puo' mappare azioni specifiche
   (retry, redirect, notifica) su un codice generico
3. **Monitorare** — i log aggregati per codice errore non distinguono tra errori diversi

## Regola operativa (da ora in poi)

**`E_GENERICO` e' deprecato.** Non deve piu' essere usato in nuove funzioni.

Per ogni errore, scegliere il codice piu' appropriato tra quelli esistenti in
`config.messaggi_errore`, oppure crearne uno nuovo se nessuno calza. Riferimenti:

| Pattern errore                                 | Codice da usare                                                  |
| ---------------------------------------------- | ---------------------------------------------------------------- |
| Lookup per id/codice fallito su tabella config | `E_CODICE` (id 112)                                              |
| Parametro obbligatorio mancante o non valido   | `E_PARAMETRO_INVALIDO` (id 204) o `E_ADMIN_VALIDAZIONE` (id 310) |
| Argomenti trigger mancanti                     | `ERRORE_PARAMETRI` (id 15)                                       |
| Delete non consentita da policy                | `E_DELETE_NOT_ALLOWED` (id 91)                                   |
| Regola di business specifica                   | Creare codice dedicato (es. `E_PDP_OBBLIGATORIO`)                |

## Metodo di refactor

1. Leggere la doc auto-generata della funzione (non le migrations)
2. Per ogni `E_GENERICO`, capire il contesto semantico dell'errore
3. Scegliere il codice esistente o crearne uno nuovo nel CSV `messaggi_errore.csv`
4. Creare un **nuovo changeset** con `CREATE OR REPLACE` e `runOnChange: true`
5. **MAI modificare changeset gia' pushati** — sempre nuovo file
6. Verificare ottimizzabilita' SQL (commenti, `%TYPE`, guard)

---

## Stato per schema

### Schema `anagrafiche` — ✅ Completato (20260331-01)

- [x] `fn_crea_soggetto_pg` — `E_GENERICO` → `E_CODICE` (stato non trovato)
- [x] `fn_crea_soggetto_pf` — `E_GENERICO` → `E_CODICE` (tipo soggetto PR + stato non trovati)
- [x] `fn_get_or_create_indirizzo_dettaglio` — `E_GENERICO` → `E_CODICE` (stradario non trovato)
- [x] `trgfn_clienti_sync_utility_from_ba` — 3x `E_GENERICO` → `E_CODICE` + `E_PDP_OBBLIGATORIO` + `E_PDP_UTILITY_MISMATCH`
- [x] `trgfn_emittenti_fiscali_guard_attivo` — `E_GENERICO` → `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA`
- [x] `trgfn_emittenti_fiscali_default_guard` — `E_GENERICO` → `E_EMITTENTE_DEFAULT_SINGLETON`
- [x] `trgfn_resellers_guard_attivo` — `E_GENERICO` → `E_RESELLER_DISATTIVAZIONE_BLOCCATA`

Changeset: `20260331-01-fix-fn-crea-soggetto-pf-pg-e-generico-mctit.yaml` (4 changeset)
Changeset: `20260331-02-fix-trgfn-emittenti-fiscali-e-generico-mctit.yaml` (3 changeset)

### Schema `script` — ✅ Completato (20260331-03, -04, -05)

- [x] `trgfn_guard_utility_tipo_ruolo_by_cols` — `E_GENERICO` → `E_CODICE` (soggetto_ruolo non trovato)
- [x] `fn_get_search_detail` — `E_GENERICO` → `E_CODICE` (tipo_ruolo non trovato) + branch FO aggiornato con `config.stati_fornitore`
- [x] `fn_guard_utility_tipo_ruolo` — `E_GENERICO` → `E_UTILITY_RUOLO_NON_AMMESSO`
- [x] `trgfn_delete_block_by_guc` — 2x `E_GENERICO` → `ERRORE_PARAMETRI` + `E_DELETE_NOT_ALLOWED`
- [x] `fn_get_entita_ruolo_detail` — `E_GENERICO` → `E_CODICE` (soggetto_ruolo non trovato)

Changeset: `20260331-03-fix-script-fn-e-generico-mctit.yaml` (2 changeset)
Changeset: `20260331-04-fix-fn-guard-utility-tipo-ruolo-e-generico-mctit.yaml` (1 changeset)
Changeset: `20260331-05-fix-script-fn-e-generico-2-mctit.yaml` (2 changeset)

### Schema `config` — ✅ Completato (20260331-06)

- [x] `fn_get_stati_doc_fiscale` — `E_GENERICO` → `E_PARAMETRO_INVALIDO` (target non valido)
- [x] `trgfn_tipi_ruoli_guard_entita_ref` — 3x `E_GENERICO` → `E_TIPI_RUOLI_ENTITA_INVALIDA` (tabella/colonna non valida)
- [x] `trgfn_stati_doc_fiscale_chiude_lotto_guard` — `E_GENERICO` → `E_CHIUDE_LOTTO_SINGLETON` (il codice era gia' nel JSONB context ma non usato come codice errore)
- [x] `fn_get_aliquota_iva` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_CODICE`

Changeset: `20260331-06-fix-config-fn-e-generico-mctit.yaml` (4 changeset)

### Schema `pratiche` — ✅ Completato (20260331-07)

- [x] `fn_genera_pratica_da_flusso` — 5x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (2) + `E_VALORE_MANCANTE` (1) + `E_CODICE` (2)

Changeset: `20260331-07-fix-fn-genera-pratica-da-flusso-e-generico-mctit.yaml` (1 changeset)

### Schema `vendite` — In corso (57 funzioni)

Changeset: `20260331-08-fix-vendite-fn-e-generico-batch1-mctit.yaml` (4 changeset)

- [x] `fn_applica_fondi_fattura` — 7x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + semplificato JSONB context
- [x] `fn_assign_numero_fattura` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_VALORE_MANCANTE`
- [x] `fn_build_fattura_key` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_VALORE_MANCANTE`
- [x] `fn_close_giornaliero_lotto` — 4x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (3) + `E_VALORE_MANCANTE`
Changeset: `20260331-09-fix-vendite-fn-e-generico-batch2-mctit.yaml` (4 changeset)

- [x] `fn_create_fatturazione_lotto` — 13x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (6) + `E_VALORE_MANCANTE` (1) + `E_CLIENTE_UTILITY_MISMATCH_BA` (1) + `E_EMITTENTE_DEFAULT_MISSING` (1) + `E_CODICE` (2) + `E_CONFIG_MANCANTE` (2)
- [x] `fn_emit_attivita_fatturabili_da_commessa` — 8x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (2) + `E_VALORE_MANCANTE` (3) + `E_CODICE` (1) + `E_RIGA_GIA_FATTURATA` (1)
- [x] `fn_genera_fondi_fattura_source` — 6x `E_GENERICO` → `E_PARAMETRO_INVALIDO`
- [x] `fn_generate_fatture_righe` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO`
Changeset: `20260331-10-fix-vendite-fn-e-generico-batch3-mctit.yaml` (4 changeset)

- [x] `fn_get_arrotondamento_scope` — 5x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_get_commessa_stato` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_VALORE_MANCANTE` + `%TYPE`
- [x] `fn_get_lotto_segnalazioni_summary` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_get_lotto_task_last_run` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
Changeset: `20260331-11-fix-vendite-fn-e-generico-batch4-mctit.yaml` (3 changeset)

- [x] `fn_get_next_progressivo` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_get_or_create_commessa` — 6x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (3) + `E_VALORE_MANCANTE` (1) + `E_BILLING_ACCOUNT_UTILITY_NULL` (1) + `E_CLIENTE_UTILITY_MISMATCH_BA` (1) + `E_DATA_AL_MINORE_DAL` (1)
- [x] `fn_get_or_create_fattura_header` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_VALORE_MANCANTE` + `E_CONFIG_MANCANTE`

Changeset: `20260331-12-fix-fn-get-or-create-lotto-e-generico-mctit.yaml` (1 changeset, file dedicato)

- [x] `fn_get_or_create_lotto` — 17x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (3) + `E_VALORE_MANCANTE` (1) + `E_LOTTO_PARAMETRO_NON_COERENTE` (12) + `E_LOTTO_NON_RIUTILIZZABILE` (2)
Changeset: `20260331-13-fix-vendite-fn-e-generico-batch5-mctit.yaml` (4 changeset)

- [x] `fn_get_pipeline_task_policy` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (2) + `E_CONFIG_MANCANTE` (1) + `%TYPE`
- [x] `fn_get_registro_id` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_CONFIG_MANCANTE` + `%TYPE`
- [x] `fn_get_tipo_doc_fiscale_id` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_CODICE` + `%TYPE`
- [x] `fn_get_totale_fondi_fattura` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
Changeset: `20260331-14-fix-vendite-fn-e-generico-batch6-mctit.yaml` (3 changeset)

- [x] `fn_get_valuta_id` — 1x `E_GENERICO` → `E_CONFIG_MANCANTE` + `%TYPE`
- [x] `fn_group_attivita_fatturabili` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_VALORE_MANCANTE` + `%TYPE`
- [x] `fn_list_attivita_sorgenti_abilitate` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`

Changeset: `20260331-15-fix-fn-link-commessa-sorgente-e-generico-mctit.yaml` (1 changeset, file dedicato)

- [x] `fn_link_commessa_sorgente` — 7x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (4) + `E_VALORE_MANCANTE` (1) + `E_COMMESSA_ROOT_CONFLITTO` (2)
Changeset: `20260331-16-fix-vendite-fn-e-generico-batch7-mctit.yaml` (4 changeset)

- [x] `fn_list_commessa_attivita` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_VALORE_MANCANTE` + `%TYPE`
- [x] `fn_list_consumi_da_pushare` — 1x `E_GENERICO` → `E_CODICE` (sorgente ATTIVITA_CONSUMI) + `%TYPE`
- [x] `fn_list_contratti_da_pushare` — 1x `E_GENERICO` → `E_CODICE` (sorgente CONTRATTO) + `%TYPE`
- [x] `fn_list_ddt_da_pushare` — 1x `E_GENERICO` → `E_CODICE` (sorgente DDT_VENDITA) + `%TYPE`
Changeset: `20260331-17-fix-vendite-fn-e-generico-batch8-mctit.yaml` (4 changeset)

- [x] `fn_list_fatturazione_pipeline_steps` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_list_lotto_task_runs` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_list_ordini_da_pushare` — 1x `E_GENERICO` → `E_CODICE` (ORDINE_VENDITA) + `%TYPE`
- [x] `fn_list_preventivi_da_pushare` — 1x `E_GENERICO` → `E_CODICE` (PREVENTIVO) + `%TYPE`
Changeset: `20260331-18-fix-vendite-fn-e-generico-batch9-mctit.yaml` (4 changeset)

- [x] `fn_log_commessa_push_run` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_log_lotto_esito_fatture` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_log_pipeline_fase` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (2) + `E_VALORE_MANCANTE` (1) + `%TYPE`
- [x] `fn_numera_fattura_opz_emessa` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + aggiunto `E_FATTURA_NON_TROVATA` (140) al CSV
Changeset: `20260331-19-fix-vendite-fn-e-generico-batch10-mctit.yaml` (4 changeset)

- [x] `fn_prepare_sdi_payload` — 4x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (2) + `E_VALORE_MANCANTE` (1) + `E_CODICE` (1) + `%TYPE`
- [x] `fn_reset_fondi_fattura` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_CONFIG_MANCANTE` + `%TYPE`
- [x] `fn_reset_lotto_draft` — 7x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (4) + `E_VALORE_MANCANTE` (1) + `E_CONFIG_MANCANTE` (2) + `%TYPE`
- [x] `fn_reset_lotto_fattura_draft` — 7x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (5) + `E_VALORE_MANCANTE` (1) + `E_CONFIG_MANCANTE` (1) + `%TYPE`
Changeset: `20260331-20-fix-vendite-fn-e-generico-batch11-mctit.yaml` (3 changeset)

- [x] `fn_resolve_commessa_prezzi` — **SKIP**: dipende da `vendite.attivita_fatturabili_lotti` che non esiste piu'. Changeset con `preCondition tableExists → MARK_RAN`. **Da verificare se la funzione va rimossa dal DB.**
- [x] `fn_resolve_fatturazione_pipeline_step` — 4x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_resolve_lotto_task_execution_mode` — 4x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (3) + `E_CONFIG_MANCANTE` (1) + `%TYPE`

Changeset: `20260331-22-fix-fn-resolve-lotto-utility-emittente-e-generico-mctit.yaml` (1 changeset, file dedicato)

- [x] `fn_resolve_lotto_utility_emittente` — 7x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (3) + `E_VALORE_MANCANTE` (1) + `E_CLIENTE_UTILITY_MISMATCH_BA` (1) + `E_LOTTO_PARAMETRO_NON_COERENTE` (1) + `E_CODICE` (1)
Changeset: `20260331-23-fix-vendite-fn-e-generico-batch12-mctit.yaml` (3 changeset)

- [x] `fn_resolve_termini_pagamento` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_ricalcola_fattura` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`
- [x] `fn_ricalcola_riepiloghi_iva_lotto` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`

Changeset: `20260331-24-fix-fn-resolve-prezzo-listino-e-generico-mctit.yaml` (1 changeset, file dedicato)

- [x] `fn_resolve_prezzo_listino` — 8x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (6) + `E_PREZZO_LISTINO_NON_TROVATO` (1) + `E_PREZZO_LISTINO_AMBIGUO` (1)
Changeset: `20260331-27-fix-vendite-fn-e-generico-batch13-mctit.yaml` (4 changeset)

- [x] `fn_ricalcola_riepilogo_iva_fattura` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_FATTURA_NON_TROVATA` + `E_PARAMETRO_INVALIDO` (stato)
- [x] `fn_ricalcola_totali_fattura` — 2x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_CONFIG_MANCANTE`
- [x] `fn_select_attivita_fatturabili` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO`
Changeset: `20260331-31-fix-fn-set-arrotondamento-scope-e-generico-mctit.yaml` (1 changeset)

- [x] `fn_set_arrotondamento_scope` — 6x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `%TYPE`

**Da fare (prossima sessione — funzioni grandi):**

- [ ] `fn_set_documento_canale_stato` — 16x E_GENERICO
- [ ] `fn_set_fatturazione_lotto_stato` — 12x E_GENERICO
- [x] `fn_set_runtime_task_run_esito` — **SKIP** (`20260331-25`): dipende da `vendite.attivita_fatturabili_lotti` (rimossa). `preCondition tableExists → MARK_RAN`
- [x] `fn_sync_fattura_critical` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO`

Changeset: `20260331-28-fix-vendite-fn-e-generico-batch14-mctit.yaml` (4 changeset)

- [x] `fn_start_lotto_task_run` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO`
- [x] `fn_sync_attivita_stato_esecuzione` — **SKIP** (`20260331-26`): dipende da `vendite.attivita_fatturabili_lotti` (rimossa). `preCondition tableExists → MARK_RAN`
- [x] `fn_sync_contabili_fondo_fattura` — 3x `E_GENERICO` → `E_PARAMETRO_INVALIDO` + `E_CONFIG_MANCANTE` (2)
- [x] `fn_sync_lotto_fatture_stato` — 4x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (2) + `E_LOTTO_NON_TROVATO` (1) + `E_PARAMETRO_INVALIDO` (1)
- [x] `fn_sync_pagamento_fondo_fattura` — 1x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (wrapper deprecato)
- [ ] `fn_upsert_commessa_attivita` — 22x E_GENERICO (da fare prossima sessione)

Changeset: `20260331-29-fix-vendite-trgfn-guard-e-generico-mctit.yaml` (3 changeset)

- [x] `trgfn_fatturazione_lotti_guard_stato` — 2x `E_GENERICO` → `E_LOTTO_PARAMETRO_NON_COERENTE`
- [x] `trgfn_fatture_guard_stato` — 3x `E_GENERICO` → `E_LOTTO_PARAMETRO_NON_COERENTE`
- [x] `trgfn_logs_guard_delete` — 1x `E_GENERICO` → `E_DELETE_NOT_ALLOWED`

Changeset: `20260331-30-fix-trgfn-attivita-fatturabili-guard-commessa-e-generico-mctit.yaml` (1 changeset)

- [x] `trgfn_attivita_fatturabili_guard_commessa` — 4x `E_GENERICO` → `E_PARAMETRO_INVALIDO` (1) + `E_COMMESSA_ATTIVITA_NON_COERENTE` (3)

---

## Messaggi errore creati durante il refactor

| Codice                                | ID  | Schema      | Creato per                            |
| ------------------------------------- | --- | ----------- | ------------------------------------- |
| `E_ADMIN_PIVA_DUPLICATA`              | 313 | anagrafiche | fn_crea_soggetto_pg (PIVA duplicata)  |
| `E_PDP_OBBLIGATORIO`                  | 330 | anagrafiche | trgfn_clienti_sync_utility_from_ba    |
| `E_PDP_UTILITY_MISMATCH`              | 331 | anagrafiche | trgfn_clienti_sync_utility_from_ba    |
| `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA` | 131 | anagrafiche | trgfn_emittenti_fiscali_guard_attivo  |
| `E_EMITTENTE_DEFAULT_SINGLETON`       | 132 | anagrafiche | trgfn_emittenti_fiscali_default_guard |
| `E_RESELLER_DISATTIVAZIONE_BLOCCATA`  | 133 | anagrafiche | trgfn_resellers_guard_attivo          |
| `E_UTILITY_RUOLO_NON_AMMESSO`         | 134 | script      | fn_guard_utility_tipo_ruolo           |

Codici esistenti riutilizzati: `E_CODICE` (112), `ERRORE_PARAMETRI` (15), `E_DELETE_NOT_ALLOWED` (91), `E_PARAMETRO_INVALIDO` (204), `E_ADMIN_VALIDAZIONE` (310).

---

*Documento di tracciamento refactor E_GENERICO — ZeroERP (31 marzo 2026)*
