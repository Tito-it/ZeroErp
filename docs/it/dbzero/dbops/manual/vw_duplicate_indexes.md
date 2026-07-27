## 📘 Documentazione Concettuale – View `dbops.vw_duplicate_indexes`

> 👀 **Vedi anche**
>
Approfondimento funzioni:  
>
[dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso)  
> [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice)  
> [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy)  

La view **`dbops.vw_duplicate_indexes`** identifica gli **indici duplicati esatti** all'interno dello stesso schema e tabella: quelli che, a parità di tutto ciò che conta, sono **intercambiabili**. È **limitata agli schemi presenti in `dbops.automation_scope`**.

Per ciascun gruppo restituisce i nomi degli indici coinvolti, quale tenere e quali eliminare.

---
### 🎯 Scopo Principale
(latest review 27-07-26)

* **Individuare indici realmente ridondanti**
  Scoprire indici intercambiabili, di cui tutti tranne uno possono essere rimossi.
* **Ottimizzazione dello storage e delle performance**
  Ridurre overhead di manutenzione e migliorare le prestazioni di scrittura: ogni indice in più costa una scrittura a ogni `INSERT`, `UPDATE` e `DELETE`.
* **Governance della struttura**
  Supportare analisi periodiche per mantenere lo schema pulito e coerente.

---

### 🔑 La firma normalizzata

Il raggruppamento avviene per **firma**: la definizione dell'indice (`pg_get_indexdef`) privata di

* il **nome**,
* la clausola `WITH (...)` dei parametri di storage,
* la clausola `TABLESPACE`.

Resta tutto ciò che determina **quali query l'indice sa servire**: metodo di accesso, colonne ed espressioni, classe di operatori, collation, `ASC`/`DESC`, `NULLS FIRST`/`LAST`, `NULLS NOT DISTINCT`, `INCLUDE`, predicato. Due indici con la stessa firma sono equivalenti per definizione.

#### Il flag UNIQUE è fuori dalla chiave di raggruppamento

Deliberatamente. Un btree non-unique identico a un `UNIQUE` ha una firma che differisce solo per quel flag, ma è ridondante al 100%: la UNIQUE serve le stesse query **e in più** impone un vincolo. Metterlo nella chiave lo avrebbe reso invisibile.

Il flag è usato invece per **ordinare** il gruppo, così `indice_da_tenere` è sempre la UNIQUE quando c'è.

---

### ⚠️ Cosa NON è un duplicato

Fino al 27-07-2026 la view raggruppava per il solo array di colonne, e segnalava **19 gruppi di cui 16 falsi positivi**. Ecco i tre modi in cui sbagliava, oggi tutti risolti:

| Caso | Perché non sono duplicati |
| --- | --- |
| GIN `trgm` e btree sulla stessa colonna | servono query diverse: `ILIKE '%x%'` contro uguaglianza e ordinamento |
| Due UNIQUE parziali disgiunte | `WHERE stato='BOZZA'` e `WHERE stato='PUBBLICATA'` convivono legittimamente |
| Un indice con colonne-espressione | il join su `pg_attribute` scartava gli `attnum = 0`, e un indice a 5 colonne di cui 4 `COALESCE(...)` veniva letto come indice a **una** colonna |

---

### ⛔ Cosa questa view non può vedere

La **ridondanza per prefisso**: un indice su `(a)` reso inutile da uno su `(a, b)`. Non è un duplicato — le colonne differiscono — quindi nessun affinamento di questa view potrà mai catturarlo.

Serve la view sorella [vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso). **Le due si usano insieme.**

---

### Colonne e Descrizione

| Colonna | Descrizione |
| --- | --- |
| `schema_name`, `table_name` | Dove si trova il gruppo |
| `index_columns` | Colonne chiave, espressioni comprese |
| `metodo` | Metodo di accesso (`btree`, `gin`, `gist`, …) |
| `predicato` | Predicato `WHERE` dell'indice parziale, `NULL` se totale |
| `duplicate_index_names` | Nomi degli indici del gruppo, UNIQUE per primo |
| `count_of_indexes` | Quanti indici nel gruppo |
| `indice_da_tenere` | Quello da conservare |
| `indici_da_droppare` | Tutti gli altri |

---

### Esempi di Utilizzo

```sql
-- cosa tenere e cosa togliere, già pronto
SELECT schema_name, table_name, indice_da_tenere, indici_da_droppare
FROM dbops.vw_duplicate_indexes;
```

> ⚠️ Prima di droppare, verificare in [vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) se l'indice è governato dall'automazione FK (`origine = 'AUTOMAZIONE_FK'`): in quel caso un `DROP` secco verrebbe annullato al primo `migrate` successivo, e serve prima portare a `false` il flag `consentito` in `dbops.fk_index_policy`.

---

### Vantaggi Operativi

* **Riduzione di ridondanze**: individua indici davvero eliminabili, senza falsi allarmi.
* **Chiarezza**: `indice_da_tenere` e `indici_da_droppare` dicono l'azione, non solo il problema.
* **Automazione**: utile in script di auditing o pulizia periodica.

---

> **“Con `vw_duplicate_indexes`, tenere sotto controllo gli indici duplicati diventa semplice, supportando azioni di consolidamento per ottimizzare il database.”**
