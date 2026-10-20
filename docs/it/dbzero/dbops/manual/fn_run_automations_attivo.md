## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_attivo`

---

### 👀 Vedi anche
>
>**Guide**
>
[Automazione DB](/guide/automazione-db)
>
**Approfondimento tabelle**
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)  
>
**Approfondimento funzioni e trigger**

> [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)   
> [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col)   
> [dbops.fn_get_child_fk_col](/dbzero/dbops/funzioni/fn_get_child_fk_col)   
> [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)   

---
### 🎯 Scopo Principale
*(latest review 13‑11‑2026)*
La funzione **`dbops.fn_run_automations_attivo(p_exec_mode, p_schemas, p_dry_run)`** applica in modo automatico e coerente le **regole di gestione del campo `attivo`** (soft‑delete / stato di validità) **sulle relazioni di chiave esterna**, creando e riconciliando **trigger di BLOCCO sul padre** e **trigger REQUIRE sul figlio**.

L’automazione opera **a livello di relazione FK**, non sulla singola tabella isolata, ed è progettata secondo un principio **conservativo e sicuro**:

> **Un record padre può essere disattivato (`attivo = false`) solo se NON esistono record figli attivi collegati tramite FK (o figli in generale se il figlio non ha `attivo`).**
> Inoltre, un record figlio puo' essere inserito/aggiornato **solo se il padre e' attivo**.

Non viene applicata alcuna cascata automatica.

---

### Ambito di applicazione

La funzione considera:

* Vincoli **FK (`pg_constraint.contype = 'f'`)** monocolonna con FK col `_id`
* Con **padre e figlio entrambi nell'ambito** degli schemi
* `storico` escluso (a livello di **ambito**, `fn_resolve_scope`)
* ⚠️ Il filtro `dbops.automation_fk_exclusions` **NON è più applicato** (disattivato in `20260113-01`, "non più utilizzato"; non ripristinato nel rewrite `20260408-06`). La tabella resta inerte. Vedi `brief-db-deprecabilita-catalogo-vs-istanze.md`.

> ⚠️ Se una tabella non partecipa ad alcuna FK eleggibile come **padre**, **nessuna automazione viene applicata**.

---

### Parametri di input

| Parametro     | Tipo      | Obbl. | Descrizione                                                                                                   |
| ------------- | --------- | :---: | ------------------------------------------------------------------------------------------------------------- |
| `p_exec_mode` | `text`    |   ✔️   | Modalità di esecuzione. La regola viene applicata se `rule.exec_mode = 'AUTO'` oppure uguale a `p_exec_mode`. |
| `p_schemas`   | `text[]`  |   ❌   | Schemi target. Se `NULL`, risolti tramite `dbops.fn_resolve_scope`.                                           |
| `p_dry_run`   | `boolean` |   ✔️   | Se `true`, non crea/droppa trigger ma registra solo audit di simulazione.                                     |

---

### Flusso logico

1. Risolve l'**ambito degli schemi** (`dbops.fn_resolve_scope`).
2. Recupera le **regole ATTIVO abilitate** da `automation_rules_tbl`.
3. Per ogni **FK compatibile**:

   * verifica che la **tabella padre** abbia la colonna `attivo` (con override opzionale);
   * determina la **colonna FK del figlio**;
   * calcola la **PK monocolonna del padre** (fallback `id`);
   * verifica l’esistenza del trigger di blocco secondo la strategia configurata.
4. Se necessario, **crea o riconcilia** il trigger di blocco sul padre e il trigger require sul figlio.

---

### Condizione fondamentale

> **La colonna `attivo` deve essere presente sul PADRE**.

Se il padre non ha la colonna `attivo`, la relazione FK viene **ignorata**.

Il caso **“solo il figlio ha `attivo`”** non è gestito ed è considerato **SKIP intenzionale**.

---

### Regole applicate

#### 🅱️ BLOCCO della disattivazione del padre

* **Trigger**: `BEFORE UPDATE OF attivo`
* **Tabella**: PADRE
* **Funzione**: `dbops.trgfn_prevent_deactivate_if_children(child_schema, child_table, fk_col [, pk_col])`

**Effetto**:

* se `OLD.attivo = true` e `NEW.attivo = false`;
* e **esistono record figli attivi collegati tramite FK** (o figli in generale se non c’è `attivo` sul figlio);

➡️ l’operazione viene **bloccata con errore**.

Nessuna modifica automatica viene applicata ai figli.

#### 🅱️ REQUIRE sul figlio (padre attivo)

* **Trigger**: `AFTER INSERT OR UPDATE OF <fk_col>[, attivo]` (constraint, DEFERRABLE)
* **Tabella**: FIGLIO
* **Funzione**: `dbops.trgfn_child_requires_active_parent(parent_schema, parent_table, attivo_parent_col, fk_col)`

