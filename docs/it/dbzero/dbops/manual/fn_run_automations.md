## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations`

> 👀 **Vedi anche**
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db)
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id)
> * [dbops.fn_run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update)
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico)
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo)

---

### 🎯 Scopo Principale

(latest review 26-12-25)
La funzione **`dbops.fn_run_automations`** è l’**orchestratore principale** del framework di automazioni. Coordina l’applicazione delle regole di sistema (Tx ID, aggiornamento audit, storico, gestione flag attivo) sugli schemi e tabelle in scope.

---

### 🔍 Parametri di input

| Parametro     | Tipo    | Default                                     | Descrizione                                                                                       |
| ------------- | ------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `p_exec_mode` | text    | 'AUTO'                                      | Modalità di esecuzione (es. AUTO, FORCE, CHECK).                                                  |
| `p_schemas`   | text[]  | NULL                                        | Lista di schemi su cui operare. Se nullo, risolto tramite `automation_scope` o fallback.          |
| `p_dry_run`   | boolean | false                                       | Se true, non applica modifiche ma produce solo log/simulazione.                                   |
| `p_parts`     | text[]  | ['TX_ID','AUDIT_UPDATE','STORICO','ATTIVO'] | Moduli da eseguire. Supporta anche la keyword 'TABLE_RULES' per includere i tre moduli tabellari. |

---

### 📤 Valore di ritorno

`void` – non restituisce dati, ma applica automazioni e produce log.

---

### ⚙️ Flusso logico

1. Determina lo **scope degli schemi**: usa `p_schemas`, oppure `automation_scope`, oppure fallback a tutti gli schemi utente.
2. Valuta se abilitare la modalità compatibile `TABLE_RULES` → esegue i tre moduli tabellari (TX_ID, AUDIT_UPDATE, STORICO).
3. Esegue i moduli richiesti:

   * `fn_run_automations_tx_id`
   * `fn_run_automations_audit_update`
   * `fn_run_automations_storico`
   * `fn_run_automations_attivo`
4. Ogni modulo applica trigger/funzioni sulle tabelle target secondo le regole.

---

### 🧩 Casi d’uso tipici

* **Setup iniziale**: eseguire `fn_run_automations` dopo il deploy per applicare automaticamente regole su tutte le tabelle.
* **Verifica**: lanciare in modalità `p_dry_run = true` per controllare quali azioni verrebbero eseguite senza modificare nulla.
* **Manutenzione**: aggiornare trigger/policy su scope limitati (es. solo schema `anagrafiche`).

---

### 🛡️ Permessi e sicurezza

* Richiede privilegi DDL (creazione/alterazione trigger e funzioni) sugli schemi target.
* In modalità `dry_run` non modifica lo schema, quindi può essere usata anche in contesti più restrittivi per analisi.

---

### 🚀 Esempi di utilizzo

* `SELECT dbops.fn_run_automations();` → applica automazioni su tutti gli schemi.
* `SELECT dbops.fn_run_automations('AUTO', ARRAY['anagrafiche'], true, ARRAY['TX_ID']);` → simula l’esecuzione solo del modulo TX_ID sullo schema anagrafiche.

---

### 📌 Considerazioni

* La funzione rappresenta il **punto unico di ingresso** per tutte le automazioni.
* `p_parts` consente granularità: si possono eseguire solo i moduli interessati.
* La compatibilità con la keyword `TABLE_RULES` agevola la transizione da versioni precedenti.

---

### ✅ Benefici

* **Centralizzazione**: un solo punto di orchestrazione.
* **Flessibilità**: selezione modulare di cosa eseguire.
* **Robustezza**: fallback e `dry_run` garantiscono sicurezza nelle esecuzioni.

---

> 🧠 **In sintesi**: `fn_run_automations` è il cuore del sistema di automazione, che assicura l’applicazione coerente e modulare delle policy (Tx ID, audit, storico, attivo) su tutti gli schemi gestiti.
