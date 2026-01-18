## 📘 Documentazione Concettuale – View `dbops.vw_duplicate_indexes`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:   
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)   
> * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy)     

La view **`dbops.vw_duplicate_indexes`** identifica gli **indici duplicati** all’interno dello stesso schema e tabella, cioè quegli indici che coprono esattamente lo stesso insieme di colonne (`cols`). La view è **limitata agli schemi presenti in `dbops.automation_scope`**; per ciascun gruppo di colonne con più indici restituisce i nomi degli indici coinvolti e il numero totale di occorrenze.

---

### 🎯 Scopo Principale

(latest review 10-01-26)
* **Individuare indici ridondanti**
  Scoprire indici che hanno lo stesso set di colonne e possono quindi essere unificati o rimossi.
* **Ottimizzazione dello storage e delle performance**
  Ridurre overhead di manutenzione e migliorare le prestazioni di scrittura eliminando duplicazioni.
* **Governance della struttura**
  Supportare analisi periodiche per mantenere lo schema pulito e coerente.

---

### ⚙️ Flusso di Costruzione

1. **CTE `index_cols`**

   * Estrae da `pg_index` le informazioni sugli indici:

     * `index_oid`, `schema_name`, `table_name`, `index_name`
     * Flag `is_unique`, `is_primary`
     * Array `cols` con i nomi delle colonne indicizzate (ordinati).
   * Filtra fuori gli indici primari (`indisprimary`) e considera solo gli indici di tipo `i`.
2. **Aggregazione e raggruppamento**

   * Raggruppa per `schema_name`, `table_name` e `cols`.
   * Calcola:

     * `duplicate_index_names`: array dei nomi degli indici che condividono le colonne.
     * `count_of_indexes`: conteggio degli indici nel gruppo.
   * Applica `HAVING count(*) > 1` per ottenere solo i gruppi con più di un indice.


---

### 💡 Vantaggi Operativi

* **Riduzione di ridondanze**: facilita la rimozione di indici duplicati per liberare spazio e ridurre costi di manutenzione.
* **Chiarezza**: fornisce un elenco immediato dei gruppi di indici da esaminare.
* **Automazione**: utile in script di auditing o pulizia periodica.

---

> 🧠 **“Con `vw_duplicate_indexes`, tenere sotto controllo gli indici duplicati diventa semplice, supportando azioni di consolidamento per ottimizzare il database.”**
