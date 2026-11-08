## 📘 Documentazione Concettuale – Funzione `dbops.fn_regola_automazione_valida`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — il registro delle regole, il cui CHECK la chiama
>
> Approfondimento funzioni:
>
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — costruisce il nome del trigger dal template che qui si pretende
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il runner che ha bisogno dell'hash della FK nei due template
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il runner che legge i parametri delle regole di scadenza
> * [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — la regola `CLEANUP_AT` letta alla nascita della riga
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Dice se una regola di `dbops.automation_rules_tbl` è **ben formata**, a partire da tipo, modo di
esecuzione, template del nome e parametri. La legge il CHECK
`chk_automation_rules_tbl_regola_valida`: una regola malformata non entra nel registro, così i
runner non devono difendersi da lei e non convertono alla cieca un valore del tipo sbagliato.

È `IMMUTABLE`: guarda solo i quattro valori che riceve, non legge tabelle.

---

### Le regole che controlla

* **`params` è un oggetto JSON**, per ogni tipo di regola (vuoto, `{}`, quando il runner non legge
  parametri).
* **Il nome del trigger sta nel registro.** Le regole che montano un trigger — `TX_ID`,
  `AUDIT_UPDATE`, `STORICO`, `LOCK_COLUMNS`, `DATE_VALIDITA`, `CODICE_MAIUSCOLO` — hanno
  `name_template` non vuoto: i runner non hanno un nome di ripiego.
* **`ATTIVO` dichiara due template.** `name_template` è un oggetto JSON con le chiavi `block` e
  `require`, entrambe testo, e ognuna contiene un segnaposto dell'hash della FK (`{fkhash6}` o
  `{fkhash6_if_long}`): due FK della stessa coppia devono poter avere due nomi.
* **Le regole di scadenza valgono sempre.** `CLEANUP_AT` e `CLEANUP_PURGE` hanno `exec_mode`
  `AUTO`: la scadenza la scrive anche il trigger alla nascita della riga, che non è un giro e non
  ha un modo.
* **`CLEANUP_AT`**: `ttl_days` obbligatorio, intero ≥ 1; `apply_on_update`, se c'è, booleano.
* **`CLEANUP_PURGE`**: `batch_limit`, se c'è, intero ≥ 1.
* **Le colonne delle regole di scadenza** (`cleanup_column`, `base_ts_column`), se ci sono, sono
  testo.

Il vocabolario di `rule_type` e quello di `exec_mode` non stanno qui: li chiudono due CHECK a sé,
`chk_automation_rules_tbl_rule_type` e `chk_automation_rules_tbl_exec_mode`.

---

### Che cosa non controlla

* Non dice che le colonne nominate nei parametri esistano sulle tabelle: la regola può valere per
  `*all`, e la colonna la cerca il runner.
* Non controlla i segnaposto del template, salvo l'hash della FK nei due template di `ATTIVO`.
* Non guarda le chiavi dei parametri che nessun runner legge.

---

### Test

* `db/pgtap/dbops/test-registro-regole-vincoli-v1.sql` — il CHECK rifiuta un tipo sconosciuto, un
  modo non canonico, un `ttl_days` testuale o zero, una scadenza in un modo diverso da `AUTO`, un
  `batch_limit` non intero, un trigger senza nome, una regola `ATTIVO` senza `require` o senza
  l'hash della FK; una regola di scadenza ben formata entra.

---

### Note di migrazione

* 2026-11-08 — nasce (`20261109-66`), letta dal CHECK di `20261109-75` (brief-db-revisione-dbops
  D2, D17-bis, D20). Prima un `ttl_days` testuale fermava il giro di pulizia e ogni inserimento nei
  registri coperti, e una regola `STORICO` senza nome prendeva un ripiego diverso dal seed.

---

{% include-markdown "signature-core.md" %}
