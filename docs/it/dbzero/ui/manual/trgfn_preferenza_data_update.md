## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preferenza_data_update`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — una delle due tabelle su cui è montata
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — l'altra
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — il guard di forma, che scatta prima
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — l'audit delle altre tabelle

---

### 🎯 Scopo Principale

`ui.trgfn_preferenza_data_update` scrive `data_update` di una preferenza, di lista o di dashboard, a ogni
INSERT e UPDATE: è l'ora della transazione che scrive. Il valore che arriva da chi scrive non conta.

---

### Perché non l'audit generico

Le preferenze non hanno audit, per scelta: sono un dato personale, scritto spesso dal suo proprietario.
Non hanno `user_insert` né `user_update`, che il trigger d'audit generico scriverebbe. Resta la data
dell'ultima scrittura, e questa funzione è la sua sola sede.

L'ultima scrittura è quella della riga, chiunque la faccia: anche il database riscrive una preferenza,
quando una colonna, una card o una misura che nomina esce dal catalogo
([trgfn_voce_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_voce_ritira_dalle_preferenze),
[trgfn_misure_pagina_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_misure_pagina_ritira_dalle_preferenze)),
e anche allora `data_update` si sposta. Non dice quando l'utente ha salvato l'ultima volta.

---

### Dove è montata

Su `ui.lista_preferenza_utente` e su `ui.dashboard_preferenza_utente`, `BEFORE INSERT OR UPDATE`, nella
fase delle derivazioni (`a20`): dopo il guard di forma, senza elenco di colonne, perché ogni scrittura della
riga è una scrittura della preferenza.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-ui-catalogo-dashboard-v1.sql` — all'INSERT e all'UPDATE `data_update` è l'ora della
  transazione, anche se chi scrive ne manda un'altra; la colonna è `NOT NULL` sulle due tabelle.

---

### Note di migrazione

* 2026-11-21 — nasce; prima `data_update` la scriveva il backend nel salvataggio.

---

{% include-markdown "signature-core.md" %}
