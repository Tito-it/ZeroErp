## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_istanza_emittente`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — la tabella su cui è montato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — il controllo su un billing account
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — il gemello sull'albero
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_istanza_emittente` fa scattare il controllo «un'istanza, un'azienda» quando il
collegamento di un billing account nasce o cambia azienda.

---

### Gli stessi movimenti del gemello sull'albero

È montata dopo ogni inserimento, modifica e cancellazione di una riga, e giudica solo il collegamento di un
billing account:

* un collegamento che **nasce** (alla nascita del billing account) o **cambia azienda**: controlla quel
  billing account contro gli altri della sua istanza.

Il resto non tocca nessuna istanza: la cancellazione del collegamento e il suo passaggio a un altro billing
account li rifiutano prima i trigger `a05` della tabella, e la riga della predefinita non si giudica, perché
spostarla non cambia l'azienda di nessun billing account.

Scatta dopo la scrittura perché il controllo rilegge il collegamento per risolvere l'azienda, e parla dopo il
controllo dell'albero. Il cancello della storia sugli stessi movimenti scatta prima: i controlli si sommano.

---

### Codici errore

* `E_ISTANZA_EMITTENTI_DIVERSI` — dal controllo che chiama.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — il secondo billing account di un'istanza spostato
  su un'altra azienda: rifiutato.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — la predefinita spostata su un'altra
  azienda passa, e il billing account resta all'azienda del suo collegamento (test 7 e 8).

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «un'istanza, un'azienda».
* 2026-11-26 — giudica solo il collegamento di un billing account che nasce o cambia azienda: i rami della
  cancellazione, dello spostamento e della predefinita sono ritirati.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
