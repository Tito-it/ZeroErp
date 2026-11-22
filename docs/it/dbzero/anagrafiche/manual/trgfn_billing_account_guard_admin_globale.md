## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_guard_admin_globale`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'appartenenza di un utente a un'azienda
>
> Approfondimento funzioni:
>
> * [script.fn_check_user_can_create_ba](/dbzero/script/funzioni/fn_check_user_can_create_ba) — la regola «può creare?»
> * [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) — l'azienda di lavoro è nel perimetro dell'utente?
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento che questa regola rende possibile

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_guard_admin_globale` rifiuta la creazione di un billing account a chi non ha
un'azienda su cui scriverlo: senza, il collegamento della nascita non saprebbe a quale azienda legare il nuovo
cliente.

---

### Chi può creare

La regola sta in `script.fn_check_user_can_create_ba`; il trigger la chiama prima di ogni inserimento. Crea
chi ha almeno una di queste:

* un'**azienda di lavoro** in sessione (`app.current_emittente_id`) che sta nel suo perimetro: è la strada del
  super admin, che sceglie l'azienda in alto; un'azienda fuori perimetro non conta;
* un'**appartenenza** a un'azienda (`config.user_emittenti_fiscali`): è la strada dell'operatore.

Senza nessuna delle due si crea solo in un'installazione che non ha aziende attive. Il caso tipico del rifiuto
è il super admin in «Tutti gli emittenti».

Il nome dice «admin globale» perché la regola, alla nascita, vietava la creazione a chiunque non avesse
un'appartenenza; nome e codice sono rimasti.

---

### Senza utente in sessione non giudica

Se `app.current_user_id` manca, il trigger lascia passare: seed, migrazioni, job e manutenzioni non hanno un
utente, e il loro billing account non riceve il collegamento automatico. È la stessa condizione con cui tace
il collegamento.

---

### ⚠️ Che cosa oggi non copre

* **Un utente in sessione illeggibile vale come assente.** Un `app.current_user_id` che non è un numero non
  solleva: il trigger lo tratta come «nessun utente» e lascia passare.

---

### Codici errore

* `E_BA_ADMIN_GLOBALE_VIETATO` — chi crea non ha un'azienda di lavoro valida né un'appartenenza, ed esistono
  aziende attive.

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` — senza utente in sessione passa; il super admin
  senza azienda di lavoro, con aziende attive, è rifiutato.

---

### Note di migrazione

* 2026-04-08 — nasce col collegamento automatico all'azienda di chi crea: «chi non appartiene a un'azienda non
  crea billing account».
* 2026-08-04 — conta anche l'azienda di lavoro in sessione: il super admin dentro un'azienda crea.

---

{% include-markdown "signature-core.md" %}
