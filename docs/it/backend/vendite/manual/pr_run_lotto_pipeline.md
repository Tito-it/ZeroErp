# pr_run_lotto_pipeline (Django)

## Scopo

Orchestrare l'esecuzione della pipeline di fatturazione per un lotto, gestendo:

- avanzamento step configurati
- aggiornamento stato lotto/job
- logging di fase e gestione errori applicativi

## Contesto

La procedura SQL `vendite.pr_run_lotto_pipeline()` è stata migrata lato backend Django.
L'orchestrazione ora vive in:

- `apps/vendite/services/pipeline_service.py` (`pr_run_lotto_pipeline`)
- `apps/vendite/services/pipeline_runner.py` (`LottoPipelineRunner.run_pipeline`)
- `apps/vendite/services/pipeline_error_logger.py` (`PipelineErrorLogger`, routing errori `LOTTO`/`FATTURA`)

I vincoli di coerenza dati e le operazioni DB specialistiche restano delegate al database.

## Input

- `lotto_id` (opzionale; `0`/`None` => crea/risolve lotto)
- `competenza_mese`
- `tipo_doc_fiscale_id`
- `utility_id`
- `billing_account_id`
- `emittente_soggetto_ruolo_id`
- `lock_batch_id`
- `meta`
- `dry_run`
- `tipo_lotto` (default `MASSIVO`)

## Output

- `lotto_id` elaborato
- stato job lotto aggiornato (`IN_ESECUZIONE` -> `COMPLETATO`/`ERRORE`)
- log fasi pipeline su `vendite.fatturazione_lotti_log`

## Regole

- Se il lotto non esiste viene creato/risolto via DB (`vendite.fn_get_or_create_lotto`).
- Il tipo lotto effettivo usa DB come fonte autoritativa; input come fallback.
- Se `stato_lotto = IN_ESECUZIONE` il rilancio pipeline è bloccato.
- Se il lotto è chiuso (`COMPLETATO`/`ERRORE`), le transizioni di stato documento sono governate da `config.stati_doc_fiscale_transizioni` (enforcement DB).
- Per lotto `GIORNALIERO`, allo stato `INVIATA` viene eseguita chiusura operativa lotto.
- Errori applicativi (`ServiceError`) preservano codice dominio e marcano lotto in errore.
- Errori inattesi vengono wrappati in `E_PIPELINE` con causa agganciata.

### Risoluzione emittente fiscale

L'emittente viene risolto **una sola volta** alla creazione/risoluzione del lotto, con questa priorità (implementata in `vendite.fn_get_or_create_lotto` tramite helper `vendite.fn_resolve_lotto_utility_emittente`):

1. `emittente_soggetto_ruolo_id` esplicito in input → validato e persistito.
2. Dedotto dal mapping `billing_account_id` → emittente fiscale (tabella `anagrafiche.emittenti_fiscali_billing_account`).
3. Unico emittente fiscale attivo nel sistema → usato come default.
4. Se non determinabile → errore bloccante.

Il valore viene persistito su `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` e letto da `LottoContext` a ogni step pipeline. I task (es. `select_attivita`) usano **esclusivamente** il valore del lotto — i params JSON della config pipeline non sovrascrivono l'emittente.

## Logging e routing errori

- Log tecnico centralizzato: `dbops.error_log` (via `ErrorManager` lato backend e `fn_log_and_raise_error` lato SQL).
- Log dominio lotto: `vendite.fatturazione_lotti_log` (fasi step + esito severità dedotto).
- Log dominio fattura: `vendite.fatture_log` solo per errori attribuibili alla singola fattura.
- Contratto errori: `scope` (`LOTTO`/`FATTURA`), `severity` (`I/W/C`), `code`, `lotto_id`, `fattura_id` (se `FATTURA`), `context/meta`.

## Dipendenze DB

- `vendite.fn_get_or_create_lotto(...)` — creazione/risoluzione lotto + risoluzione emittente
- `vendite.fn_resolve_lotto_utility_emittente(...)` — helper condiviso per coerenza `billing_account`/`utility`/`emittente`
- `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` — attributo lotto persistito
- `anagrafiche.emittenti_fiscali_billing_account` — mapping BA → emittente (usato in DB)
- `vendite.fn_log_pipeline_fase(...)`
- `vendite.fn_sync_lotto_fatture_stato(...)` — sync `stato_esecuzione` e `stato_doc_fiscale_id` sul ponte lotto-fatture

## Matrice responsabilità (Python vs DB)

- **Python** (service/runner): orchestrazione flusso pipeline, sequencing step, gestione errori applicativi, policy `dry_run`.
- **DB** (funzioni/tabelle): creazione/risoluzione lotto, risoluzione emittente, persistenza stati e log, operazioni set-based sulle fatture, vincoli di integrità.

## Note di migrazione

- Orchestrazione e step executor migrati in Python.
- Il mapping task è esplicito nel servizio (`PipelineStepExecutor`) con whitelist funzioni ammesse.
- La configurazione step resta su `vendite.fatturazione_pipeline` (source of truth).
- La selezione step usa fallback di specificità: match su `utility_id`/`tipo_doc_fiscale_id`, poi fallback su valori `NULL` (configurazione base).
- L'emittente fiscale era in precedenza dedotto a runtime; ora è attributo esplicito del lotto, persistito in DB alla creazione e propagato via `LottoContext`.
