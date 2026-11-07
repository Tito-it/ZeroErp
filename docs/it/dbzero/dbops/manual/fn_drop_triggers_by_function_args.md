## 📘 Documentazione Concettuale – Funzione `dbops.fn_drop_triggers_by_function_args`

> **Ultimo aggiornamento**: 7 novembre 2026
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
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — la lettura degli argomenti salvati di un trigger
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
* La funzione si indica con schema e nome, e si riconosce per **identità**: la risposta è la stessa
  con qualunque `search_path` di chi chiama. Una funzione che non esiste non ha trigger da togliere,
  e la risposta è zero.
* Gli argomenti si confrontano con quelli **salvati** del trigger (`dbops.fn_trigger_argomenti`):
  stesso numero, stesso ordine, stesso testo. Un trigger sulla stessa funzione con argomenti
  diversi resta; una maiuscola o un trattino basso diversi fanno un argomento diverso.
* È generica: confronta l'elenco intero degli argomenti, senza sapere che cosa significano. La
  grammatica di una famiglia di trigger la applica chi la chiama.

---

### Non scrive audit e non solleva

Toglie i trigger con `DROP TRIGGER IF EXISTS`, uno alla volta, e restituisce il conteggio.
Non scrive in `dbops.audit_log`: la traccia la lascia, se serve, il runner che la chiama. Non ha
codici errore propri; un errore del `DROP` (un lock, un privilegio) arriva al chiamante così
com'è.

---

### Test

`dbops/test-trigger-attivo-riconoscimento-per-funzione-v1`: toglie il solo trigger con gli
argomenti chiesti e lascia gli altri sulla stessa tabella, anche col `search_path`
dell'applicazione; per una funzione che non esiste risponde zero.

---

{% include-markdown "signature-core.md" %}
