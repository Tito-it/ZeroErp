## 📘 Documentazione Concettuale – Funzione `dbops.fn_drop_triggers_by_function_args`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola ATTIVO, col parametro `reconcile_on_change` che accende questa pulizia
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — l'unico chiamante
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la funzione dei trigger *require* che toglie
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — la funzione dei trigger *block* che toglie
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — la lettura condivisa degli argomenti, che qui non si usa
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — la regola ATTIVO

---

### 🎯 Scopo Principale

Toglie da una tabella i trigger che eseguono una certa funzione con **esattamente** certi
argomenti, e dice quanti ne ha tolti. Serve al runner della regola ATTIVO per sgombrare il posto
prima di rimontare un trigger *block* o *require* con la forma di oggi.

La chiama soltanto `dbops.fn_run_automations_attivo`, quando la regola ha
`reconcile_on_change` acceso (è il default) e sta per creare un trigger: prima toglie quelli
con la stessa funzione e gli stessi argomenti, poi crea.

---

### Che cosa toglie

* Solo i trigger **utente** della tabella indicata; i trigger interni di PostgreSQL restano.
* Se la tabella indicata è una **partizione**, non toglie niente: i trigger di una tabella
  partizionata si governano sul padre.
* Un trigger si toglie quando la sua definizione contiene la chiamata alla funzione con quegli
  argomenti, nello stesso ordine e separati da virgola e spazio. Un trigger sulla stessa
  funzione con argomenti diversi resta.

---

### ⚠️ Il confronto è sul testo della definizione

La funzione ricostruisce la chiamata attesa come testo (schema, nome, argomenti fra apici) e la
cerca nella definizione che PostgreSQL restituisce per ogni trigger. Ne vengono tre
conseguenze:

* **Dipende dal `search_path` di chi chiama.** PostgreSQL scrive il nome della funzione con lo
  schema solo se lo schema **non** è nel `search_path` della sessione. Il testo atteso porta
  sempre lo schema: con `dbops` nel `search_path` la definizione dice la funzione senza schema,
  il confronto non trova niente e la funzione non toglie niente, senza errore. Per lo stesso
  motivo la doc auto-generata fissa il `search_path` a `public` prima di leggere le definizioni.
* Il confronto è un `ILIKE`: il trattino basso degli argomenti vale come jolly, e un argomento
  che differisce per un carattere in quella posizione si considera uguale.
* La grammatica degli argomenti è ricopiata qui, invece di passare da
  `dbops.fn_trigger_argomenti`, che legge gli argomenti salvati e non il testo. Le
  [linee guida dei trigger](/linee-guida-trigger#il-nome-della-funzione-trigger) chiedono a chi
  legge gli argomenti da fuori di usare la lettura condivisa.

---

### Non scrive audit e non solleva

Toglie i trigger con `DROP TRIGGER IF EXISTS`, uno alla volta, e restituisce il conteggio.
Non scrive in `dbops.audit_log`: la traccia la lascia, se serve, il runner che la chiama. Non ha
codici errore propri; un errore del `DROP` (un lock, un privilegio) arriva al chiamante così
com'è.

---

### Test

Nessun pgTAP la chiama per nome. Il ramo che la usa (riconciliazione della regola ATTIVO) non ha
una prova di comportamento.

---

### Note di migrazione

* 2025-08-28 — nasce nel primo albero dei changeSet (`db/changelog/migrations/50_dbops`).
* 2026-01-13 — ultima versione del corpo: esclude le partizioni.

---

{% include-markdown "signature-core.md" %}
