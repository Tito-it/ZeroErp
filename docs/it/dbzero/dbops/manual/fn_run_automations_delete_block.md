## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_delete_block`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block) — il registro delle tabelle che non si cancellano
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: una riga del registro fuori ambito non si esegue
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove finisce ogni azione, nel giro vero e in simulazione
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger) — il passo che monta il trigger
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — la funzione del trigger montato
> * [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name) — il controllo di esistenza
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — che cosa è un guasto dell'ambiente
> * [maintenance.proc_automations_delete_block_job](/dbzero/maintenance/funzioni/proc_automations_delete_block_job) — il wrapper che la lancia
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni

---

### 🎯 Scopo Principale

Il runner `DELETE_BLOCK`: per ogni riga attiva di `dbops.automation_delete_block` nell'ambito,
monta sulla tabella il trigger che ne blocca la cancellazione salvo una GUC accesa, se non c'è già.
Oggi il registro protegge le tabelle dei ruoli anagrafici; lo lanciano il processo
`automations_delete_block` su pgAgent e la passata `ci_apply` della CI.

---

### Che cosa fa per ogni riga del registro

* La riga conta se è attiva, se il suo schema è fra quelli del giro — quelli passati o, se non ne
  passa nessuno, quelli dell'ambito — e se l'ambito ammette la tabella. ⚠️ Una riga fuori ambito non
  si esegue, senza traccia: è una questione dell'ambito, non del runner.
* Se la tabella non esiste, la riga si salta con una riga di audit `WARN` (`SKIP`,
  `TABLE_NOT_FOUND`), nel giro vero come in simulazione: è un salto, non un'azione.
* Il nome del trigger è quello della riga o, se manca o è vuoto, `trg_<tabella>_a10_delete_block_dlt`,
  lo stesso che calcola [fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger).
  Se un trigger con quel nome c'è già sulla tabella, non si fa niente e non si registra niente:
  l'esistenza si decide solo dal nome.
* Altrimenti, in simulazione si scrive una riga di audit `DRYRUN` con l'azione che si farebbe; nel
  giro vero si monta il trigger e si scrive una riga `OK` (`CREATE_TRIGGER`), con la tabella, il
  nome del trigger e la GUC che lo apre.

⭐ L'audit dice che cosa è successo, non solo che cosa succederebbe: ogni trigger montato e ogni
tabella sparita lasciano una riga anche nel giro vero.

La modalità di esecuzione entra solo nell'audit: il registro non ha regole per modalità.

---

### Un errore ferma il giro, ma con il suo nome

Se il montaggio fallisce, l'errore finisce prima nel registro errori con il codice
`E_DELETE_BLOCK` e il contesto (la tabella), poi il giro si ferma:

* un **guasto dell'ambiente** — connessione, risorse, arresto, sistema, privilegio, lock — si
  rilancia così com'è, con il suo SQLSTATE, perché il presidio dei job lo mandi a chi gestisce
  l'ambiente e non allo sviluppo;
* ogni altro errore, un difetto di struttura, esce come `E_DELETE_BLOCK`.

---

### Codici errore

* `E_DELETE_BLOCK` — il montaggio del trigger su una tabella è fallito per un difetto di struttura;
  con un guasto dell'ambiente il codice va solo nel registro errori, e l'errore esce col suo SQLSTATE.

---

### Test

* `db/pgtap/dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` — presidio sul testo: il
  gestore d'errore chiede al predicato dell'ambiente, scrive nel registro errori e rilancia
  l'originale, e altrimenti usa l'involucro con lo stesso contesto.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome con cui il wrapper si registra esiste
  fra i processi.

* `db/pgtap/dbops/test-delete-block-audit-v1.sql` — una tabella vera e una sparita: in simulazione
  `DRYRUN` per la prima e `WARN TABLE_NOT_FOUND` per la seconda, senza montare niente; nel giro vero
  il trigger c'è, con la sua riga `OK`, e la tabella sparita lascia il suo `WARN`; un secondo giro,
  col trigger già presente, non registra niente.

Il trigger montato lo incontrano anche le fixture anagrafiche (`db/pgtap/anagrafiche/create-cliente.sql`): non cancellano
più i soggetti di prova, e chiudono in `ROLLBACK` invece di aggirare il blocco con la GUC.

---

### Note di migrazione

* 2026-01-23 — nasce con il registro e con le righe dei ruoli anagrafici.
* 2026-10-16 — un guasto dell'ambiente si rilancia con il suo SQLSTATE dopo essere stato scritto
  nel registro errori; prima diventava `P0001` con il codice dell'involucro, e il presidio dei job
  lo mandava allo sviluppo (`brief-db-presidio-job-run-a-chi-tocca` D8, D11).
* 2026-11-04 — il giro vero scrive l'audit: `OK` per ogni trigger montato, `WARN TABLE_NOT_FOUND`
  per ogni tabella sparita, che in simulazione era `DRYRUN` (D41 di `brief-db-revisione-dbops`).
  Prima solo la simulazione lasciava traccia. Il nome del trigger tratta la stringa vuota come
  assente, come il passo che lo monta.

---

{% include-markdown "signature-core.md" %}
