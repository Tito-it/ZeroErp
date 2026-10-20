# fn_ritira_attivo_orfani

### Scopo

Toglie i trigger ATTIVO che nominano una tabella o una colonna che non esiste
più: i motivi `TABELLA_ASSENTE` e `COLONNA_ASSENTE` del lettore
[`dbops.fn_trigger_attivo_orfani`](/dbzero/dbops/manual/fn_trigger_attivo_orfani).
Torna quanti ne ha tolti.

`ARGOMENTI_INSUFFICIENTI` resta dov'è: è un errore di scrittura, lo segnala il
presidio.

## Chi la chiama

`dbops.fn_run_automations_attivo`, in testa a ogni giro e fuori dal dry run,
accanto a [`dbops.fn_ritira_attivo_eccezioni`](/dbzero/dbops/manual/fn_ritira_attivo_eccezioni):
chi genera i trigger ritira anche quelli rimasti senza la figlia. Chi elimina
una tabella non deve ricordarsi dei guard sui padri.

- In CI non trova niente: `ci_apply` gira dopo i `DROP`, e il generatore non
  crea mai un orfano.
- Su un database di sviluppo ripulisce al primo job `automations_attivo`, oppure
  subito con la `CALL` del job a mano.

È un `DROP TRIGGER IF EXISTS`: idempotente. `INVOKER`: la chiamano il migratore
o il job, che possiedono le tabelle.
