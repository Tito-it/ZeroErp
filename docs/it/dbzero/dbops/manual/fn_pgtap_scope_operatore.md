## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_scope_operatore`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — la coda dove lo scope finisce
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta che lo accetta
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — il contesto da aprire prima
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — un'azienda col suo operatore

---

### 🎯 Scopo Principale

Helper di fixture pgTAP: lo **scope di un lavoro operatore** accodato da chi è in sessione. Contiene
l'utente del contesto (`app.current_user_id`), la sua identità `OPERATORE` e un'azienda del suo
perimetro, in `emittente_attivo_id` ed `emittente_ids`: quella passata come argomento, altrimenti la
prima. Per il super admin, che non ha un perimetro, la prima azienda.

È lo scope che `dbops.fn_accoda_lavoro` accetta da una sessione dell'applicazione: a nome di chi
accoda e dentro il suo perimetro. Uno scope scritto a mano con valori di fantasia
(`{"auth_user_id": 1}`) la porta lo respinge, e un lavoro operatore senza azienda non nasce.

⚠️ Solleva se in sessione non c'è nessuno, o se l'utente non ha aziende: prima si apre il contesto
con `script.fn_pgtap_set_contesto_operatore()`.

---

### Test

* `db/pgtap/dbops/test-fn-accoda-lavoro-porta-v1.sql`, `db/pgtap/dbops/test-coda-lavori.sql`,
  `db/pgtap/dbops/test-coda-accoda-classe.sql`, `db/pgtap/dbops/test-vw-coda-lavori-da-guardare.sql`
  — le fixture che lo usano.

---

### Note di migrazione

* 2026-11-07 — nasce col giro 5 di `brief-db-revisione-dbops` (`20261107-56`).

---

{% include-markdown "signature-core.md" %}
