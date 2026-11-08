## 📘 Documentazione Concettuale – Funzione `dbops.fn_cleanup_at_regola`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` fra cui sceglie
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions) — le tabelle per cui la regola non si applica
>
> Approfondimento funzioni:
>
> * [dbops.fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa) — la domanda «la tabella è esclusa?», che qui diventa il motivo `EXCLUDED`
> * [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — il primo lettore: la scadenza scritta all'INSERT
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il secondo: la scadenza scritta sul pregresso
> * [script.fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login) — il terzo: la scadenza ricalcolata a ogni fallimento di login
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — il passo che riceve la colonna base scelta qui
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — §4.5, la regola CLEANUP
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Dice **con quale regola scade una tabella**: la regola `CLEANUP_AT` che vale, il termine in
giorni, la colonna da cui contare e se il pregresso si ricalcola. È la sede unica della regola
di scadenza: la leggono tutti quelli che scrivono `cleanup_at`, così una riga riceve la stessa
scadenza chiunque la scriva.

| Chi la legge | Quando scrive la scadenza |
| --- | --- |
| [trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) | all'`INSERT`, sui registri che non ammettono l'`UPDATE` del job |
| [fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) | nel giro di pulizia, sulle righe che non l'hanno ancora |
| [fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login) | a ogni fallimento di login, sulle tre tabelle dei tentativi |

---

### Quale regola vale

Una sola: fra le regole `CLEANUP_AT` abilitate che coprono schema e tabella (per nome, con il
carattere jolly o con `*all`), quella con la priorità più bassa, e a parità di priorità quella con
l'`id` minore. La regola generica su tutte le tabelle ha una priorità più alta delle regole di
tabella, quindi vale solo dove nessuna regola di tabella c'è.

Non c'è un'applicazione «a strati»: le regole che coprono la stessa tabella non si sommano e non si
susseguono. La regola scelta qui è l'unica che il trigger e il runner applicano.

La forma della regola la garantisce il CHECK del registro
([fn_regola_automazione_valida](/dbzero/dbops/funzioni/fn_regola_automazione_valida)): il termine
c'è sempre ed è un intero ≥ 1, il ricalcolo è un booleano.

---

### Le tre risposte

| Risposta | Che cosa vuol dire | La tabella scade? |
| --- | --- | --- |
| nessuna riga | nessuna regola copre la tabella, oppure schema o tabella sono vuoti | no |
| una riga con `motivo_salto` vuoto | la regola si applica | sì: colonna base + `ttl_days` |
| una riga con `motivo_salto` valorizzato | la regola c'è, ma non si applica | no |

I motivi per cui una regola non si applica sono tre, e sono gli stessi che il runner scrive come
`skip_reason` nel suo audit:

| `motivo_salto` | Quando |
| --- | --- |
| `EXCLUDED` | la tabella ha un'esclusione attiva in `dbops.automation_cleanup_exclusions` ([fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa)) |
| `NO_CLEANUP_COLUMN` | la tabella non ha la colonna `cleanup_at` |
| `MISSING_BASE_TS_COLUMN` | la colonna base dichiarata non esiste sulla tabella, oppure la regola non la dichiara e la catena non ne trova nessuna |

I motivi si controllano in quest'ordine: una tabella esclusa risponde `EXCLUDED` anche se le manca
la colonna.

---

### La colonna base

* Se la regola dichiara `base_ts_column`, la base è quella.
* Se non la dichiara, la base è la prima colonna che la tabella ha fra `data_insert`,
  `executed_at`, `occurred_at`, `created_at`, in quest'ordine.

La risposta riporta la colonna scelta, così chi scrive la scadenza non la deve ricalcolare. Una
base dichiarata ma assente sulla tabella è riportata comunque, insieme al motivo
`MISSING_BASE_TS_COLUMN`: chi legge l'audit vede quale colonna mancava.

⭐ La colonna della scadenza non si sceglie: è sempre `cleanup_at`, nome fisso del framework come
le colonne di audit. Nessun parametro della regola la cambia.

---

### Casi limite

* **Schema o tabella vuoti**: nessuna riga, cioè «non scade». Non è un errore, di proposito: la
  funzione è una lettura chiamata riga per riga da un trigger, e sollevare con il contratto di
  progetto scriverebbe una riga di log. Senza quel ramo la regola generica coprirebbe anche una
  tabella senza nome.
* **Base vuota sulla riga**: la funzione non guarda le righe, solo la tabella. Che una riga con la
  colonna base vuota non riceva scadenza lo decide chi scrive: il trigger lascia `cleanup_at`
  vuoto, il runner non la tocca.
* **Chiamata da una funzione `SECURITY DEFINER`**: ogni nome dentro la funzione è qualificato con
  lo schema, perché la chiama anche il login, che gira con un percorso di ricerca stretto.

---

### Codici errore

La funzione non solleva codici suoi.

---

### Test

* `db/pgtap/dbops/test-cleanup-at-regola-unica-v1.sql` — la regola più specifica vince e la base
  arriva dalla catena; il trigger e il runner danno alla stessa riga la stessa scadenza; una riga
  con la base vuota non riceve scadenza né dall'uno né dall'altro; una tabella esclusa risponde
  `EXCLUDED` e non riceve scadenza, nemmeno se il chiamante ne passa una; una tabella senza base
  risponde `MISSING_BASE_TS_COLUMN`, una senza `cleanup_at` `NO_CLEANUP_COLUMN`; il login scrive
  istante più termine sulle sue tre tabelle; nessuna regola porta più `cleanup_column`.
* `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — le regole dei
  registri di fatturazione ci sono, e una tabella senza regola propria cade sulla generica.

---

### Note di migrazione

* 2026-11-08 — nasce (`20261109-85`, brief-db-revisione-dbops, giro 10b) e riassorbe
  `dbops.fn_cleanup_at_params`, ritirata (`20261109-91`). Prima la regola di scadenza aveva tre
  letture che non coincidevano: il trigger alla nascita sceglieva la regola senza guardare le
  esclusioni, partiva dall'istante della transazione quando la colonna base mancava o era vuota,
  e scriveva sempre `cleanup_at`; il runner applicava le esclusioni, la catena di ripiego e la
  colonna del parametro `cleanup_column`, e applicava in ordine tutte le regole che coprivano la
  tabella; `fn_apply_cleanup_at` ripiegava da sé su `data_insert`. Chi arriva da un link a
  `fn_cleanup_at_params` trova qui la stessa scelta della regola, con in più le esclusioni e la
  colonna base.

---

{% include-markdown "signature-core.md" %}
