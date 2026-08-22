## 📘 Documentazione Concettuale – Funzione `vendite.fn_start_lotto_task_run`
### 🎯 Scopo Principale
Apre un nuovo record runtime task su lotto in stato `IN_ESECUZIONE`.

---

### Regole principali

* `p_lotto_id` obbligatorio (`> 0`)
* `p_task_code` obbligatorio
* calcola `tentativo` incrementale per coppia `(lotto_id, stato_doc_fiscale_id, task_code)`
* salva snapshot di contesto (`pipeline_id`, `fase`, `meta`)
* ⭐ **dal 2026-08-22 scrive anche `correlation_id`**, cioè l'identità della
  *corsa* che ha prodotto il tentativo

---

### ⭐ Il filo della corsa (`p_correlation_id`)

È un identificativo che il runner genera **una volta per corsa** e scrive su
tutto ciò che quella corsa produce: gli eventi, i tentativi dei task e — sul
ramo push — la riga del giro. Serve a rispondere a una domanda che prima non
aveva risposta: *«queste righe appartengono alla stessa passata?»*.

⚠️ **Non è l'identificativo del lotto**, che nasce col lotto e non cambia mai:
due corse dello stesso lotto lo condividerebbero, e sulla domanda «in quale
passata» sarebbero indistinguibili.

⚠️ **E non è l'identificativo della transazione**: una corsa attraversa più
transazioni, una per passo. Le due cose rispondono a domande diverse e servono
entrambe.

⚠️ **È facoltativo, e se non arriva resta vuoto.** Non viene inventato: un filo
che non lega nessun'altra riga sembra un filo, ma non ricuce niente — mentre un
vuoto si può contare.

---

### Output

Una riga con:
* `task_run_id`
* `tentativo`

---

{% include-markdown "signature-core.md" %}
