## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preferenza_data_update`

> **Ultimo aggiornamento**: 21 novembre 2026
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

Le preferenze non hanno audit, per scelta: sono un dato personale, scritto solo dal suo proprietario e
spesso. Non hanno `user_insert` né `user_update`, che il trigger d'audit generico scriverebbe. Resta la
data dell'ultima scrittura, e questa funzione è la sua sola sede.

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
