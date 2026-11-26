## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza che nasce
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account che dichiara la utility
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_istanza_ha_ba](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ha_ba) — il controllo a cui delega
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il billing account non si cancella, e l'istanza non lo perde
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — l'istanza nasce col suo billing account

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata` pretende che un'istanza appena nata abbia,
al COMMIT, almeno un billing account.

---

### Istanza e billing account nascono insieme

Un'istanza senza billing account non è uno stato del suo ciclo di vita: è un dato fuori regola. Il trigger è
differito al COMMIT, così nella stessa transazione l'istanza si scrive prima o dopo il suo BA, nell'ordine
che serve. Il controllo lo fa `anagrafiche.fn_guard_istanza_ha_ba`. È l'unica strada da presidiare: dopo la
nascita un'istanza non perde il suo billing account, perché il billing account non si cancella
(`E_BA_NON_SI_CANCELLA`) e non si sposta su un'altra istanza (`E_BA_ISTANZA_IMMUTABILE`).

Il nome dice «utility dichiarata» perché una utility è dichiarata sull'istanza dal billing account di quella
utility.

---

### Codici errore

* `E_ISTANZA_SENZA_BA` — l'istanza arriva al COMMIT senza billing account.

---

### Test

* `db/pgtap/anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql` — il trigger differito
  c'è, l'istanza col BA vive, l'istanza senza BA è rifiutata.
* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — la regola intera: l'istanza senza BA rifiutata,
  il BA che non si cancella, nemmeno insieme alla sua istanza.

---

### Note di migrazione

* 2026-05-01 — nasce: bastava uno fra billing account, dati precontrattuali e cliente, col codice
  `E_ISTANZA_UTILITY_SENZA_UTILITY`.
* 2026-10-08 — pretende il billing account, col codice `E_ISTANZA_SENZA_BA`; il codice di prima resta nel catalogo dei messaggi, ma nessuna funzione lo solleva più.
* 2026-11-26 — il controllo gemello sulla cancellazione del billing account è ritirato: il billing account non
  si cancella più.

---

{% include-markdown "signature-core.md" %}
