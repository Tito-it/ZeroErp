## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_delete_block`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block) — il registro delle tabelle che non si cancellano
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: una tabella fuori ambito non si confronta
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove finisce ogni azione, nel giro vero e in simulazione
>
> Approfondimento funzioni:
>
> * [dbops.fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze) — il confronto fra atteso e vivo, che qui si esegue
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger) — il passo che monta il trigger
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — la funzione del trigger montato
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — che cosa è un guasto dell'ambiente
> * [maintenance.proc_automations_delete_block_job](/dbzero/maintenance/funzioni/proc_automations_delete_block_job) — il wrapper che la lancia
>
> Guide:
>
> * [Automazione DB, §4.4](/guide/automazione-db#44-delete_block-blocco-delete-con-guc) — la regola DELETE_BLOCK

---

### 🎯 Scopo Principale

Il runner `DELETE_BLOCK`: porta i blocchi di cancellazione (i trigger su
`script.trgfn_delete_block_by_guc`) delle tabelle dell'ambito allo stato che dichiara
`dbops.automation_delete_block`. Oggi il registro protegge le tabelle dei ruoli anagrafici; lo
lanciano il processo `automations_delete_block` su pgAgent e la convergenza del rilascio.

⭐ **Converge, non si limita a creare**: il confronto lo fa
[fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze), qui si esegue
l'azione di ogni tabella che diverge. Ha la stessa forma del runner dei lock di colonna.

---

### Le azioni

* `CREA` — monta il trigger atteso, `BEFORE DELETE` per riga, con
  [fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger).
* `RIGENERA` — toglie **tutti** i blocchi vivi della tabella, qualunque nome abbiano, e monta
  quello atteso. Un nome, un momento, una `guc_key` diversi, o un trigger disabilitato, si
  riallineano così.
* `TOGLIE` — toglie tutti i blocchi vivi: la riga è spenta.

Una tabella già allineata non si tocca: un secondo giro non ricrea niente. Al primo giro dopo
l'aggiornamento del 2026-11-08 i blocchi esistenti, nati `AFTER DELETE`, si rigenerano `BEFORE`.

Una riga accesa che punta a una tabella che non esiste lascia un `WARN TABLE_NOT_FOUND`, nel giro
vero come in simulazione: è un salto, non un'azione.

---

### ⛔ Si ferma prima di cancellare un blocco che il registro non conosce

Prima di qualunque DDL, e per tutte le tabelle insieme, la funzione guarda i blocchi vivi su
tabelle che il registro non nomina. Se ce n'è anche uno solo, solleva `E_DELETE_BLOCK` e li nomina
tutti in un solo errore: convergere li cancellerebbe in silenzio. Il rimedio è una riga nel
registro: accesa se il blocco va tenuto, spenta se va tolto.

---

### Il dry run non tocca niente e non si ferma

Con `p_dry_run` vero la funzione non fa DDL e non si ferma sui blocchi sconosciuti: scrive in
`dbops.audit_log`, per ogni tabella che diverge, l'azione che farebbe (`DRYRUN_<azione>`), con la
tabella, il nome e la GUC attesi e i trigger vivi.

Nel giro vero ogni azione eseguita lascia una riga `OK`, con l'azione (`CREA`, `RIGENERA`,
`TOGLIE`) negli stessi campi.

La modalità di esecuzione entra solo nell'audit: il registro non ha regole per modalità.

---

### Un errore ferma il giro, ma con il suo nome

Se un DDL fallisce su una tabella, l'errore finisce prima nel registro errori con il codice
`E_DELETE_BLOCK` e il contesto (la tabella e l'azione), poi il giro si ferma:

* un **guasto dell'ambiente** — connessione, risorse, arresto, sistema, privilegio, lock — si
  rilancia così com'è, con il suo SQLSTATE, perché il presidio dei job lo mandi a chi gestisce
  l'ambiente e non allo sviluppo;
* ogni altro errore, un difetto di struttura, esce come `E_DELETE_BLOCK`.

---

### Codici errore

* `E_DELETE_BLOCK` — uno o più blocchi su tabelle che il registro non nomina (prima di ogni DDL),
  oppure un DDL fallito su una tabella; con un guasto dell'ambiente il codice va solo nel registro
  errori, e l'errore esce col suo SQLSTATE.

---

### Test

* `db/pgtap/dbops/test-delete-block-convergenza-v1.sql` — su tutto l'ambito nessun blocco diverge;
  un blocco `AFTER` scritto a mano si rigenera `BEFORE`, e il padre con un figlio in cascata è
  rifiutato con il figlio intatto; una `guc_key` o un `trigger_name` cambiati arrivano sul
  trigger; una tabella dal nome lungo non diverge dopo due giri; una riga spenta toglie il blocco;
  un blocco su una tabella senza riga ferma il runner con `E_DELETE_BLOCK` senza toccarlo; il dry
  run non fa DDL.
* `db/pgtap/dbops/test-delete-block-audit-v1.sql` — una tabella vera e una sparita: in simulazione
  `DRYRUN` per la prima e `WARN TABLE_NOT_FOUND` per la seconda, senza montare niente; nel giro vero
  il trigger c'è, con la sua riga `OK` `CREA`, e la tabella sparita lascia il suo `WARN`; un secondo
  giro non registra niente.
* `db/pgtap/dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` — presidio sul testo: il
  gestore d'errore chiede al predicato dell'ambiente, scrive nel registro errori e rilancia
  l'originale, e altrimenti usa l'involucro con lo stesso contesto.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome con cui il wrapper si registra esiste
  fra i processi.

Il trigger montato lo incontrano anche le fixture anagrafiche (`db/pgtap/anagrafiche/create-cliente.sql`): non cancellano
più i soggetti di prova, e chiudono in `ROLLBACK` invece di aggirare il blocco con la GUC.

---

### Note di migrazione

* 2026-01-23 — nasce con il registro e con le righe dei ruoli anagrafici.
* 2026-10-16 — un guasto dell'ambiente si rilancia con il suo SQLSTATE dopo essere stato scritto
  nel registro errori; prima diventava `P0001` con il codice dell'involucro, e il presidio dei job
  lo mandava allo sviluppo (`brief-db-presidio-job-run-a-chi-tocca` D8, D11).
* 2026-11-04 — il giro vero scrive l'audit: `OK` per ogni trigger montato, `WARN TABLE_NOT_FOUND`
  per ogni tabella sparita (D41 di `brief-db-revisione-dbops`).
* 2026-11-08 — converge col registro attraverso `fn_delete_block_divergenze`: crea, rigenera,
  toglie, e si ferma su un blocco che il registro non nomina (`20261109-98`,
  `brief-db-revisione-dbops`, giro 10c). Prima riconosceva il trigger solo per nome
  (`dbops.fn_trigger_exists_by_name`) e lo creava dove mancava: una riga spenta lasciava il
  blocco, un `trigger_name` cambiato ne montava un secondo. L'azione in audit era
  `CREATE_TRIGGER` (`DRYRUN_CREATE_TRIGGER` in simulazione); ora è `CREA`, `RIGENERA` o `TOGLIE`.

---

{% include-markdown "signature-core.md" %}
