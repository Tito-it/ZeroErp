## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_emittente_fiscale_pk`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'azienda di cui restituisce l'`id`
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — per quale azienda fattura un billing account, e la predefinita
>
> Approfondimento funzioni:
>
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — la regola dei tre livelli, che questa funzione usa
> * [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) — la gemella che restituisce il ruolo dell'emittente
> * [script.trgfn_doc_guard_emittente_ba](/dbzero/script/funzioni/trgfn_doc_guard_emittente_ba) — il guard dei documenti, che confronta l'azienda del documento con questa

---

### 🎯 Scopo Principale

`anagrafiche.fn_get_emittente_fiscale_pk` dice per quale azienda fattura un billing account, come `id` di
`anagrafiche.emittenti_fiscali`, e solleva quando l'azienda non si risolve. È la funzione per chi scrive su
tabelle che nominano l'azienda con `emittente_fiscale_id`.

---

### Lo stesso lettore della gemella, un'altra chiave

Quale azienda lo decide `script.fn_get_ba_emittente_sr_id`: ogni billing account ha sempre il suo collegamento,
e la risposta è quella; gli altri livelli (l'azienda di chi agisce in sessione, la predefinita) contano solo
nell'istante della nascita. La regola è nella scheda di `anagrafiche.emittenti_fiscali_billing_account`. Questa
funzione e `anagrafiche.fn_get_emittente_fiscale_id` sono due involucri dello stesso lettore: la seconda
restituisce il ruolo dell'emittente, questa lo traduce nell'`id` della tabella. Sullo stesso billing account
rispondono la stessa azienda.

`script.trgfn_doc_guard_emittente_ba` usa l'una o l'altra secondo la colonna del documento: contratti, offerte,
preventivi, ordini, DDT, resi e asset tengono l'`id`, commesse e fatture il ruolo.

---

### Che cosa fa di suo

* **Il billing account è obbligatorio.** Un valore nullo o non positivo è rifiutato (`E_PARAMETRO_INVALIDO`): a
  differenza della gemella, qui non c'è il ripiego sulla predefinita senza billing account.
* **L'azienda risolta deve essere accesa.** Un'azienda spenta conta come non risolta. Il filtro è una difesa:
  un collegamento o la predefinita non possono puntare a un'azienda spenta, e un'azienda collegata non si
  spegne. Se il caso si presentasse, «non risolto» è la risposta giusta, non il ripiego su un'altra azienda.
* **Un'azienda non risolta è un errore**, `E_EMITTENTE_DEFAULT_MISSING`: è l'installazione che non ha nessuna
  azienda, non il chiamante che ha sbagliato.

---

### ⚠️ Che cosa oggi non copre

* **Un billing account che non esiste** non è rifiutato: un id positivo senza collegamento riceve l'azienda di
  chi agisce o la predefinita, come un billing account nell'istante della sua nascita.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il billing account manca o non è positivo.
* `E_EMITTENTE_DEFAULT_MISSING` — nessun livello risponde, o l'azienda risolta è spenta.

---

### Test

* `db/pgtap/anagrafiche/test-fn-get-emittente-fiscale-pk.sql` — il guard sul parametro; i tre livelli, con la
  coppia in sessione e senza sessione (test 6 e 7); il valore che è davvero l'`id` dell'emittente; la delega
  esatta al lettore e l'assenza di una copia della regola nel corpo (test 9 e 10).

---

### Note di migrazione

* 2026-04-07 — nasce accanto a `fn_get_emittente_fiscale_id`, che nonostante il nome restituisce il ruolo.
* 2026-09-13 — non tiene più una sua copia della regola a due livelli: delega al lettore, che ha il terzo
  livello «azienda di chi agisce». Con la copia, la stessa azienda sarebbe stata vista dalla RLS e respinta dal
  guard di un documento.
* 2026-11-26 — ogni billing account ha sempre il suo collegamento: i livelli dopo il primo riguardano solo la
  nascita.

---

{% include-markdown "signature-core.md" %}
