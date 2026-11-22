## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_cliente_chiave_unica`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il cliente controllato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_clienti_stessa_chiave](/dbzero/anagrafiche/funzioni/fn_clienti_stessa_chiave) — chi occupa la chiave, la lettura su cui decide
> * [anagrafiche.fn_guard_clienti_chiave_unica_di](/dbzero/anagrafiche/funzioni/fn_guard_clienti_chiave_unica_di) — lo applica ai clienti di un billing account o di un'istanza
> * [anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_clienti_chiave_unica_gestore_globale) — lo applica ai clienti che seguono l'azienda predefinita
>
> Guide:
>
> * [Un cliente manuale per soggetto, servizio e azienda](/guide/gestione-delle-istanze-utility#un-cliente-manuale-per-soggetto-servizio-e-azienda) — la regola raccontata a chi usa il gestionale

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_cliente_chiave_unica` è il controllo della chiave unica su **un** cliente: rifiuta il
cliente se un altro cliente con lo stesso soggetto, servizio e azienda occupa la stessa fornitura in un
periodo che si sovrappone al suo.

---

### Un cliente alla volta, su una sola lettura

Il controllo prende la chiave del cliente (soggetto, servizio e l'azienda del suo billing account per
l'installazione) e chiede a `anagrafiche.fn_clienti_stessa_chiave` chi la occupa. Confronta il periodo del
cliente con quello degli altri: non ripete il criterio degli stati, che sta tutto nella lettura. Un cliente
che non occupa la chiave (istanza non fittizia, annullato, pre-contrattuale, aggregante, senza periodo) non
esce dalla lettura, quindi non si sovrappone a nessuno e passa.

Un cliente che non esiste più nella stessa operazione non ha niente da presidiare, e un id vuoto non
controlla niente.

---

### Codici errore

* `E_CLIENTE_STESSA_CHIAVE` — un altro cliente occupa la stessa chiave in un periodo che si sovrappone. Il
  messaggio porta il codice del billing account di quel cliente, il primo per data di attivazione se sono
  più d'uno.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale (decisioni di Tid del 2026-10-13).

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
