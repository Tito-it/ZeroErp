## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la riga dell'azienda predefinita, il cui cambio fa partire il controllo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica) — il controllo di un cliente, a cui delega
> * [anagrafiche.trgfn_efba_guard_clienti_chiave](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_clienti_chiave) — chi la chiama
> * [anagrafiche.fn_guard_istanza_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_gestore_globale) — la gemella per la regola dell'istanza e dell'azienda

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale` applica il controllo della chiave unica a tutti
i clienti fittizi dei billing account senza collegamento: sono quelli la cui azienda è la predefinita, e
che cambiano chiave tutti insieme quando la predefinita si sposta.

---

### Il raggio largo, ristretto a chi può entrare in conflitto

Spostare l'azienda predefinita cambia l'azienda di ogni billing account non collegato, quindi la chiave di
tutti i loro clienti. La funzione guarda solo quelli che possono occupare una chiave: i clienti delle
istanze fittizie che hanno un periodo. Non guarda i clienti dei billing account collegati: la loro azienda
non cambia, e un doppione fra due clienti collegati non nasce da questo movimento. Un doppione fra un
cliente che segue la predefinita e uno collegato all'azienda nuova, invece, si trova, perché il controllo
del primo cerca su tutta la chiave.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale, sul modello della gemella per l'istanza.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
