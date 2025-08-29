## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_child_fk_col()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)
>
> Approfondimento funzioni:
>
> * [dbops.fn_foreign_keys_info](/dbzero/dbops/funzioni/fn_foreign_keys_info)
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy)
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)

---

### 🎯 Scopo Principale

La funzione **`dbops.fn_get_child_fk_col(p_conoid oid)`** restituisce **il nome della colonna figlia** coinvolta in un **vincolo di chiave esterna** identificato dal suo **OID** (`pg_constraint.oid`). È pensata come **building-block** per automazioni di analisi/normalizzazione delle FK (naming, indici consigliati, audit), evitando join ripetitivi sui cataloghi `pg_constraint` e `pg_attribute`.

---

### 🔍 Parametri di input

| Parametro  |  Tipo | Obbligatorio | Descrizione                                                                  |
| ---------- | ----: | :----------: | ---------------------------------------------------------------------------- |
| `p_conoid` | `oid` |      ✔️      | OID del vincolo in `pg_constraint` (deve essere un vincolo **FOREIGN KEY**). |

> ℹ️ **Nota**: la funzione presuppone che `p_conoid` identifichi una FK valida. Se si passa l’OID di un vincolo non-FK, l’esito non è definito.

---

### 📤 Valore di ritorno

`text` – il **nome della colonna figlia** (attributo della tabella referenziante) corrispondente alla FK.

> ⚠️ **FK multi-colonna**: la funzione ritorna **solo la prima colonna** della chiave esterna (equivalente a `pg_constraint.conkey[1]`). Per FK composte, usare funzioni complementari (es. una variante che renda tutte le colonne) se necessario nelle automazioni.

---

### ⚙️ Flusso logico (semplificato)

1. Legge da `pg_constraint` il **relid** della tabella figlia (`conrelid`) e l’**indice della colonna** figlia (`conkey[1]`).
2. Risale a `pg_attribute` filtrando per `attrelid = conrelid` e `attnum = conkey[1]`.
3. Restituisce `attname` (nome della colonna figlia).

Questa logica incapsula il mapping OID→(tabella, colonna) evitando al chiamante di toccare direttamente i cataloghi.

---

### 🧩 Casi d’uso tipici

* **Naming policy**: derivare dinamicamente il nome della colonna figlia per proporre/rinominare l’identificatore del vincolo (`fk_<tabella_base>_<tabella_ref>`).
* **Indice consigliato**: individuare rapidamente la/e colonna/e figlia/e per verificare la presenza di un indice a supporto della FK (policy performance).
* **Audit/Report**: generare report tecnici sulle FK (per schema, tabella, qualità naming, indice mancante).

---

### 🛡️ Permessi e sicurezza

* La funzione legge i **cataloghi di sistema** (`pg_constraint`, `pg_attribute`); sono necessarie **privilegi di metadato** (in genere disponibili a ruoli tecnici / amministrativi).
* Non modifica dati né DDL: è **read-only**.

---

### 🚀 Esempi di utilizzo (concettuali)

* **Pipeline di enforcement naming**

  1. Elenco OID FK dallo schema target (vista utilitaria o `pg_constraint`).
  2. Per ogni OID, chiama `fn_get_child_fk_col(oid)` per ottenere la colonna figlia.
  3. Costruisci il **nome canonico** del vincolo e confrontalo con quello reale.
  4. Se difforme, prepara SQL di `ALTER TABLE … RENAME CONSTRAINT …` (o logga in `automation_rules_tbl`).

* **Verifica indice**

  1. Ottieni `child_col := fn_get_child_fk_col(oid)`.
  2. Controlla su `pg_index`/`pg_class` la presenza di un indice che inizi con `child_col`.
  3. In assenza, proponi `CREATE INDEX` secondo `fk_index_policy`.

---

### 📌 Considerazioni ed edge case

* **FK composte**: se la tua policy richiede di considerare **tutte** le colonne, integra questa funzione con una che ritorni l’intero array `conkey` mappato in nomi colonna.
* **Vincoli invalidi o parziali**: se l’OID non esiste o il vincolo è stato droppato durante la scansione, prevedere un controllo/gestione eccezioni nel chiamante.
* **Rinominhe di colonne**: se una colonna figlia viene rinominata, l’uso runtime della funzione restituirà il nuovo nome (coerente con i cataloghi).

---

### ✅ Benefici

* **Semplicità**: evita boilerplate SQL verso i cataloghi.
* **Componibilità**: si integra facilmente in funzioni/trigger di automazione.
* **Coerenza**: centralizza la logica di risoluzione OID→colonna figlia in un unico punto riusabile.

---

> 🧠 **In sintesi**: `fn_get_child_fk_col` è un mattone leggero ma strategico per tutte le automazioni che analizzano o normalizzano le **foreign key**: naming, indici, reportistica e audit diventano più semplici, consistenti e manutenibili.
