## 📘 Documentazione Concettuale – Tabella `dbops.error_log`

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)    
> [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)    
>
Approfondimento funzioni:    
> 
[dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)    
> [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic)    

La tabella **`dbops.error_log`** serve a **centralizzare la registrazione degli errori** che si verificano nelle diverse aree dell’applicazione (database, backend, frontend, job, ecc.), fornendo un quadro completo del contesto, della fonte e della transazione coinvolta.

---
### 🎯 Scopo Principale
* Raccogliere in un unico punto gli errori generati da funzioni, trigger o applicazioni, permettendo analisi e allineamento con il catalogo di messaggi di errore.
* Consentire il **collegamento transazionale** tramite `tx_id`, per ricostruire l’intero flusso di operazioni (ad esempio un job batch) incrociando tabelle come `dbops.audit_log`.

---

### 🔒 Privilegi — registro APPEND-ONLY per l'applicazione (dal 2026-09-11)

`zeroerp_app` — il ruolo con cui l'applicazione si collega, cioè il soggetto che
questo registro racconta — può **leggere** e **aggiungere** (`SELECT`, `INSERT`).
Non `UPDATE`, non `DELETE`, non `TRUNCATE`: *un registro modificabile da chi è
auditato non è un registro*. Nessuna funzione e nessun codice del backend
aggiorna o cancella righe di `error_log`; la retention su `cleanup_at` è
mestiere del proprietario.

⚠️ La postura **non** è un `REVOKE` scritto una volta: i privilegi dell'app
vengono riconcessi in blocco a ogni passata `ci_apply`, e la postura più
stretta è **dichiarata dentro quel loop** (`90_end/ci_apply/20260205-41`).
Presidio: `db/pgtap/dbops/test-registri-append-only-postura-v1.sql`.
Regola: [linee-guida-sql](/linee-guida-sql) §11.8; motivazione: guida
[Audit Logging](/guide/messaggi-audit), sezione *Chi può scrivere*.

---

### Significato dei Campi Chiave

* **`id`**: identificativo univoco del record di errore.
* **`occurred_at`**: timestamp con timezone dell’evento di errore.
* **`area`**: ambito di origine (es. `database`, `backend`, `frontend`, `job`).
* **`function_name`**: nome della funzione o metodo che ha generato l’errore (trigger, procedure, job, endpoint).
* **`messaggio_errore_id`**: FK verso `config.messaggi_errore(id)`, collega il record al testo di errore e alle eventuali traduzioni.
* **`context`**: campo JSONB in cui si registrano parametri di input, valori di variabili, utente esecutore o altri metadati rilevanti.
* **`tx_id`**: UUID di transazione corrente, utile per tracciare errori in contesti transazionali e correlare con altri log.
* **`cleanup_at`**: timestamp opzionale di pulizia programmata (non indica scadenza funzionale).

---

### Vincoli e Relazioni

* **PK**: vincolo `error_log_pkey` su `id`.
* **FK**: `messaggio_errore_id` → `config.messaggi_errore(id)` (senza azioni di update o delete).
* **Generazione automatica**:

  * `occurred_at` default `now()`
  * `tx_id` 
  * `context` default a JSONB vuoto `{}`

---

### 🚨 Trigger

* **`trg_assign_tx_id_error_log`** (BEFORE INSERT OR UPDATE): assegna automaticamente il valore di `tx_id` tramite la trigger function `dbops.trgfn_tx_id_managed()`, garantendo che ogni record di errore sia correlato all’identificativo di transazione.
* **Protezione modifiche**: dal 2026-09-11 la protezione è nei **privilegi**: `zeroerp_app` ha `SELECT, INSERT` e basta — vedi *Privilegi* qui sotto. Un trigger `script.trgfn_prevent_modification_generic()` resterebbe l'attrezzo per bloccare anche il proprietario, se un giorno servisse; oggi non è montato.

---

### Esempi di Utilizzo

1. **Recuperare tutti gli errori di una specifica transazione**:

   ```sql
   SELECT *
     FROM dbops.error_log
    WHERE tx_id = '123e4567-e89b-12d3-a456-426614174000';
   ```

2. **Unire gli errori con il catalogo dei messaggi**:

   ```sql
   SELECT e.id, e.occurred_at, m.codice, m.messaggio, e.context
     FROM dbops.error_log e
     JOIN config.messaggi_errore m ON e.messaggio_errore_id = m.id;
   ```

3. **Cronologia completa di una transazione**:

   ```sql
   WITH errs AS (
     SELECT * FROM dbops.error_log WHERE tx_id = :tx
   ), audits AS (
     SELECT * FROM dbops.audit_log WHERE tx_id = :tx
   )
   SELECT * FROM errs
   UNION ALL
   SELECT * FROM audits
   ORDER BY occurred_at;
   ```

