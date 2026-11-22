## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_guard_chiave_unica`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica) — il controllo a cui delega
> * [anagrafiche.trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — ricava dalle date il periodo che qui si confronta
> * [anagrafiche.trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date) — il guard degli stati e delle date, che il periodo presuppone

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_guard_chiave_unica` è la strada del cliente: a ogni nascita e a ogni modifica
di un cliente, alla conferma dell'operazione, controlla che quel cliente non duplichi una fornitura già
occupata.

---

### Ogni scrittura del cliente, al COMMIT

Il trigger scatta su qualunque modifica del cliente, non su un elenco di colonne: la chiave può cambiare per
lo stato (un pre-contrattuale che si attiva entra nella chiave) e per le date (un'attivazione anticipata, una
chiusura). Il controllo legge il cliente com'è alla conferma, quindi una sequenza di scritture sullo stesso
cliente si giudica sul risultato finale. Il trigger non decide niente: passa il cliente al controllo.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
