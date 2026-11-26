## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_clienti_chiave`

> **Ultimo aggiornamento**: 26 novembre 2026
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
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — un altro guard della stessa tabella, con la stessa scelta della riga da giudicare

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_clienti_chiave` è la strada dell'azienda: quando il collegamento di un billing
account nasce o cambia azienda, controlla alla conferma dell'operazione i clienti di quel billing account, la
cui chiave contiene l'azienda.

---

### Un movimento, un billing account

Una riga della tabella è un collegamento fra un billing account e un'azienda, oppure, senza billing account,
l'azienda predefinita. Il trigger giudica solo il collegamento di un billing account, quando nasce o quando
la sua azienda cambia, e controlla i clienti di quel billing account.

Gli altri movimenti non cambiano la chiave di nessuno:

* la riga della predefinita non si giudica: spostarla decide solo l'azienda dei billing account che
  nasceranno, non quella di un cliente che c'è già;
* il collegamento non si cancella e non passa a un altro billing account: lo rifiutano prima i trigger `a05`
  della tabella (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, `E_BA_COLLEGAMENTO_NON_SI_SPOSTA`), e sulla cancellazione
  il trigger non fa niente.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale.
* 2026-11-26 — perde i rami dell'azienda predefinita e del collegamento che sparisce o si sposta: ogni
  billing account ha sempre il suo collegamento, che non si toglie.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
