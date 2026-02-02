# pr_run_lotto_pipeline (Django)

## Scopo
Orchestrare l’esecuzione della pipeline di fatturazione per un lotto, gestendo:
- avanzamento degli step
- aggiornamento stato lotto / job
- log di processo

## Contesto
In DB la procedura `vendite.pr_run_lotto_pipeline()` esegue la pipeline configurabile.
In Django questa logica diventa **processo applicativo**, con i vincoli di coerenza e locking che **restano in DB**.

## Input
- `lotto_id`
- parametri di esecuzione (es. `tipo_lotto`, `dry_run` se previsto)
- contesto utente/tx (se richiesto)

## Output
- esito pipeline
- stato lotto aggiornato
- log di esecuzione (warning/errori)

## Regole
- Ogni step è idempotente.
- La transizione stato lotto è sempre registrata.
- I lock e le operazioni atomiche rimangono in DB.

## Dipendenze DB
- `vendite.fn_execute_pipeline_step()` (finché non migrata completamente)
- funzioni di log e stato lotto

## Note di migrazione
- La pipeline deve rispettare gli stessi stati e step definiti in `vendite.fatturazione_pipeline`.
- Eventuali rollback devono essere espliciti e tracciati.
