## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_override_col`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — il registro delle eccezioni di nome
>
> Approfondimento funzioni:
>
> * [dbops.fn_col_exists](/dbzero/dbops/funzioni/fn_col_exists) — verifica che la colonna restituita esista davvero
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — la chiede per la colonna `attivo`
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — la chiede per la chiave verso lo storico
> * [dbops.fn_storico_risolvi_scope](/dbzero/dbops/funzioni/fn_storico_risolvi_scope) — la chiede per la chiave verso lo storico
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la chiede, a ogni scrittura, per la colonna `attivo` del padre
> * [dbops.fn_get_lookup_codici](/dbzero/dbops/funzioni/fn_get_lookup_codici) — legge lo stesso registro direttamente, per i ruoli dei codici
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — le convenzioni di nome su cui le automazioni contano

---

### 🎯 Scopo Principale

Restituisce il nome della colonna che una tabella usa per un **ruolo** delle automazioni (la colonna
`attivo`, la chiave verso lo storico…): l'eccezione registrata in
`dbops.automation_overrides_cols`, se c'è, altrimenti il nome di convenzione che il chiamante passa.
Restituisce sempre un nome.

---

### Le automazioni lavorano per convenzione, con eccezioni scritte

I runner delle automazioni si aspettano nomi di colonna fissi. Una tabella che per una buona
ragione ne usa un altro non si rinomina e non si esclude: si registra l'eccezione, una riga per
tabella e ruolo. La chiave del registro è (schema, tabella, ruolo), quindi l'eccezione è al più una.

I ruoli sono quelli che i chiamanti chiedono, scritti in maiuscolo: `ATTIVO_COL` (i runner e i due
trigger di attivazione padre/figlio), `STORICO_FK` e `STORICIZZA_COL`. Il registro porta anche
ruoli che non passano da qui: `CODICE_COL` e `CODICE_INTERNO_COL` li legge direttamente
`dbops.fn_get_lookup_codici`. Le colonne di audit (`data_update`, `user_update`) non hanno
eccezioni: hanno nome fisso per contratto.

⚠️ La funzione non verifica che la colonna restituita esista: lo fa il chiamante, di norma con
`dbops.fn_col_exists`.

---

{% include-markdown "signature-core.md" %}
