## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_date_validita`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `DATE_VALIDITA`: template del nome, strategia d'esistenza, contesto
> * [dbops.error_log](/dbzero/dbops/tabelle/error_log) — dove resta il fallimento del montaggio
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — il guard che monta: `valido_al` non precede `valido_dal`
> * [maintenance.proc_automations_lock_columns_job](/dbzero/maintenance/funzioni/proc_automations_lock_columns_job) — il giro a orario che la chiama
> * [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name) — il riconoscimento per nome
> * [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function) — il riconoscimento per funzione
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — che cosa è un guasto dell'ambiente
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione DATE_VALIDITA fra le altre
> * [Linee guida Trigger](/linee-guida-trigger#i-trigger-generati) — le regole dei trigger generati

---

### 🎯 Scopo Principale

Monta il guard della regola del periodo, `script.trgfn_guard_date_validita`, su ogni tabella
dell'ambito che ha le colonne `valido_dal` e `valido_al`: un trigger `BEFORE INSERT OR UPDATE OF`
delle due date, che rifiuta una fine che precede l'inizio con un errore che l'operatore capisce.

La chiamano la convergenza di ogni migrate e il giro a orario `automations_lock_columns`.

---

### ⭐ La regola è della coppia di colonne, non della tabella

Non c'è un registro per tabella: basta la presenza delle due colonne, e una tabella nuova nasce
presidiata al primo migrate. È la stessa forma del lucchetto su `codice_interno`. Restano fuori lo
schema `storico` — le tabelle ombra ricordano, non si giudicano — e le tabelle escluse
dall'ambito.

Serve comunque una regola `DATE_VALIDITA` accesa in `dbops.automation_rules_tbl` che copra lo
schema e la tabella, per il contesto della chiamata: da lì vengono il template del nome e la
strategia con cui si riconosce un trigger già montato. Senza regola la tabella non si tocca. Fra
più regole che la coprono vale la prima per priorità, e basta quella.

⚠️ Su ogni migrate la convergenza, dopo il giro, controlla che ogni tabella con la coppia di date
abbia il guard, e ferma il migrate elencando quelle che ne sono senza: una regola spenta o tolta
dal CSV non lascia tabelle scoperte in silenzio.

---

### Idempotente: un guard già montato si riconosce

La strategia d'esistenza della regola dice come: per nome, per funzione, o con entrambi
(`BOTH`, il default) — e allora basta una delle due. Con `BOTH` un nome troncato oltre i 63
caratteri si riconosce comunque dalla funzione. A regime il giro non fa DDL.

Con `p_dry_run` vero non crea niente e scrive in `dbops.audit_log` una riga per ogni tabella su cui
monterebbe il guard. Il montaggio vero non lascia una riga d'audit. ⚠️ La riga della simulazione è
firmata `dbops.fn_run_automations`, non col nome di questa funzione: un nome che non esiste più,
perché l'orchestratore è stato ritirato. È un difetto aperto.

---

### ⛔ Il fallimento del montaggio ferma il giro

Un errore nel creare il trigger si scrive nel registro errori con il codice `E_DATE_VALIDITA` e la
tabella, e poi esce. Due casi:

* un **difetto di struttura** o di permessi di chi migra esce come errore di dominio
  `E_DATE_VALIDITA`;
* un **guasto dell'ambiente** (connessione, risorse, arresto, sistema, privilegio, lock, secondo
  `script.fn_sqlstate_di_ambiente`) si scrive nel registro con lo stesso codice e si rilancia con
  il **suo** SQLSTATE: così il presidio dei job lo manda a chi gestisce l'ambiente, non allo
  sviluppo.

---

### Codici errore

* `E_DATE_VALIDITA` — il guard non si è potuto montare su una tabella. Nessun operatore lo
  provoca: è un difetto di struttura o di permessi di chi migra. Con un guasto dell'ambiente il
  codice resta nel registro errori, ma l'errore esce con lo SQLSTATE originale.

---

### Test

* `db/pgtap/script/test-trgfn-guard-date-validita-v1.sql` — nessuna tabella con la coppia di date è
  senza il guard (la lista si legge dalla struttura) e nessuna ne ha due; ogni guard è `BEFORE ROW`
  su `INSERT` e `UPDATE OF` delle due date; nessuna tabella dello storico lo porta; sulle tre forme
  in cui la regola parlava prima (intervallo generato, CHECK, entrambi) parla ora il guard, prima
  del calcolo dell'intervallo.

---

### Note di migrazione

* 2026-09-23 — nasce, insieme al guard, alla parte `DATE_VALIDITA` dell'orchestratore e alla
  convergenza a ogni migrate. Prima la regola del periodo parlava in tre modi diversi secondo la
  tabella, o non parlava (`brief-db-guard-date-validita`).
* 2026-10-16 — un guasto dell'ambiente esce con il suo SQLSTATE; prima diventava un errore di
  dominio, e il presidio dei job lo mandava allo sviluppo (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-11-04 — ritirato l'orchestratore `dbops.fn_run_automations`, di cui era la parte
  `DATE_VALIDITA`; la firma della simulazione ne porta ancora il nome (`brief-db-revisione-dbops`).

---

{% include-markdown "signature-core.md" %}
