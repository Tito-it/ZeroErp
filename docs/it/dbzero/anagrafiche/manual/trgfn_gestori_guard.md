## ⚙️ Documentazione Funzione – `anagrafiche.trgfn_gestori_guard()`

> 👀 **Vedi anche**
>
> **Tabelle correlate:**
>
> * [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori)
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
> **Trigger collegati:**
>
> * `trg_gestori_a10_guard_ins_upd` su `anagrafiche.gestori`
>
> **Funzioni di supporto:**
>
> * [dbops.fn_log_and_raise_error](/dbzero/dbops/funzioni/fn_log_and_raise_error)
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale
(latest review 03-12-25)
La funzione **`anagrafiche.trgfn_gestori_guard()`** è una **funzione trigger di guardia di dominio** per la tabella `anagrafiche.gestori`.

Viene eseguita **BEFORE INSERT/UPDATE** (tramite il trigger `trg_gestori_a10_guard_ins_upd`) e ha il compito di garantire che:

1. Il **soggetto_ruolo** associato al gestore **esista**.
2. Il **soggetto collegato** al gestore abbia una **partita IVA valorizzata**.
3. Esista al massimo **un solo record** in `anagrafiche.gestori` (regola di **singleton** del Gestore del Sistema Informativo).

In caso di violazione di una di queste regole, la funzione **non blocca manualmente** l'operazione, ma demanda la segnalazione a `fn_log_and_raise_error(...)`, che registra il contesto e solleva un'eccezione applicativa.

---

### 🧱 Contesto e attivazione

La funzione è pensata per essere utilizzata tramite il trigger:

```sql
CREATE OR REPLACE TRIGGER trg_gestori_a10_guard_ins_upd
    BEFORE INSERT OR UPDATE
    ON anagrafiche.gestori
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_gestori_guard();
```

Pertanto viene invocata automaticamente su **ogni inserimento o modifica** di un record della tabella `anagrafiche.gestori`.

---

### 🔎 Regole di dominio applicate

La funzione implementa **tre regole principali**:

1. **Esistenza del `soggetto_ruolo`**

   * Verifica che `NEW.soggetto_ruolo_id` referenzi un record esistente in `anagrafiche.soggetti_ruoli`.
   * In caso contrario, invoca:

     ```plpgsql
     dbops.fn_log_and_raise_error(
         'database',
         TG_NAME,
         p_codice_errore := 'E_GESTORE_SOGGETTO_RUOLO_MANCANTE',
         jsonb_build_object(
             'table', TG_TABLE_NAME,
             'soggetto_ruolo_id', NEW.soggetto_ruolo_id
         ),
         NULL::uuid,
         NEW.soggetto_ruolo_id::text
     );
     ```
   * La mancanza del ruolo è quindi gestita come **errore strutturale di configurazione**.

2. **Obbligatorietà della Partita IVA per il soggetto del Gestore**

   * Dato il `soggetto_ruolo`, la funzione risale al relativo `soggetto` e ne legge `partita_iva`.
   * Se `partita_iva` è `NULL` o vuota:

     ```plpgsql
     script.fn_log_and_raise_error(
         'database',
         TG_NAME,
         'E_RUOLO_RICHIEDE_PIVA',
         jsonb_build_object(
             'table', TG_TABLE_NAME,
             'soggetto_id', v_soggetto_id,
             'soggetto_ruolo_id', NEW.soggetto_ruolo_id
         ),
         NULL::uuid,
         'gestore',
         v_soggetto_id::text,
         NEW.soggetto_ruolo_id::text
     );
     ```
   * Questo codifica la regola di dominio: **il Gestore deve essere un soggetto con P.IVA** valida a livello anagrafico.

