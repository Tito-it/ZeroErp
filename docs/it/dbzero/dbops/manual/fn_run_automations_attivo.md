## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_attivo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `ATTIVO`: ambito, template dei nomi, strategia, parametri
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — le FK che il motore non lega
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — il nome della colonna attivo, quando non è `attivo`
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il block che monta sul padre
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il require che monta sul figlio
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — toglie i trigger delle FK diventate eccezione
> * [dbops.fn_ritira_attivo_orfani](/dbzero/dbops/funzioni/fn_ritira_attivo_orfani) — toglie i trigger che nominano oggetti spariti
> * [dbops.fn_trigger_exists_require_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_require_by_args) — il controllo di esistenza per argomenti del require
> * [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args) — il controllo di esistenza per argomenti del block
> * [dbops.fn_drop_triggers_by_function_args](/dbzero/dbops/funzioni/fn_drop_triggers_by_function_args) — la riconciliazione prima di creare
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — il nome del trigger dal template
> * [maintenance.proc_automations_attivo_job](/dbzero/maintenance/funzioni/proc_automations_attivo_job) — il wrapper del job che la fa girare
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO
> * [Linee guida trigger](/linee-guida-trigger#i-trigger-generati) — i trigger generati non si scrivono a mano

---

### 🎯 Scopo Principale

Il motore della regola ATTIVO: per ogni FK eleggibile nell'ambito monta sul **padre** un trigger
che impedisce di spegnerlo finché ha figli collegati (il *block*), e sul **figlio** un trigger che
impedisce a un figlio attivo di puntare a un padre spento (il *require*). Nessuna cascata: i figli
non si spengono da soli.

In testa a ogni giro, fuori dal dry run, toglie anche i trigger ATTIVO che non devono più esserci:
quelli delle FK dichiarate eccezione e quelli che nominano una tabella o una colonna sparita.

---

### Quali FK si legano

Il motore lavora per **relazione FK**, non per tabella. Una FK entra quando:

* è a **una sola colonna**: le funzioni trigger non gestiscono le FK composte;
* padre e figlio sono **entrambi nell'ambito** (`dbops.fn_resolve_scope`, che esclude `storico`) e
  la regola nomina lo schema o la tabella di uno dei due;
* il **padre ha la colonna attivo** (col nome di `automation_overrides_cols`, se c'è): senza, la FK
  si salta. Il caso «solo il figlio ha `attivo`» non è gestito, di proposito;
* non è dichiarata in `dbops.automazione_attivo_eccezioni`;
* la colonna FK finisce in `_id`: le FK su codici testuali non si legano.

Il tipo di azione della FK (`RESTRICT`, `NO ACTION`, `CASCADE`…) non conta: il motore non lo
guarda.

⭐ La colonna del padre passata ai trigger è quella **realmente referenziata** dalla FK, non la
chiave primaria: una FK può puntare a una colonna `UNIQUE` diversa dall'`id`.

---

### I due trigger

| | Block | Require |
| --- | --- | --- |
| Dove | padre | figlio |
| Quando | prima di un `UPDATE` della colonna attivo del padre | constraint trigger differito al commit, dopo un `INSERT` o un `UPDATE` della colonna FK (e della colonna attivo del figlio, se c'è) |
| Che cosa vieta | spegnere un padre con figli attivi, o con figli qualunque se la figlia non ha la colonna attivo | un figlio attivo sotto un padre spento |
| Argomenti | figlia, colonna FK, colonna referenziata, colonna attivo del padre | padre, colonna attivo del padre, colonna FK, colonna referenziata |

I nomi vengono dal template della regola (chiavi `block` e `require`), risolto da
`dbops.fn_name_from_template` con il nome del vincolo FK come base dell'hash: l'hash si aggiunge
solo quando il nome supererebbe i 63 caratteri.

⚠️ Due FK dalla stessa figlia allo stesso padre danno lo **stesso nome**, se è corto: il template
distingue padre e figlia, non la colonna. La seconda FK trova il nome già preso, risulta «già
presente» e resta senza trigger.

---

### Quando un trigger si considera già presente

La regola dichiara una strategia (`existence_strategy`): `BY_NAME` guarda il nome del trigger,
`BY_FUNCTION` guarda funzione e argomenti, `BOTH` si accontenta di uno dei due. Senza strategia
vale `BY_NAME`; la regola del seed dichiara `BOTH`.

⚠️ Il controllo per argomenti oggi non riconosce mai un trigger (vedi
`dbops.fn_trigger_exists_block_by_args`): con `BOTH` decide solo il nome, e con `BY_FUNCTION` ogni
giro toglierebbe e ricreerebbe il trigger.

Se il trigger manca, prima di crearlo il motore **riconcilia**: toglie i trigger della stessa
funzione con gli stessi argomenti, così un trigger rinominato non resta doppio. La riconciliazione
la governa la chiave `reconcile_on_change` dei parametri della regola, vera se manca; è l'**unica**
chiave dei parametri che il motore legge.

---

### Chi genera ritira

Fuori dal dry run, prima di guardare le FK, il motore chiama `dbops.fn_ritira_attivo_eccezioni` e
`dbops.fn_ritira_attivo_orfani`. Il primo toglie i trigger delle FK diventate eccezione dopo
essere state legate; il secondo quelli che nominano una tabella o una colonna che non esiste più,
come il block rimasto su un padre dopo l'eliminazione della figlia. I due ritiri guardano tutto il
database, non solo l'ambito del giro.

---

### Il dry run

Con `p_dry_run` vero il motore non tocca niente: niente ritiri, niente DDL. Scrive in audit, una
riga per caso, che cosa farebbe: i trigger che creerebbe, quelli già presenti, e i salti col loro
motivo (padre senza colonna attivo, FK eccezione, colonna FK senza `_id`).

---

### Codici errore

Un errore nella creazione di un trigger esce come `E_ATTIVO_REQUIRE` o `E_ATTIVO_BLOCK`, con il
contesto (padre, figlio, colonne, nome del trigger) nel registro errori. Un guasto dell'ambiente —
connessione, risorse, arresto, sistema, privilegio, lock, secondo `script.fn_sqlstate_di_ambiente` —
si scrive nel registro con lo stesso codice e poi si rilancia **con il suo SQLSTATE**, perché il
presidio dei job lo attribuisca all'esercizio e non allo sviluppo.

---

### Test

* `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — il motore chiama il ritiro degli orfani nel
  ramo fuori dal dry run.
* `db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql` — la FK dichiarata eccezione non ha
  trigger, e il motore continua a legare le altre FK della stessa figlia.

---

### Note di migrazione

* 2026-01-13 — il filtro su `automation_fk_exclusions` non si applica più; quella tabella è stata
  poi ritirata con le funzioni trigger legacy.
* 2026-09-01 — i parametri della regola `ATTIVO` diventano solo `reconcile_on_change`: prima ne
  dichiaravano cinque che nessuno leggeva, e tacevano l'unica letta.
* 2026-09-25 — le eccezioni dichiarate e il loro ritiro (`brief-db-blocco-login-per-credenziale`
  §12.3).
* 2026-10-16 — un guasto dell'ambiente si rilancia col suo SQLSTATE invece di diventare `P0001`
  (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-10-21 — il ritiro degli orfani in testa al giro (`brief-be-utenti-di-sviluppo` §9.5).

---

{% include-markdown "signature-core.md" %}
