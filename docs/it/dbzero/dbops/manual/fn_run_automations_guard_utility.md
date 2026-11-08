## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_guard_utility`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il registro delle tabelle da proteggere
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove finisce ogni azione, nel giro vero e in simulazione
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `automations_guard_utility` che la fa girare
>
> Approfondimento funzioni:
>
> * [dbops.fn_guard_utility_divergenze](/dbzero/dbops/funzioni/fn_guard_utility_divergenze) — il confronto fra atteso e vivo, che qui si esegue
> * [script.trgfn_guard_utility_tipo_ruolo_by_cols](/dbzero/script/funzioni/trgfn_guard_utility_tipo_ruolo_by_cols) — la funzione dei trigger che monta
> * [dbops.fn_apply_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_apply_automazione_guard_utility_tipo_ruolo) — la porta storica, che la chiama
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — che cosa è un guasto dell'ambiente
> * [maintenance.proc_automations_guard_utility_job](/dbzero/maintenance/funzioni/proc_automations_guard_utility_job) — il wrapper del processo
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Il runner del guard **utility → tipo ruolo**: porta i trigger su
`script.trgfn_guard_utility_tipo_ruolo_by_cols` delle tabelle dell'ambito allo stato che dichiara
`dbops.automazione_guard_utility_tipo_ruolo`.

⭐ **Converge, non si limita a creare**: un guard già montato si rigenera se il registro è
cambiato, e si toglie se la riga è spenta. Il confronto non lo fa questa funzione, ma
[fn_guard_utility_divergenze](/dbzero/dbops/funzioni/fn_guard_utility_divergenze): qui si esegue
l'azione di ogni tabella che diverge.

---

### Le azioni

* `CREA` — monta il trigger atteso: `BEFORE INSERT OR UPDATE OF` le due colonne della riga, per
  riga, con i loro nomi come argomenti.
* `RIGENERA` — toglie **tutti** i guard vivi della tabella, qualunque nome abbiano, e monta quello
  atteso.
* `TOGLIE` — toglie tutti i guard vivi (la riga è spenta).
* `COLONNA_MANCANTE` — una delle due colonne non esiste: scrive un `WARN` con il motivo
  `COLUMN_MISSING`, toglie un eventuale guard vivo e non monta niente.

Una tabella già allineata non si tocca: un secondo giro non ricrea niente.

---

### ⛔ Si ferma prima di cancellare un guard che il registro non conosce

Prima di qualunque DDL, e per tutte le tabelle insieme, la funzione guarda i guard vivi su
tabelle che il registro non nomina. Se ce n'è anche uno solo, solleva `E_GUARD_UTILITY` e li
nomina tutti in un solo errore: convergere li cancellerebbe in silenzio. Il rimedio è una riga nel
CSV del registro, spenta se il guard va tolto.

---

### Il dry run non tocca niente e non si ferma

Con `p_dry_run` vero la funzione non fa DDL e non si ferma sui guard sconosciuti: scrive in
`dbops.audit_log`, per ogni tabella che diverge, l'azione che farebbe (`DRYRUN_<azione>`), le
colonne e i trigger vivi. Una colonna mancante lascia anche lì la sua riga, con stato `DRYRUN`.

Nel giro vero ogni azione eseguita lascia una riga `OK`, e ogni colonna mancante una riga `WARN`.

---

### Un errore ferma tutto il giro

Un DDL che fallisce su una tabella solleva `E_GUARD_UTILITY`, con la tabella e l'azione nel
contesto, e annulla il giro intero. Un guasto dell'**ambiente** (connessione, risorse, privilegio,
lock) si scrive nel registro errori con lo stesso codice e poi si rilancia col suo SQLSTATE
originale, perché il presidio dei job lo mandi a chi gestisce l'ambiente e non allo sviluppo.

---

### Chi la chiama

* il processo `automations_guard_utility`, tramite
  [maintenance.proc_automations_guard_utility_job](/dbzero/maintenance/funzioni/proc_automations_guard_utility_job),
  in modo `SCHEDULED`: nella convergenza del rilascio (`ci_ordine` 75) e ogni sera alle 21:10 da
  pgAgent;
* la porta storica
  [fn_apply_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_apply_automazione_guard_utility_tipo_ruolo),
  che il primo giro di `ci_apply` chiama ancora, in modo `CI`.

Il modo filtra le righe come negli altri runner: una riga `AUTO` vale per tutti, le altre solo per
il loro modo.

---

### Codici errore

* `E_GUARD_UTILITY` — uno o più guard su tabelle che il registro non nomina (prima di ogni DDL),
  oppure un DDL fallito su una tabella.

Il codice del dominio, `E_UTILITY_RUOLO_NON_AMMESSO`, lo solleva il guard montato sulle scritture
delle tabelle protette, non questa funzione.

---

### Test

* `db/pgtap/dbops/test-guard-utility-convergenza-v1.sql` — una riga con la colonna
  `soggetto_ruolo_id` monta il guard nella forma attesa; una colonna inesistente lascia
  `WARN COLUMN_MISSING` e nessun trigger; un `trigger_name` cambiato lascia solo il nuovo; una riga
  spenta toglie il guard; un guard su una tabella senza riga ferma il runner con `E_GUARD_UTILITY`
  senza cancellarlo; il dry run non fa DDL; la porta storica fa lo stesso lavoro; il processo è
  nella catena fra `automations_delete_block` e `automations_overlap`.

---

### Note di migrazione

* 2026-11-08 — nasce (`20261110-01`, `brief-db-revisione-dbops`, giro 10c). Prima la famiglia non
  aveva un runner: il guard lo montava
  `fn_apply_automazione_guard_utility_tipo_ruolo`, solo nel primo giro di `ci_apply`, senza audit,
  senza togliere i guard delle righe spente e scartando la colonna senza prefisso.

---

{% include-markdown "signature-core.md" %}
