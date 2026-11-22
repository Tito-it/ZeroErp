## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_clienti_chiave_unica_di`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — i clienti che passa al controllo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica) — il controllo di un cliente, a cui delega
> * [anagrafiche.trgfn_efba_guard_clienti_chiave](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_clienti_chiave) — la chiama per i clienti di un billing account
> * [anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_guard_clienti_chiave) — la chiama per i clienti di un'istanza

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_clienti_chiave_unica_di` applica il controllo della chiave unica a tutti i clienti di
un billing account o di un'istanza: serve quando a cambiare non è il cliente ma un dato da cui la sua chiave
dipende.

---

### Due insiemi, nessun «tutti»

I due parametri scelgono i clienti da guardare: quelli del billing account, quelli dell'istanza, o
l'unione dei due quando sono passati entrambi. Un parametro vuoto non vuol dire «tutti»: con tutti e due
vuoti non si controlla niente. Il caso in cui la chiave cambia per tutti i clienti senza collegamento ha la
sua funzione, `anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale`.

La funzione non filtra: passa al controllo ogni cliente trovato, e il controllo lascia andare da solo chi
non occupa la chiave. Il primo cliente in conflitto, nell'ordine degli id, ferma l'operazione.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale, per le strade del collegamento all'azienda e
  dell'istanza fittizia.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
