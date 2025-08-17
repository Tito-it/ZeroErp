## 📘 Documentazione Concettuale – Tabella `config.stati_cliente`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
>
> Approfondimento funzioni e view:
>
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)
> * [script.view_clienti_istanza_states](/dbzero/script/view/view_clienti_istanza_states)

---

### 🎯 Scopo Principale

La tabella `config.stati_cliente` definisce i possibili **stati funzionali** di un cliente all’interno di Zero ERP, utilizzati sia per il controllo dei processi (letture, fatturazione) sia per la logica di avanzamento (precontrattuale, attivo, sospeso, chiuso, ecc.).

---

### 🔗 Collegamenti con Altre Tabelle

| Campo                   | Riferimento                            | Azione                                        |
| ----------------------- | -------------------------------------- | --------------------------------------------- |
| `id`                    | PK                                     | Identificatore unico dello stato cliente      |
| Utilizzo in client view | `view_clienti_istanza_states.stato_id` | Join per descrizione stato di istanza/cliente |

---

### 🚩 Regole di Validazione Condizionale

* **Codice Non Modificabile**: `codice_interno` è unico (`uq_stati_cli_cod_unq`) e bloccato da trigger su update.
* **Flag Booleani**: `check_lettura`, `abilita_fattura` accettano solo `S` o `N`.
* **Tipologia Stato**:

  * `codice` accetta solo valori `AT`, `IS`, `CH`, `AN`, `SM`, `CE`, `LE`.
  * `stato_cliente_ia` ammette solo `A` (Altro) o `I` (Istanza).

---

### 🔍 Indicizzazione

* **`ix_config_stati_cli_desc`**: supporta ricerche per descrizione estesa (`descrizione`).

---

### 💡 Vantaggi Operativi

* **Centralizzazione**: tutti i processi leggono gli stati da un unico catalogo configurabile.
* **Multifunzionalità**: gli stessi stati guidano logica di letture, abilitazione fatture, transizioni contrattuali.
* **Blocchi di coerenza**: codici fissi e check riducono errori di configurazione.

---

### ⚙️ Trigger e Automatismi

| Trigger                                    | Evento        | Funzione                                                                        |
| ------------------------------------------ | ------------- | ------------------------------------------------------------------------------- |
| `trg_stati_cliente_upd_lock_codiceinterno` | BEFORE UPDATE | `script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| `trg_upd_stati_cliente_audit_data_user`    | BEFORE UPDATE | `script.trgfn_upd_audit_data_user_generic()`                                    |

---

### ✅ Controlli di Coerenza

* `codice_interno` è **unico** e non può essere modificato.
* I check sui caratteri `S/N` e sui valori di stato evitano inserimenti fuori standard.
* Tutte le colonne di audit (`data_insert`, `user_insert`, `data_update`, `user_update`) vengono automaticamente popolate e aggiornate.

---

### 🧾 Note Finali

I codici interni `codice_interno` permettono l’internazionalizzazione e i test automatici, mentre i flag `check_lettura` e `abilita_fattura` abilitano o meno le funzionalità di lettura consumi e fatturazione per ciascuno stato. Questa tabella è fondamentale per governare l’intero workflow cliente.
