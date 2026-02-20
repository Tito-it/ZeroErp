# pr_run_lotto_pipeline (Django)

## Scopo
Orchestrare l'esecuzione della pipeline di fatturazione per un lotto, gestendo:
- avanzamento step configurati
- aggiornamento stato lotto/job
- logging di fase e gestione errori applicativi

## Contesto
La procedura SQL `vendite.pr_run_lotto_pipeline()` e` stata migrata lato backend Django.
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
- Se il lotto non esiste viene creato/risolto via DB.
- Il tipo lotto effettivo usa DB come fonte autoritativa; input come fallback.
- Se `stato_lotto = IN_ESECUZIONE` il rilancio pipeline e` bloccato.
- Se il lotto e` chiuso (`COMPLETATO`/`ERRORE`), le transizioni di stato documento sono governate da `config.stati_doc_fiscale_transizioni` (enforcement DB).
- Per lotto `GIORNALIERO`, allo stato `INVIATA` viene eseguita chiusura operativa lotto.
- Errori applicativi (`ServiceError`) preservano codice dominio e marcano lotto in errore.
- Errori inattesi vengono wrappati in `E_PIPELINE` con causa agganciata (`raise ... from ...`).

## Logging e routing errori
- Log tecnico centralizzato: `dbops.error_log` (via `ErrorManager` lato backend e `fn_log_and_raise_error` lato SQL).
- Log dominio lotto: `vendite.fatturazione_lotti_log` (fasi step + esito severita` dedotto).
- Log dominio fattura: `vendite.fatture_log` solo per errori attribuibili alla singola fattura (non massivamente a tutto il lotto).
- Contratto consigliato per errori applicativi: `scope` (`LOTTO`/`FATTURA`), `severity` (`I/W/C`), `code`, `lotto_id`, `fattura_id` (se `FATTURA`), `context/meta`.

## Dipendenze DB
- `vendite.fn_get_or_create_lotto(...)`
- `vendite.fn_set_fatturazione_lotto_stato(...)`
- `vendite.fn_log_pipeline_fase(...)`
- `vendite.fn_select_attivita_fatturabili(...)`
- `vendite.fn_close_giornaliero_lotto(...)`

## Matrice responsabilita` (Python vs DB)
- Python (service/runner): orchestrazione flusso pipeline, sequencing step, gestione errori applicativi, policy `dry_run`.
- DB (funzioni/tabelle): creazione/risoluzione lotto, persistenza stati e log, operazioni set-based sulle fatture, vincoli di integrita`.

## Note di migrazione
- Stato attuale: orchestrazione e step executor migrati in Python.
- Il mapping task e` esplicito nel servizio (`PipelineStepExecutor`) con whitelist funzioni ammesse.
- La configurazione step resta su `vendite.fatturazione_pipeline` (source of truth).
- La selezione step usa fallback di specificita`: match su `utility_id`/`tipo_doc_fiscale_id`,
  poi fallback su valori `NULL` (configurazione base).
