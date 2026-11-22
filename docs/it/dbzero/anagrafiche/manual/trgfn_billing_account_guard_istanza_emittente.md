## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_guard_istanza_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza, i cui billing account sono di un'azienda sola
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — il controllo a cui delega
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — lo stesso controllo, quando cambia il collegamento all'azienda
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento della nascita, che deve venire prima
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility#unistanza-unazienda) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_guard_istanza_emittente` verifica, quando nasce un billing account, che sia
della stessa azienda degli altri billing account della sua istanza. Il controllo vero sta in
`fn_guard_istanza_ba_emittente`: il trigger dice solo quando.

---

### ⭐ Un'istanza, un'azienda

Un'istanza ha un billing account per utility, e tutti fatturano per la stessa azienda: così la domanda «di
quale azienda è questa istanza?» ha una risposta sola. Il controllo confronta l'azienda risolta del billing
account nuovo con quella di ciascun fratello, anche fuori dal perimetro di chi scrive (la funzione a cui delega
è privilegiata), e rifiuta con `E_ISTANZA_EMITTENTI_DIVERSI`.

---

### Solo alla nascita, dopo il collegamento

Il trigger scatta dopo l'inserimento, in fascia `z95`: l'azienda del billing account nuovo esiste quando esiste
il suo collegamento, che `trgfn_billing_account_link_ef` scrive in fascia `z90`.

Solo all'inserimento, perché un billing account non cambia fratelli: la sua coppia (istanza, utility) è
bloccata (`E_BA_ISTANZA_IMMUTABILE`). La sua azienda cambia solo dal collegamento, e lì lo stesso controllo lo
chiama `trgfn_efba_guard_istanza_emittente`.

---

### ⚠️ Che cosa oggi non copre

* **Un collegamento scritto dopo l'inserimento arriva tardi.** Senza utente in sessione il trigger `z90` non
  scrive niente, e il controllo giudica il billing account nuovo con l'azienda predefinita: se i fratelli sono
  collegati a un'altra azienda, il secondo billing account di un'istanza è rifiutato anche quando chi lo crea
  stava per collegarlo a quella giusta (è il limite di `fn_crea_billing_account` senza sessione).

---

### Codici errore

* `E_ISTANZA_EMITTENTI_DIVERSI` — da `fn_guard_istanza_ba_emittente`: il billing account nuovo e un fratello
  risolvono ad aziende diverse.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — il secondo billing account della stessa azienda
  passa; lo spostamento di un fratello su un'altra azienda, dal collegamento, è rifiutato.
* `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` — l'istanza quando si sposta l'azienda
  predefinita.

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «un'istanza, un'azienda».

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

{% include-markdown "signature-core.md" %}
