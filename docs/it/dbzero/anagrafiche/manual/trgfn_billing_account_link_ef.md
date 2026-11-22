## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_link_ef`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento che scrive
>
> Approfondimento funzioni:
>
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — l'azienda di chi agisce
> * [anagrafiche.trgfn_billing_account_guard_admin_globale](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale) — il guard che, prima, esige un'azienda su cui scrivere
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il verbo, che senza sessione scrive lui il collegamento
> * [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — quando il collegamento non si corregge più
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — il trigger di quella regola

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_link_ef` collega ogni billing account appena nato all'azienda di chi lo
crea, scrivendo la sua riga in `emittenti_fiscali_billing_account`.

---

### ⭐ Un billing account nasce già della sua azienda

Il trigger scatta dopo l'inserimento, in fascia `z90`. L'azienda è quella di chi agisce, la stessa che la
lettura dell'azienda dà in sessione a un billing account non ancora collegato
(`script.fn_resolve_emittente_for_user`): l'azienda di lavoro scelta in sessione, se è nel perimetro
dell'utente, altrimenti quella a cui l'utente appartiene. Il collegamento è proprio del billing account
(`is_default` falso), mai la riga dell'azienda predefinita.

Così un billing account non passa mai da uno stato «senza azienda»: nell'istante fra l'inserimento e il
collegamento la lettura risponde già con l'azienda che il trigger sta per scrivere. I guard che confrontano
l'azienda di più billing account (l'istanza, l'albero padre/figli) girano dopo, in fascia `z95`, e leggono il
collegamento scritto.

---

### Quando non scrive niente

* **Senza utente in sessione** (seed, migrazioni, job, il provisioning): il collegamento, se serve, lo scrive
  chi crea, per esempio `fn_crea_billing_account` con l'azienda indicata; senza, il billing account segue
  l'azienda predefinita.
* **Utente senza azienda** in un'installazione senza aziende attive: non c'è niente da collegare. Con aziende
  attive il caso non arriva qui, lo ha già rifiutato il guard della creazione.
* **Collegamento già presente** per il billing account: il trigger non lo duplica.

---

### ⚠️ La finestra di correzione si apre qui

Se chi crea lavorava sull'azienda sbagliata, il billing account nasce collegato male. Il collegamento si
corregge solo finché il billing account non ha storia: la definisce `fn_guard_ba_cambio_emittente`, e la
presidia `trgfn_efba_guard_storia_emittente`. Dopo, il cliente resta all'azienda che ha emesso i suoi
documenti.

---

### ⚠️ Che cosa oggi non copre

* **Un utente in sessione illeggibile vale come assente.** Un `app.current_user_id` che non è un numero non
  solleva: il trigger non scrive il collegamento, come il guard della creazione non giudica.

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` — senza utente nessun collegamento; l'operatore
  ottiene il collegamento alla sua azienda, non duplicato.
* `db/pgtap/rls/test-rls-billing-account-returning-secondo-emittente.sql` — l'operatore di un'azienda non
  predefinita crea con `RETURNING`, e il collegamento va alla sua azienda.
* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — con l'operatore in sessione il collegamento lo scrive
  il trigger, e il verbo rifiuta un'azienda chiesta diversa.

---

### Note di migrazione

* 2026-04-08 — nasce: il collegamento all'azienda diventa immediato, e l'azienda predefinita resta la riserva
  di chi crea senza sessione.
* 2026-08-04 — l'azienda di chi agisce comprende l'azienda di lavoro scelta in sessione.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

{% include-markdown "signature-core.md" %}
