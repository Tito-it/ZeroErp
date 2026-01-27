## 📘 Documentazione Concettuale – Tabella `config.sorgenti`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle/domìni collegati:
>
> * [config.note_tipologie](/dbzero/config/tabelle/note_tipologie)
> * [config.note_stili](/dbzero/config/tabelle/note_stili)
>
> Approfondimenti funzioni/trigger:
>
> * [config.trgfn_sorgenti_norm](/dbzero/config/funzioni/trgfn_sorgenti_norm)

---

La tabella **`config.sorgenti`** definisce il **dizionario centralizzato delle sorgenti applicative**.

È pensata per:

* identificare in modo **standard e normalizzato** la “sorgente” di un collegamento (es. *ATTIVITA*, *PREVENTIVO_RIGA*, *DDT_VENDITA*);
* supportare meccanismi di **idempotenza** e **validazione polimorfa** (tramite `target_table` e `key_selector`), cioè controlli che possono agire su tabelle diverse con la stessa logica;
* fungere da perno per collegare record di tabelle eterogenee a **note**, **log**, **attività**, **job**, ecc.

---

### 🎯 Scopo Principale

(latest update 24-01-2026)
* Fornire un **catalogo univoco** delle sorgenti applicative utilizzate in:

  * tabelle di collegamento (es. note collegate a entità diverse),
  * funzioni di validazione polimorfa su tabelle target,
  * sistemi di idempotenza/lock (es. registrazione eventi, attività, job).
* Normalizzare i riferimenti alle sorgenti per evitare codifiche testuali sparse e non controllate nel database.
* Permettere a trigger generici di **individuare automaticamente**:

  * quale tabella target leggere/validare (`target_table`),
  * quale chiave usare (`key_selector`: `id` o `uid`).

---

### 🔒 Vincoli e Regole Aziendali

* **Chiave primaria** (`id`):

  * identificatore tecnico `bigint` con identity.

* **Codici sorgente**:

  * `codice_interno`:

    * codice **funzionale interno**, univoco (`uq_sorgenti_codice_interno`),
    * non vuoto (`chk_sorgenti_codice_interno_non_vuoto`),
    * normalmente gestito in **UPPER** (come da commento),
    * dovrebbe essere considerato **immutabile** a livello di regole applicative.
  * `codice`:

    * codice esposto o operativo, anch’esso univoco (`uq_sorgenti_codice`),
    * usato da UI, integrazioni, configurazioni leggibili.

* **Categoria** (`categoria`):

  * classificazione opzionale ma consigliata della sorgente (es. `ANAGRAFICA`, `DOCUMENTO`, `PROCESSO`);
  * utilizzata per raggruppare e filtrare sorgenti in base al tipo di entità collegata;
  * **non modificabile** dopo la creazione (vedi trigger `trg_sorgenti_a10_upd_lock_columns`).

* **Descrizione** (`descrizione`):

  * testo leggibile che descrive in modo chiaro cosa rappresenta la sorgente (es. “Riga preventivo vendita”, “DDT di vendita”, “Attività di fatturazione”).

* **Stato di attivazione** (`attivo`):

  * indica se la sorgente è utilizzabile nelle nuove configurazioni;
  * le sorgenti utilizzate storicamente non dovrebbero essere cancellate, ma eventualmente rese non attive.

* **Metadati estensibili** (`meta`):

  * campo `jsonb` obbligatorio con default `{}`;
  * utilizzabile per:

    * parametri di comportamento specifici della sorgente,
    * indicazioni su tabelle correlate,
    * regole speciali per trigger o job;
  * la struttura del JSON deve seguire linee guida condivise per evitare incoerenze.

* **Target polimorfo** (`target_table`):

  * campo di tipo `regclass` che identifica la **tabella target** associata alla sorgente (schema + tabella);
  * utilizzato da trigger/funzioni polimorfe per:

    * verificare l’esistenza di una riga sorgente;
    * applicare controlli consistenti su entità diverse.

* **Selettore chiave** (`key_selector`):

  * indica quale tipo di chiave utilizzare per identificare la riga nella tabella target;
  * vincolato dal check `chk_sorgenti_key_selector_values` ai soli valori ammessi:

    * `id` → chiave intera/bigint,
    * `uid` → chiave UUID.
  * guida la logica dei trigger polimorfi su come costruire le query di validazione.

* **Audit**:

  * `data_insert`, `user_insert`, `data_update`, `user_update` tracciano le modifiche al catalogo sorgenti;
  * la gestione può essere uniformata in futuro tramite trigger generici di audit.

* **Tipo documento fiscale** (`tipo_doc_fiscale_id`):

  * opzionale, usato per sorgenti **RIGA** nella generazione di `attivita_fatturabili`;
  * se valorizzato, ha priorita` sul tipo documento di default della utility.

---

### 🔗 Relazioni

`config.sorgenti` è una tabella **di dominio/i18n logico** usata tipicamente da:

* **Tabelle di note collegate a entità diverse**:

  * una nota può salvare `sorgente_id` + chiave della riga (id/uid) cui si riferisce;
  * tramite `target_table` e `key_selector` è possibile verificare la coerenza del collegamento.

* **Tabelle di attività / job / log applicativo**:

  * per tracciare da quale sorgente logica (documento, processo, evento) nasce una certa attività o un certo log.

* **Meccanismi di idempotenza**:

  * utilizzando `codice_interno` e la chiave della riga sorgente, è possibile evitare esecuzioni duplicate di processi.

> 🔁 In generale, dove serve un **collegamento generico e riusabile** a “qualcosa nel sistema”, `config.sorgenti` diventa il punto di partenza per identificare *cosa* sia quel “qualcosa”.

---

### 💡 Vantaggi Operativi

* **Centralizzazione**: tutte le sorgenti logiche del sistema sono censite in un unico punto.
* **Riutilizzo**: le stesse definizioni di sorgente possono essere impiegate in note, log, attività, job, idempotenza, ecc.
* **Polimorfismo controllato**: grazie a `target_table` e `key_selector` è possibile scrivere **trigger e funzioni generiche** che lavorano su entità diverse senza perdere sicurezza.
* **Governance**: categorie, descrizioni e metadati permettono di documentare e governare l’uso delle sorgenti nel tempo.
* **Evolutività**: l’uso di `meta` consente di arricchire il comportamento associato alle sorgenti senza modificare la struttura fisica della tabella.

---

> 🧠 **“`config.sorgenti` è il dizionario centrale che dà un nome e una struttura alle ‘origini’ dei dati e dei processi in Zero ERP, abilitando controlli polimorfi e collegamenti robusti tra moduli diversi.”**
