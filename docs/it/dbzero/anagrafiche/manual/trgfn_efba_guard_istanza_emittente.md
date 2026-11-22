## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_efba_guard_istanza_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [anagrafiche.fn_guard_istanza_ba_gestore_globale](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_gestore_globale) — il controllo sullo spostamento della predefinita
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — il gemello sull'albero
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_efba_guard_istanza_emittente` fa scattare il controllo «un'istanza, un'azienda» a ogni
movimento del collegamento fra billing account e azienda, nascita compresa.

---

### Gli stessi movimenti del gemello sull'albero

È montata dopo ogni inserimento, modifica e cancellazione di una riga, e smista:

* un collegamento che **nasce** (anche alla nascita del billing account), **cambia azienda** o **si
  cancella**: controlla quel billing account contro gli altri della sua istanza;
* una modifica che **sposta** la riga da un billing account a un altro: controlla tutti e due, e se uno dei due
  lati è la predefinita (la riga diventa predefinita, o smette di esserlo) controlla anche lo spostamento della
  predefinita;
* la riga **senza billing account**, cioè la predefinita: controlla tutte le istanze con un billing account
  senza collegamento.

Scatta dopo la scrittura perché il controllo rilegge il collegamento per risolvere l'azienda, e parla dopo il
controllo dell'albero. Il cancello della storia sugli stessi movimenti scatta prima: i controlli si sommano.

---

### ⚠️ Che cosa oggi non copre

* **Lo scollegamento fatto in sessione** si giudica con l'azienda di chi agisce, non con la predefinita su cui
  il billing account ricade (vedi `fn_check_ba_coppia_emittente_omogenea`).

---

### Codici errore

* `E_ISTANZA_EMITTENTI_DIVERSI` — dai due controlli che chiama.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — il secondo billing account di un'istanza spostato
  su un'altra azienda: rifiutato.
* `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` — la predefinita spostata sopra un'istanza
  mista: rifiutata, chiunque la sposti.

---

### Note di migrazione

* 2026-10-08 — nasce con la regola «un'istanza, un'azienda».

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
