# 📗 Guida Tecnica – Gestione dei Messaggi di Errore e Generazione Log in Zero ERP

> 📋 **Destinatari:** sviluppatori database, backend e devops

---

## 📌 Introduzione

Zero ERP adotta un modello unificato per la **centralizzazione**, il **logging** e la **gestione** dei messaggi di errore, basato su:

* **Tabella messaggi**: [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) – definisce template, cause e suggerimenti per ogni codice di errore.
* **Tabella log**: [dbops.error_log](/dbzero/dbops/tabelle/error_log) – archivia ogni occorrenza di errore con contesto e transazione.
* **Funzioni PL/pgSQL**:

  * [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio) per recuperare e formattare il testo del messaggio con internazionalizzazione e placeholder.
  * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) per eseguire il logging remoto e sollevare l’eccezione.

Questa guida illustra come utilizzare e estendere la struttura di errore, garantendo **consistenza**, **audit** e **facilità di manutenzione**.

---

## 🗂️ Definizione dei Messaggi di Errore

### 📚 Tabella `config.messaggi_errore`

> Dati di origine dei template di messaggio.

* **Path**: `config/messaggi_errore.md`
* **Scopo Principale**: mantenere un catalogo multilingua di messaggi, cause e suggerimenti.
* **Campi chiave**:

  * `codice` (TEXT, PK): identificativo del messaggio.
  * `lingua` (TEXT): lingua del template (`it`, `en`, …).
  * `messaggio` (TEXT): testo con placeholder `%s`.
  * `causa` / `soluzione` (TEXT): dettagli per `DETAIL` e `HINT` dell’eccezione.

> Consulta la documentazione dettagliata: [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)

---

## 📑 Archiviazione degli Errori

### 📚 Tabella `dbops.error_log`

> Registro immutabile di tutte le occorrenze di errore.

* **Path**: `dbops/error_log.md`
* **Scopo Principale**: tracciare (timestamp, area, funzione, contesto JSONB) ogni errore prima dell’eccezione.
* **Campi chiave**:

  * `occurred_at` (TIMESTAMPTZ): istante di logging.
  * `area` / `function_name`: ambito e origine.
  * `messaggio_errore_id`: FK a `config.messaggi_errore.id`.
  * `context` (JSONB): payload di variabili/circostanze.
  * `tx_id` (UUID): transazione correlata.

> Consulta la documentazione dettagliata: [dbops.error_log](/dbzero/dbops/tabelle/error_log)

---

## ⚙️ Funzioni di Supporto

### 📘 `script.fn_get_messaggio`

> Recupera e formatta un messaggio dal catalogo

* **Path**: `script/fn_get_messaggio.md`
* **Scopo**: internazionalizzare e sostituire placeholder `%s` nel testo.
* **Link**: [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)

### 📘 `script.fn_log_and_raise_error`

> Esegue il logging remoto e solleva l’eccezione

* **Path**: `script/fn_log_and_raise_error.md`
* **Scopo**: unificare logging via `dblink_exec` e `RAISE EXCEPTION` con `DETAIL` e `HINT`.
* **Link**: [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 📘 `script.fn_log_error_only`

> Esegue il logging remoto ma non solleva l’eccezione

* **Path**: `script/fn_log_error_only.md`
* **Scopo**: unificare logging via `dblink_exec` .
* **Link**: [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only)

---

## 🔄 Flusso di Gestione degli Errori

1. **Validazione/Check** in trigger o procedure PL/pgSQL.
2. **Invocazione** di `script.fn_log_and_raise_error(`

   * parametri: `p_area`, `p_function_name`, `p_error_code`, `p_context`, (varargs)
   * il logging avviene su `dbops.error_log` in una connessione dedicata.
3. **Recupero** del testo con `script.fn_get_messaggio` (interno a `fn_log_and_raise_error`).
4. **Raise** dell’eccezione con `RAISE EXCEPTION`, includendo `DETAIL` e `HINT`.

L’applicazione riceverà l’errore formattato, mentre il database manterrà un audit completo.

---

## 💡 Best Practices

* **Centralizzare tutti i messaggi** in `config.messaggi_errore`, senza hard‑coding di testi.
* **Usare codici coerenti** e documentati (es. `ERR_TIMEOUT`, `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`).
* **Popolare il `context`** con dati rilevanti (ID, payload, parametri) per facilitare il debug.
* **Sfruttare la multilingua** definendo template in più lingue e usando il GUC `myapp.user_language`.
* **Monitoraggio**: creare viste o dashboard su `dbops.error_log` per alert e metriche di errore.
* **Evoluzione dello schema**: il JSONB `context` e il modello di log separato preservano la flessibilità nelle colonne future.

---

> 🧠 **“Un approccio unificato al logging e all’exception handling in Zero ERP garantisce qualità, tracciabilità e facilità di manutenzione: dai template in tabella alle connessioni dblink, fino alle eccezioni multilingua.”**

---

{% include-markdown "signature-core.md" %}