**Effetto**:

* se il figlio ha `attivo`, il controllo si applica quando `attivo = true`;
* il padre referenziato deve risultare **attivo**.

➡️ l’operazione viene **bloccata con errore** se il padre non è attivo.

#### ⛔ Le eccezioni dichiarate (dal 2026-09-25)

Le FK scritte in [`dbops.automazione_attivo_eccezioni`](/dbzero/dbops/manual/automazione_attivo_eccezioni)
(schema e tabella della figlia, colonna FK, **motivo** obbligatorio) non si
legano: per loro non nasce né il block né il require (passo 2.0 del ciclo
delle FK; in dry run una riga di audit `ATTIVO_SKIP_ECCEZIONE`). E fuori dal
dry run, in testa a ogni giro, il motore chiama
[`dbops.fn_ritira_attivo_eccezioni`](/dbzero/dbops/manual/fn_ritira_attivo_eccezioni),
che toglie i trigger già generati per quelle coppie: chi genera ritira.
L'eccezione è **per FK**, non per tabella.

#### ⛔ Gli orfani (dal 2026-10-21)

Nello stesso punto il motore chiama
[`dbops.fn_ritira_attivo_orfani`](/dbzero/dbops/manual/fn_ritira_attivo_orfani),
che toglie i trigger ATTIVO che nominano una tabella o una colonna che non
esiste più. Il legame con la figlia è una stringa negli argomenti: un `DROP
TABLE … CASCADE` della figlia lasciava il block sul padre, e ogni
disattivazione del padre rispondeva `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`. Il
presidio è `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql`.

---

### Naming dei trigger

I nomi dei trigger sono generati tramite template JSON (`automation_rules_tbl.name_template`), utilizzando le chiavi `block` e `require`:

```json
{
  "block": "trg_{parent}_a10_{child}_block_deact_upd",
  "require": "trg_{child}_a10_{parent}_require_attivo_ins_upd"
}
```

Il nome finale è risolto tramite `dbops.fn_name_from_template`.

---

### Riconciliazione automatica

Se `params.reconcile_on_change = true` (default se assente, e **dichiarata
esplicitamente dal 2026-09-01**):

* eventuali trigger di blocco pre‑esistenti con stessi argomenti vengono **rimossi e ricreati**;
* si evita la duplicazione di trigger in caso di rename o migrazioni progressive.

> ⭐ **È l'unica chiave di `params` che questa funzione legge**, e fino al
> 2026-09-01 era l'unica **non dichiarata**: la riga `ATTIVO` ne portava cinque
> (`mode`, `cascade_children`, `include_no_action`, `require_active_parent`,
> `block_if_child_no_attivo`) che **nessuno leggeva**, e taceva su questa.
> ⇒ Ora `params` è `{"reconcile_on_change": true}`: dichiarato e letto
> coincidono. ⚠️ *Una chiave dichiarata e mai letta è una leva finta — prima o
> poi qualcuno la gira. Una letta e mai dichiarata non si scopre affatto.*

La riconciliazione **non** introduce cascade né altri comportamenti.

---

### Modalità DRY‑RUN

Con `p_dry_run = true`:

* Nessun DDL viene eseguito.
* Vengono registrati eventi `DRYRUN` tramite `dbops.fn_audit_log_once` per:

  * creazione pianificata del trigger;
  * skip intenzionali (es. padre senza `attivo`);
  * nessuna azione se il trigger esiste già.

Questo garantisce **osservabilità completa** del comportamento dell’automazione.

---

**Nota**: **l’automazione ATTIVO viene applicata solo alle FK con colonna che termina in `_id`**; in caso contrario la regola viene saltata per evitare riferimenti a codici testuali o chiavi non id.

---

### Permessi e sicurezza

* Richiede privilegi DDL sugli schemi target.
* In modalità `dry_run` è sufficiente il permesso di scrittura sull’audit.
* Gli operatori senza ownership **non possono aggirare** i trigger generati.

---

### Benefici

* **Sicurezza massima**: nessun soft‑delete distruttivo o implicito.
* **Semplicità**: una sola regola chiara e prevedibile.
* **Coerenza**: applicazione uniforme su tutte le FK rilevanti, indipendentemente dal tipo di `ON DELETE`.
* **Manutenibilità**: assenza di configurazioni complesse o ambigue.

---

> **In sintesi**: `fn_run_automations_attivo` implementa una politica ATTIVO conservativa:
> il padre si disattiva **solo quando è libero da dipendenze FK attive**, e il figlio può puntare al padre **solo se attivo**.
