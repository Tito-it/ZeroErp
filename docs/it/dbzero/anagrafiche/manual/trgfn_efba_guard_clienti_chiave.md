## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_clienti_chiave`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la tabella su cui è montata: i collegamenti e la predefinita
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_clienti_chiave_unica_di](/dbzero/anagrafiche/funzioni/fn_guard_clienti_chiave_unica_di) — il controllo dei clienti di un billing account
> * [anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_clienti_chiave_unica_gestore_globale) — il controllo dei clienti che seguono la predefinita
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — un altro guard della stessa tabella, con la stessa scelta del raggio

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_clienti_chiave` è la strada dell'azienda: quando cambia l'azienda di un
billing account, o l'azienda predefinita, controlla alla conferma dell'operazione i clienti la cui chiave è
cambiata con lei.

---

### Quattro movimenti, due raggi

Una riga della tabella è un collegamento fra un billing account e un'azienda, oppure, senza billing account,
l'azienda predefinita. Il trigger guarda la riga e sceglie quali clienti controllare:

| Movimento | Clienti controllati |
| --- | --- |
| un collegamento nasce, cambia azienda o sparisce | quelli del billing account |
| un collegamento passa da un billing account a un altro | quelli di tutti e due |
| la predefinita nasce, cambia azienda o sparisce | tutti i clienti fittizi dei billing account senza collegamento |
| una riga passa da predefinita a collegamento, o il contrario | quelli del billing account e quelli che seguono la predefinita |

Un collegamento che sparisce non libera i clienti dalla regola: il loro billing account passa alla
predefinita, ed è contro quella che si controllano.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
