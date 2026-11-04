## 📘 Documentazione Concettuale – Tabella `dbops.audit_log`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.error_log](/dbzero/dbops/tabelle/error_log) — il registro degli errori, l'altro registro append-only di `dbops`
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola di scadenza del registro
>
> Approfondimento viste:
>
> * [dbops.vw_audit_log_scrittori_fuori_perimetro](/dbzero/dbops/views/vw_audit_log_scrittori_fuori_perimetro) — il cancello su chi può scriverci
>
> Approfondimento funzioni:
>
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la riga intera in una volta: la porta dell'applicazione
> * [dbops.fn_audit_begin](/dbzero/dbops/funzioni/fn_audit_begin) — apre una riga `START`, riservata al proprietario
> * [dbops.fn_audit_end](/dbzero/dbops/funzioni/fn_audit_end) — la chiude con l'esito e la durata
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — il trigger che valorizza `tx_id`
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — il job che calcola la scadenza
>
> Guide:
>
> * [Audit Logging](/guide/messaggi-audit) — le funzioni di audit e chi può scrivere
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — quale registro risponde a quale domanda

---

### 🎯 Scopo Principale

Il **registro tecnico delle esecuzioni**: le corse delle automazioni del framework, degli
strumenti di amministrazione del database e delle loro simulazioni, con parametri, esito, durata
e riepilogo. Risponde alla domanda «quale funzione o automazione è stata eseguita, con quali
parametri, e com'è finita?».

⛔ Non è un registro di dominio: le funzioni che ci scrivono stanno in `dbops` e `maintenance`, e
un cancello lo tiene così (vedi sotto).

---

### Che cosa dice una riga

* `function_name` è la funzione o l'automazione che ha girato.
* `status` è l'esito, in un vocabolario chiuso dal vincolo `chk_audit_status`: `START` (una corsa
  aperta e non ancora chiusa), `OK`, `ERROR`, `WARN`, `DRYRUN` (una simulazione: che cosa la
  funzione avrebbe fatto).
* `executed_by` è il **ruolo di database** che ha scritto la riga, non l'operatore: chi ha chiesto
  il lavoro, se c'è, sta nel contesto della sessione e nel `tx_id`. ⚠️ Le righe scritte prima che
  il default diventasse il ruolo corrente portano la parola `CURRENT_USER`: si riconoscono e non si
  ricostruiscono.
* `params` porta l'ingresso o il contesto della corsa, `result` il suo riepilogo (trigger creati,
  conteggi, metriche), `message` una frase sull'esito.
* `exec_mode` è la modalità con cui il framework è stato lanciato (`AUTO`, `SCHEDULED`, `CI`…),
  `parts` i moduli eseguiti, `rule_type` il tipo di regola quando la riga riguarda una regola sola,
  `dry_run` dice se era una simulazione.
* `sqlstate`, `error_context` e `rows_affected` raccontano un errore o un conteggio, quando ci
  sono.
* `duration_ms` la calcola `fn_audit_end` alla chiusura di una corsa aperta con `fn_audit_begin`;
  chi scrive la riga intera la passa da sé, o la lascia vuota.

---

### `tx_id`: lo valorizza il trigger

La colonna non ha default: quando una riga arriva senza `tx_id`, il trigger generato
dall'automazione dei transaction id (`dbops.trgfn_tx_id_managed`) le assegna quello della
transazione. Così una corsa si incrocia con gli errori registrati nella stessa transazione in
`dbops.error_log`. La colonna ammette il vuoto: il registro non pretende la correlazione.

---

### ⛔ Append-only per l'applicazione

| Ruolo | Che cosa può fare | Perché |
| --- | --- | --- |
| `zeroerp_app` | leggere e aggiungere | Un registro modificabile da chi è registrato non è un registro: niente modifica, cancellazione, svuotamento |
| proprietario (migratore, job) | tutto | Scrive le automazioni, chiude le corse aperte con `fn_audit_end`, che è un aggiornamento, e cancella le righe scadute |
| ruoli batch | leggere | Il perimetro sta nel provisioning |

L'applicazione scrive solo con `fn_audit_log_once`; la coppia `fn_audit_begin` / `fn_audit_end`
le è negata, perché la chiusura è un aggiornamento della riga.

⚠️ La postura non è una revoca scritta una volta: i privilegi dell'applicazione si riconcedono in
blocco a ogni passata della convergenza del rilascio, e la postura più stretta è dichiarata dentro
quel ciclo e nel provisioning. Regola:
[Linee guida SQL — sezione 11](/linee-guida-sql#11-ciclo-di-vita-di-un-changeset-i-divieti),
punto 11.8.

---

### ⛔ Solo `dbops` e `maintenance` ci scrivono

Il registro non deve poter contenere dati di dominio. Invece di filtrarlo riga per riga, il
rischio si toglie alla fonte: la vista
[dbops.vw_audit_log_scrittori_fuori_perimetro](/dbzero/dbops/views/vw_audit_log_scrittori_fuori_perimetro)
elenca le funzioni fuori da quei due schemi che ci scrivono, direttamente o con le funzioni di
audit, e deve restare vuota.

---

### Scade dopo 90 giorni

Una riga resta **90 giorni** dall'esecuzione (`executed_at`), come gli errori di
`dbops.error_log`: i due registri si leggono insieme e scadono insieme. La scadenza la calcola il
job delle automazioni, non un trigger alla nascita, perché il registro può essere scritto anche da
una sessione fuori transazione che non legge le regole; poi il job di pulizia cancella le righe
scadute. `cleanup_at` è una data di pulizia, non una scadenza funzionale dell'evento.

---

### Test

* `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` — l'applicazione legge e aggiunge, non
  modifica né cancella né svuota; può eseguire `fn_audit_log_once` e non la coppia sessione; la
  riga scritta porta il ruolo che l'ha scritta.
* `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` — nessuna funzione fuori da `dbops` e
  `maintenance` scrive nel registro.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — il registro è nello scope delle
  automazioni, con la sua regola di scadenza e la sua colonna base, e senza trigger alla nascita.
* `db/pgtap/dbops/test-cleanup-framework.sql` — un rifiuto durante la pulizia lascia una riga
  `ERROR` con lo SQLSTATE.

---

### Note di migrazione

* 2025-08-22 — entrano le colonne di dettaglio (`exec_mode`, `parts`, `rule_type`, `dry_run`,
  `sqlstate`, `error_context`, `rows_affected`, `host`, `app_version`, `result`) e il vincolo sullo
  stato.
* 2026-01-11 — `tx_id` ammette il vuoto; lo valorizza il trigger.
* 2026-02-06 — entra `cleanup_at`.
* 2026-09-11 — il registro diventa append-only per l'applicazione, e il default di `executed_by`
  diventa il ruolo corrente: prima era la stringa `CURRENT_USER`.
* 2026-10-23 — entra nello scope delle automazioni con la regola di scadenza a 90 giorni: prima
  nessuna riga scadeva.

---

{% include-markdown "signature-core.md" %}