---

### 🔎 Gli indici della consultazione (dal 19-09-2026)

La consultazione dei tecnici — «quale funzione ha sollevato quale codice,
quando, in quale transazione» (pezzo E del piano BE/FE dell'osservabilità) —
dichiara una whitelist di filtri, e **ogni filtro dichiarato ha un indice da cui
partire** (P-3 del brief `brief-db-osservabilita-lotto-fermo-r6-indici`,
changeSet `20260919-06`):

| Indice | Serve a |
| --- | --- |
| `ix_error_log_occurred_at` | la finestra `data_da`/`data_a`, il filtro sempre presente, e la prima pagina (`ORDER BY occurred_at DESC LIMIT n`) |
| `ix_error_log_area_occurred_at` | `area` (esatto), ordinato nel tempo dentro l'area |
| `ix_error_log_function_name_occurred_at` | `function_name`, esatto o a **prefisso** — con `text_pattern_ops` |
| `ix_error_log_tx_id` | il **ponte** dal giornale (`script.vw_giornale_entita.tx_id`) agli appunti tecnici della stessa transazione |

`codice` sta sul catalogo, non qui: si risolve prima `codice → messaggio_errore_id`
e si entra dall'indice che c'è già.

⛔ **Due cose da sapere sul prefisso di `function_name`**, verificate con
`EXPLAIN` il 19-09:

1. la collation del database è `it_IT.UTF-8`: un btree ordinario **non serve**
   `LIKE 'x%'`. L'indice ha `text_pattern_ops`, che serve `=` e `LIKE 'x%'` —
   e **mai** `ILIKE`. Il backend filtri con `LIKE`: i nomi di funzione sono
   minuscoli per convenzione;
2. **`_` è un jolly di `LIKE`**, e i nomi di funzione ne sono pieni:
   `LIKE 'fn_get_lotto%'` ha come prefisso fisso solo `fn`, e il planner torna
   a scandire la tabella. Il prefisso va **escapato** (`fn\_get\_lotto%`) — che
   è anche l'unica forma corretta: senza, `fn_get` combacerebbe con `fnXget`.

⚠️ Il costo sta in scrittura, ed è dichiarato: la tabella si scrive a ogni
errore, e quattro indici in più sono quattro scritture in più sul ramo che sta
già fallendo. È il posto giusto per pagarli.

---

### 🧹 Pulizia programmata (`cleanup_at`)

Il campo **`cleanup_at`** è usato esclusivamente per **gestire job di pulizia** dei log storici.  
Non rappresenta una scadenza “funzionale” dell’errore, ma solo un **timestamp indicativo per il cleanup**.

---

### Vantaggi Operativi

* **Tracciabilità a 360°**: unisce errori e transazioni in un unico flusso temporale.
* **Analisi rapida**: il campo `context` permette filtri e aggregazioni sui metadati.
* **Integrità delle informazioni**: i trigger automatici garantiscono corretto popolamento di `tx_id` e audit inalterabile.
* **Coerenza semantica**: l’uso di FK verso `config.messaggi_errore` assicura messaggi uniformi e localizzati.

---

### Pattern di integrazione con log di dominio

`dbops.error_log` è il **log tecnico centralizzato**.  
Nei domini applicativi è consigliato affiancarlo con log funzionali dedicati.

Esempio dominio vendite/fatturazione:

* log tecnico: `dbops.error_log` (raise SQL / ErrorManager backend)
* log di processo lotto: `vendite.fatturazione_lotti_log`
* log documento: `vendite.fatture_log`

Regola operativa:

* errore di orchestrazione/processo -> log di dominio `LOTTO` + `error_log`
* errore su singolo documento -> log di dominio `FATTURA` + `error_log`

Questo approccio evita ambiguità: `error_log` conserva il dettaglio tecnico,
mentre i log di dominio governano stato/esito funzionale visibile in dashboard.

---

> **“Un error log strutturato con identità transazionale e contesto dettagliato semplifica il debug e il monitoraggio degli incidenti applicativi.”**

---

### 🧹 Scadenza

Una riga di errore resta **90 giorni** dall'orario dell'errore (`occurred_at`), come le
chiamate di [`dbops.request_log`](/dbzero/dbops/manual/request_log): regola CLEANUP_AT id=25.
La scadenza la calcola il job settimanale delle automazioni, non un trigger alla nascita:
la tabella la scrive anche una sessione dblink che non legge le regole. Dettaglio nella
guida [Audit e tracciabilità](/guide/audit-e-tracciabilita).
