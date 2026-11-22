## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata`

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [anagrafiche.trgfn_billing_account_require_istanza_ha_ba](/dbzero/anagrafiche/funzioni/trgfn_billing_account_require_istanza_ha_ba) — lo stesso controllo sulla cancellazione del BA
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
che serve. Il controllo lo fa `anagrafiche.fn_guard_istanza_ha_ba`, lo stesso che chiama il trigger della
cancellazione del BA: la regola si rompe alla nascita dell'istanza o togliendole l'ultimo BA, e il controllo
è uno. Un'istanza cancellata nella stessa transazione, insieme ai suoi BA, non ha più niente da presidiare.

Il nome dice «utility dichiarata» perché una utility è dichiarata sull'istanza dal billing account di quella
utility.

---

### Codici errore

* `E_ISTANZA_SENZA_BA` — l'istanza arriva al COMMIT senza billing account.

---

### Test

* `db/pgtap/anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql` — il trigger differito
  c'è, l'istanza col BA vive, l'istanza senza BA è rifiutata.
* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — la regola intera: l'ultimo BA che non si cancella,
  istanza e BA cancellati insieme.

---

### Note di migrazione

* 2026-05-01 — nasce: bastava uno fra billing account, dati precontrattuali e cliente, col codice
  `E_ISTANZA_UTILITY_SENZA_UTILITY`.
* 2026-10-08 — pretende il billing account, col codice `E_ISTANZA_SENZA_BA`; il codice di prima resta nel catalogo dei messaggi, ma nessuna funzione lo solleva più.

---

{% include-markdown "signature-core.md" %}
