## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_link_ef`

> **Ultimo aggiornamento**: 26 novembre 2026
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
> * [script.fn_utente_di_sessione](/dbzero/script/funzioni/fn_utente_di_sessione) — l'utente della richiesta, letto da una sede sola
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — l'azienda di chi agisce
> * [anagrafiche.trgfn_billing_account_guard_admin_globale](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale) — il guard che, prima, esige un'azienda su cui scrivere
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il verbo, che senza sessione modifica il collegamento verso l'azienda chiesta
> * [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — quando il collegamento non si corregge più
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — il trigger di quella regola

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_link_ef` collega ogni billing account appena nato a un'azienda, scrivendo
la sua riga in `anagrafiche.emittenti_fiscali_billing_account`: l'azienda di chi lo crea, oppure, senza
sessione o senza un'azienda di chi agisce, l'azienda predefinita. Senza nessuna azienda il billing account
non nasce.

---

### ⭐ Un billing account nasce già della sua azienda

Il trigger scatta dopo l'inserimento, in fascia `z90`, e sceglie l'azienda così:

1. **chi agisce**: l'azienda dell'utente di sessione (`script.fn_resolve_emittente_for_user`), cioè l'azienda
   di lavoro scelta in sessione, se è nel perimetro dell'utente, altrimenti quella a cui l'utente appartiene;
2. **la predefinita**, senza utente in sessione (seed, migrazioni, job, il provisioning) o se l'utente non ha
   un'azienda;
3. **nessuna**: nell'installazione non c'è nessuna azienda, e la nascita è rifiutata
   (`E_EMITTENTE_DEFAULT_MISSING`). Un cliente fattura sempre per qualcuno.

Il collegamento è proprio del billing account (`is_default` falso), mai la riga dell'azienda predefinita,
anche quando ne porta l'azienda: da lì in poi il billing account è di quell'azienda, e spostare la
predefinita non lo tocca.

Così un billing account non passa mai da uno stato «senza azienda»: nell'istante fra l'inserimento e il
collegamento la lettura risponde già con l'azienda che il trigger sta per scrivere. I guard che confrontano
l'azienda di più billing account (l'istanza, l'albero padre/figli) girano dopo, in fascia `z95`, e leggono il
collegamento scritto.

---

### L'utente si legge senza ingoiarne il rifiuto

L'utente si legge da `script.fn_utente_di_sessione`, che rifiuta un `app.current_user_id` che non è l'id di
un utente (`E_SCRIPT_CHIAMATA_NON_VALIDA`): il rifiuto sale fino a chi scrive, e il billing account non nasce.
Un utente illeggibile non diventa «nessun utente», che porterebbe il billing account alla predefinita senza
che nessuno abbia controllato chi lo crea.

---

### Quando non scrive niente

* **Collegamento già presente** per il billing account (una doppia esecuzione): il trigger non lo duplica.
* Un **utente senza azienda** in un'installazione con aziende attive non arriva qui: lo ha già rifiutato il
  guard della creazione (`anagrafiche.trgfn_billing_account_guard_admin_globale`).

Chi crea senza sessione e vuole un'azienda diversa dalla predefinita la ottiene modificando il collegamento
appena nato, come fa `anagrafiche.fn_crea_billing_account`.

---

### ⚠️ La finestra di correzione si apre qui

Se chi crea lavorava sull'azienda sbagliata, il billing account nasce collegato male. Il collegamento si
corregge modificandone l'azienda, solo finché il billing account non ha nessun documento, anche in bozza: lo
decide `anagrafiche.fn_guard_ba_cambio_emittente`, e lo presidia `anagrafiche.trgfn_efba_guard_storia_emittente`.
Dopo, il cliente resta all'azienda dei suoi documenti.

---

### Codici errore

* `E_EMITTENTE_DEFAULT_MISSING` — nell'installazione non c'è nessuna azienda a cui collegare il billing account.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — da `script.fn_utente_di_sessione`: `app.current_user_id` non è l'id di un
  utente.

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` — senza utente il collegamento alla predefinita;
  l'operatore ottiene il collegamento alla sua azienda, non duplicato.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — nessun billing account senza collegamento.
* `db/pgtap/anagrafiche/test-billing-account-utente-illeggibile-v1.sql` — l'utente illeggibile è rifiutato, e la
  lettura non sta in un blocco che ingoia gli errori.
* `db/pgtap/rls/test-rls-billing-account-returning-secondo-emittente.sql` — l'operatore di un'azienda non
  predefinita crea con `RETURNING`, e il collegamento va alla sua azienda.
* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — con l'operatore in sessione il collegamento lo scrive
  il trigger, e il verbo rifiuta un'azienda chiesta diversa.

---

### Note di migrazione

* 2026-04-08 — nasce: il collegamento all'azienda diventa immediato, e l'azienda predefinita resta la riserva
  di chi crea senza sessione.
* 2026-08-04 — l'azienda di chi agisce comprende l'azienda di lavoro scelta in sessione.
* 2026-11-26 — senza sessione collega alla predefinita (prima non collegava, e il billing account seguiva la
  predefinita quando si spostava); senza nessuna azienda rifiuta la nascita; l'utente illeggibile non è più
  ingoiato.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

{% include-markdown "signature-core.md" %}
