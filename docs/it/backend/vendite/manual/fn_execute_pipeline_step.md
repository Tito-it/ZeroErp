# fn_execute_pipeline_step (Django)

## Scopo
Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.

## Contesto
In DB la funzione `vendite.fn_execute_pipeline_step()` esegue i task definiti in `processi`/`rollback`.
In Django questa logica viene portata nei **services**.

## Input
- `lotto_id`
- `step_code` o riferimento allo step
- configurazione step (task JSON)

## Output
- esito step
- log task (successo/errore)

## Regole
- Ogni task deve essere tracciato.
- In caso di errore, interrompere lo step e registrare il log.

## Dipendenze DB
- Lettura pipeline da `vendite.fatturazione_pipeline`
- Funzioni/trigger di integrità in DB (immutate)

## Note di migrazione
- Convertire i task JSON in chiamate a service Django con mapping esplicito.
- Evitare logica dinamica non controllata: mantenere mapping chiaro tra `task_code` e handler.
