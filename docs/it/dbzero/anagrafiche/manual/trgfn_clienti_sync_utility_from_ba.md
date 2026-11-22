## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_sync_utility_from_ba`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella su cui scatta
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto da cui si copiano ruolo e utility
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il PDP, che dev'essere della stessa utility
> * [config.utilities](/dbzero/config/tabelle/utilities) — la utility, che dice se il PDP è obbligatorio
>
> Approfondimento funzioni:
>
> * [script.fn_cliente_dal_billing_account](/dbzero/script/funzioni/fn_cliente_dal_billing_account) — la copia di ruolo e utility dal billing account, comune ai documenti
> * [anagrafiche.trgfn_clienti_sync_pdp](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp) — la copia del PDP dall'istanza, che per nome viene prima
> * [anagrafiche.trgfn_clienti_guard_ruolo_cliente](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_ruolo_cliente) — il controllo del ruolo, che per nome viene prima

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_sync_utility_from_ba` tiene la fornitura del cliente coerente col suo billing
account e col suo PDP: ruolo e utility sono copie del conto, il PDP c'è quando la utility lo richiede ed è della
stessa utility.

---

### ⭐ Ruolo e utility sono copie del billing account

Il billing account dice già di quale cliente e di quale utility è. La copia la fa
`script.fn_cliente_dal_billing_account`, la stessa che usano i documenti di vendita per il loro cliente: un
valore che manca lo scrive, uno che dissente lo rifiuta. Così la regola della copia sta in un posto solo.

Alla nascita del cliente la copia si fa sempre. Su una modifica si fa solo se chi scrive cambia billing
account, ruolo o utility, e in quel caso ha già risposto il blocco della fornitura
(`E_CLIENTE_FORNITURA_IMMUTABILE`): in pratica la copia lavora alla nascita.

La utility si può non passare: la scrive la copia. Il ruolo no, perché il suo controllo viene prima della copia
e rifiuta un ruolo mancante.

---

### Il PDP della utility

* **Obbligatorio quando la utility lo richiede** (`config.utilities.richiede_pdp`): un cliente del gas senza
  PDP è rifiutato.
* **Della stessa utility del cliente**: un PDP della luce non va sotto un cliente del gas.

Il PDP che il trigger giudica è già quello dell'istanza: la copia di `anagrafiche.trgfn_clienti_sync_pdp` per
nome viene prima. I due controlli valgono a ogni scrittura del cliente.

---

### Codici errore

* `E_DOC_CLIENTE_DIVERSO_DA_BA` — il ruolo o la utility passati non sono quelli del billing account (dalla
  copia). Il campo è la colonna che dissente.
* `E_PDP_OBBLIGATORIO` — la utility richiede il PDP e il cliente non ce l'ha.
* `E_PDP_UTILITY_MISMATCH` — il PDP è di un'altra utility.
* `E_CODICE` — il billing account non si trova (o chi scrive non lo vede), oppure la utility non è nel catalogo.

---

### Test

* `db/pgtap/anagrafiche/test-clienti-sync-utility-pdp-policy.sql` — la utility copiata dal billing account con
  e senza PDP, il PDP mancante per una utility che lo richiede, il PDP di un'altra utility.

---

### Note di migrazione

* 2026-10-10 — la copia di ruolo e utility passa a `script.fn_cliente_dal_billing_account`, comune ai
  documenti, e copre anche il ruolo. Escono `E_BILLING_ACCOUNT_UTILITY_NULL` (la utility del billing account è
  obbligatoria) ed `E_CLIENTE_UTILITY_MISMATCH_BA`, che il trigger non solleva più.

---

{% include-markdown "signature-core.md" %}
