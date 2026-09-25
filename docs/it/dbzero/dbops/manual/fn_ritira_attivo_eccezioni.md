# fn_ritira_attivo_eccezioni

### Scopo

Toglie i trigger ATTIVO **già generati** per le FK dichiarate in
[`dbops.automazione_attivo_eccezioni`](/dbzero/dbops/manual/automazione_attivo_eccezioni).
Torna quanti ne ha tolti.

## Come li riconosce

⛔ **Per funzione e argomenti, non per nome**: i nomi generati oltre i 63
caratteri sono hashati. `tgargs` si legge con `encode(…, 'escape')`.

| Trigger | Funzione | Dove sta la FK negli argomenti |
| --- | --- | --- |
| require, sul **figlio** | `dbops.trgfn_child_requires_active_parent` | il figlio è la tabella del trigger, la colonna FK è l'argomento 4 |
| block, sul **padre** | `dbops.trgfn_prevent_deactivate_if_children` | argomenti 1, 2, 3 = schema, tabella e colonna FK della figlia |

## Chi la chiama

- `dbops.fn_run_automations_attivo`, in testa a ogni giro (fuori dal dry run):
  chi genera i trigger li ritira quando la coppia diventa un'eccezione;
- `90_end/20260925-50`, una volta: su dbdev i trigger c'erano già e il job
  delle automazioni gira solo la sera.

È un `DROP TRIGGER IF EXISTS`: idempotente, e su un database nuovo (prima del
`ci_apply`) torna 0. `INVOKER`: la chiamano il migratore o il job, che
possiedono le tabelle.