3. **Regola di singleton su `anagrafiche.gestori`**

   * La funzione controlla che non esistano **altri record** in `anagrafiche.gestori` oltre a quello eventualmente in aggiornamento:

     ```plpgsql
     SELECT g.id
       INTO v_existing_id
       FROM anagrafiche.gestori g
      WHERE g.id <> COALESCE(NEW.id, -1)
      LIMIT 1;
     ```
   * Se viene trovato un altro record (`FOUND = TRUE`), viene invocata:

     ```plpgsql
     script.fn_log_and_raise_error(
         'database',
         TG_NAME,
         'E_GESTORE_SINGLETON_VIOLATO',
         jsonb_build_object(
             'table', TG_TABLE_NAME,
             'existing_gestore_id', v_existing_id,
             'new_soggetto_ruolo_id', NEW.soggetto_ruolo_id
         ),
         NULL::uuid,
         NEW.soggetto_ruolo_id::text
     );
     ```
   * In questo modo viene garantito che esista **un solo Gestore del Sistema Informativo** in tutta la base dati.

---

### 🧩 Parametri e variabili principali

Essendo una funzione trigger, non espone parametri “classici”, ma utilizza i record **`NEW`** e i metadati del trigger (`TG_NAME`, `TG_TABLE_NAME`).

Variabili interne:

* `v_soggetto_id UUID` – id del soggetto associato al ruolo `NEW.soggetto_ruolo_id`.
* `v_partita_iva TEXT` – partita IVA del soggetto recuperata da `anagrafiche.soggetti`.
* `v_existing_id INTEGER` – id di un eventuale altro record già presente in `anagrafiche.gestori`.

Valore di ritorno:

* `RETURN NEW;` – se tutte le verifiche sono superate, l'operazione può proseguire normalmente.

---

### 🚨 Codici di errore gestiti

La funzione non esegue `RAISE EXCEPTION` direttamente, ma delega a:

* `dbops.fn_log_and_raise_error(...)`
* `script.fn_log_and_raise_error(...)`

che gestiscono in modo centralizzato **logging e generazione dell'eccezione**.

I principali codici di errore utilizzati sono:

* **`E_GESTORE_SOGGETTO_RUOLO_MANCANTE`**
  → Il `soggetto_ruolo_id` indicato non esiste in `anagrafiche.soggetti_ruoli`.

* **`E_RUOLO_RICHIEDE_PIVA`**
  → Il ruolo Gestore richiede che il soggetto collegato abbia `partita_iva` valorizzata.

* **`E_GESTORE_SINGLETON_VIOLATO`**
  → È stato rilevato un secondo record in `anagrafiche.gestori`, violando la regola di singleton.

Questi codici devono essere mappati nella tabella di messaggistica centralizzata (es. `config.messaggi_errore`) per garantire messaggi coerenti verso l'esterno.

---

### 📌 Dipendenze

La funzione dipende da:

* **Tabelle**

  * `anagrafiche.gestori`
  * `anagrafiche.soggetti_ruoli`
  * `anagrafiche.soggetti`

* **Funzioni esterne**

  * `dbops.fn_log_and_raise_error(...)`
  * `script.fn_log_and_raise_error(...)`

La corretta configurazione di queste funzioni e della tabella dei messaggi è fondamentale per avere errori tracciati e comprensibili.

---

### 💡 Considerazioni implementative

* La regola di **singleton** è implementata tramite query e non solo tramite vincolo `EXCLUDE` o `UNIQUE`, perché si vuole avere:

  * **controllo esplicito** sulla gestione dell'errore,
  * logging strutturato in JSON (`jsonb_build_object(...)`).
* Le funzioni `fn_log_and_raise_error` permettono di:

  * registrare il contesto (`TG_NAME`, `TG_TABLE_NAME`, chiavi coinvolte);
  * sollevare un'eccezione coerente con il framework applicativo (codici errore, testabilità, localizzazione).
* In ambienti multi-tenant o multi-utility il concetto di Gestore rimane **unico a livello di istanza DB**, e questa funzione ne garantisce la coerenza.

---

### ✅ Riepilogo

La funzione **`anagrafiche.trgfn_gestori_guard()`**:

* assicura che il **Gestore del Sistema Informativo** sia collegato a un ruolo e a un soggetto validi;
* impone che il soggetto del Gestore abbia **partita IVA valorizzata**;
* garantisce la regola di **“uno e un solo Gestore”** tramite controllo applicativo;
* integra la gestione errori con il framework centralizzato di logging/raising.

È quindi un tassello chiave per mantenere coerente e robusta l'anagrafica del Gestore nel modello dati di Zero ERP.

---

{% include-markdown "signature-core.md" %}
