## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_codice_errore`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_codice_dominio](/dbzero/script/funzioni/fn_codice_dominio) — la lettura del codice di dominio, che questa riusa
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — chi solleva un errore di dominio, e dove mette il codice
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — «Un errore si asserisce, non si spera»

---

### 🎯 Scopo Principale

Esegue un'istruzione dentro un pgTAP e dice **che cosa l'ha rifiutata**, per asserirlo con
`is()`. Sostituisce le copie locali (`pg_temp.codice_errore` e simili) che i test si scrivevano da
soli, in sei varianti che allo stesso rifiuto rispondevano in modi diversi.

---

### ⭐ Che cosa risponde

In quest'ordine:

1. `NULL`, se l'istruzione passa. Le sue scritture restano nella transazione del test;
2. il **codice di dominio**, se l'errore viene da `script.fn_log_and_raise_error` (letto da
   `script.fn_codice_dominio`);
3. il **nome del vincolo**, per un CHECK, una UNIQUE o una FK violati;
4. lo **SQLSTATE**, per ogni altro errore.

Un errore inatteso non interrompe il file: torna come valore, e l'`is()` del test mostra che cosa
è successo invece del codice atteso. Il test resta rosso. Le scritture di un'istruzione rifiutata
si annullano.

Un test che vuole provare che un'istruzione **passa** asserisce `NULL`. Un test che vuole il
messaggio, la colonna o lo SQLSTATE insieme al codice non usa questa funzione: quelle sono letture
diverse.

---

### Codici errore

Non ne solleva: ogni errore dell'istruzione diventa il valore restituito. Non scrive niente di
suo.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-codice-errore-v1.sql` — le quattro risposte, costruite su una
  tabella temporanea; la scrittura che passa resta, quella rifiutata no.

---

### Note di migrazione

* 2026-11-12 — nasce (`20261112-28`), per ritirare le copie locali della stessa lettura nei pgTAP.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
