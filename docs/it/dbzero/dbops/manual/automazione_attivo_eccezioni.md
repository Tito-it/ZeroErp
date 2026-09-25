# automazione_attivo_eccezioni

### Scopo

Le **FK che l'automazione ATTIVO non lega**. Per una riga — schema e tabella
della **figlia**, colonna FK — `dbops.fn_run_automations_attivo` non genera né
il *block* sul padre («il padre non si spegne con figli attivi») né il
*require* sul figlio («un figlio attivo solo sotto un padre attivo»), e
[`dbops.fn_ritira_attivo_eccezioni`](/dbzero/dbops/manual/fn_ritira_attivo_eccezioni)
toglie quelli già generati.

Serve quando `attivo` sul padre e `attivo` sul figlio rispondono a **due
domande diverse**, e legarli rende impossibile uno stato legittimo.

## Regole

- **Una FK per riga, non una tabella**: le altre coppie della stessa figlia
  restano legate.
- **Il motivo è obbligatorio** (`CHECK`): un'eccezione senza perché è un buco
  nel framework, non una decisione.
- Seed da `80_data`, CSV `dbops/automazione_attivo_eccezioni.csv`, mirror sulla
  chiave naturale. Per ritirare una riga: `DELETE` forward-only (il mirror non
  cancella); il giro successivo dell'automazione rigenera i trigger.

## Le righe

| Figlia · FK | Perché |
| --- | --- |
| `config.profili_accesso_bindings.identita_digitale_id` | **porta e profili** (decisione Tid, 2026-09-25): la veste attiva dice se la porta è aperta, il binding cosa si può fare dentro. La veste OPERATORE nasce spenta e deve poter avere i suoi profili (SUPER_ADMIN compreso) prima dell'invito accettato; spegnere una veste non deve togliere i profili. I lettori dei permessi chiedono già entrambe le cose |

⚠️ Non è la vecchia `automation_fk_exclusions`, ritirata con le funzioni
trigger legacy: quella era un elenco senza motivo e senza ritiro.

Guida: [automazione DB](/guide/automazione-db), §1.3 e §4.2. Presidio:
`db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql`.
