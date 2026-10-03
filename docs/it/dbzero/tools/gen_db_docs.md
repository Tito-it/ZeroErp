## 📘 Documentazione – Script `gen_db_docs.py`

> 🔗 **Posizione consigliata**
>
> * `docs/it/dbzero/tools/gen_db_docs.md`

Lo script **`gen_db_docs.py`** automatizza la creazione di documentazione Markdown per il vostro database PostgreSQL, generando file per **tabelle** e **funzioni** all’interno delle cartelle `docs/it/dbzero/<schema>/tabelle` e `docs/it/dbzero/<schema>/funzioni`.
Permette inoltre di includere documentazione manuale preesistente, mantenendo un punto di dettaglio customizzabile in `.../manual`.

---

### 🎯 Obiettivo

1. **Esportare struttura e metadati**

   * Colonne, tipi, default, nullable
   * Vincoli (PK, FK, UNIQUE, CHECK)
   * Indici (btree, gist, ecc.)
   * Trigger associati alle tabelle
2. **Generare file di documentazione per le funzioni**

   * Firma SQL e definizione completa
3. **Mantenere integrazione manuale**

   * Se esistono file in `docs/it/dbzero/<schema>/manual`, li include all’inizio del documento
4. **Produrre un indice**

   * Crea `index.md` per ogni schema elencando tabelle, funzioni e documentazione manuale

---

### 🔍 Prerequisiti

* **Ambiente Python 3** con i pacchetti:

  ```bash
  pip install python-dotenv "psycopg[binary]"
  ```
* **File `.env`**:

  * `internal.env` (override) e `git.env` (fallback) contenenti le variabili di connessione
* **Variabili d’ambiente**:

  * `DATABASE_DSN` oppure `DB_HOST`, `DB_PORT`, `DB_NAME`, `POSTGRESQL_USER`, `POSTGRESQL_PWD`
  * `DB_DOC_SCHEMAS`: elenco separato da virgole degli schemi da documentare, es.:

    ```env
    DB_DOC_SCHEMAS=public,anagrafiche,config,script
    ```

---

### ⚙️ Modalità di Utilizzo

1. **Posizionarsi nella root del progetto** (il parent diretto di `gen_db_docs.py`).
2. **Eseguire lo script**:

   ```bash
   python3 tools/gen_db_docs.py
   ```
3. **Verificare l’output** in:

   ```
   docs/it/dbzero/<schema>/tabelle/*.md
   docs/it/dbzero/<schema>/funzioni/*.md
   ```
4. **Integrare documentazione manuale** aggiungendo file Markdown nella cartella:

   ```
   docs/it/dbzero/<schema>/manual/
   ```

   che verranno automaticamente inclusi con ` include-markdown `.

---

### 🔗 Struttura dello Script

* **Caricamento configurazione**

  * Utilizza `dotenv` per leggere `internal.env` e `git.env`.
  * Costruisce `DB_DSN` a partire da `DATABASE_DSN` o da variabili host/port/utente.
* **Directory di output**

  * `docs/it/dbzero` + `<schema>` + sottocartelle `tabelle`, `funzioni`, `manual`.
* **Generazione Markdown**

  * `gen_table_md()`: legge `information_schema` e `pg_*` per tabelle.
  * `gen_function_md()`: legge `pg_proc` per definizioni funzione.
  * Aggiunge icone:

    * 🗂️ Campi principali
    * 🔒 Vincoli
    * 📑 Indici
    * 🚨 Trigger
    * ⚙️ Funzione
* **Creazione indice**

  * `index.md` elenca file `.md` suddivisi in Tabelle, Funzioni e Documentazione Manuale.

---

### 💡 Vantaggi

* **Automazione**: riduce drasticamente il lavoro manuale di documentazione.
* **Consistenza**: garantisce stesse sezioni e formato uniforme.
* **Estendibilità**: aggiungi manualmente dettagli nei file `manual/` senza toccare lo script.
* **Manutenzione**: aggiorna la documentazione semplicemente rieseguendo lo script dopo modifiche DB.

---

> 🧠 **“Un unico script per trasformare il vostro schema PostgreSQL in una completa documentazione Markdown, integrabile con note manuali e sempre aggiornabile.”**
---


---
{% include-markdown "signature-core.md" %}
