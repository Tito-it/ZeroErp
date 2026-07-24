## 📘 Documentazione Concettuale – Trigger Function `dbops.trgfn_tx_id_managed()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
>
[dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids)      
>
Approfondimento funzioni :    
>
[dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)    
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    
### 🎯 Scopo Principale
(latest review 01-01-26)
La trigger function **`dbops.trgfn_tx_id_managed()`** viene eseguita **`BEFORE INSERT OR UPDATE`** su ogni tabella che contiene la colonna `tx_id` e centralizza la **logica di validazione**, **generazione** e **assegnazione** dell’**UUID di transazione** per la riga in corso di inserimento/aggiornamento.

---

### 🎯 Obiettivi e Ruolo

1. **Bypass configurabile**: permette di saltare la generazione e verifica del `tx_id` in contesti speciali (es. test, migrazioni, debug).
2. **Validazione integrità**: garantisce che un `tx_id` presente in sessione esista già in `dbops.transaction_ids`, altrimenti segnala un warning e resetta a `nil`.
3. **Generazione on-demand**: se non è presente alcun `tx_id` in sessione e il bypass è disabilitato, invoca `dbops.fn_get_or_create_session_tx_id()` per creare un nuovo identificativo.
4. **Assegnazione uniforme**: popola la colonna `NEW.tx_id` con il valore deciso dal flusso, assicurando coerenza transazionale.

---

### Variabili di Contesto e Configurazione

| Variabile                              | Scopo                                                                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `tx_id_bypass_enabled`                 | Parametro (`config.parameters`) che abilita il bypass completo: se `TRUE`, non viene generato né verificato un nuovo `tx_id`. |
| `app.bypass_tx_id_check`               | GUC di sessione: può essere usata per override temporanei del bypass senza cambiare il parametro globale.                     |
| `current_setting('dbops.tx_id', TRUE)` | Legge il valore di `tx_id` salvato in sessione, se presente; altrimenti solleva eccezione interna.                            |
| `script.uuid_nil()`                    | Funzione helper che restituisce l’UUID nil (`00000000-0000-0000-0000-000000000000`).                                          |

---

### Flusso di Esecuzione Dettagliato

1. **Verifica bypass globale**

   * Legge `config.parameters` per il parametro `tx_id_bypass_enabled`.
   * In caso di mancanza o di errore, logga via `fn_log_and_raise_error` e prosegue con bypass disabilitato.

2. **Override bypass a sessione**

   * Se il bypass non è già abilitato, prova a leggere `app.bypass_tx_id_check` dalla GUC di sessione.
   * Eventuali errori di lettura vengono ignorati (assume bypass disabilitato).

3. **Recupero `tx_id` di sessione**

   * Tenta `current_setting('dbops.tx_id', TRUE)` per ottenere un `tx_id` già presente in sessione.
   * In caso di errore o non esistenza, `v_session_tx_id` = `NULL`.

4. **Determinazione del nuovo `tx_id`**

   * **Bypass attivo**: usa `v_session_tx_id` se esistente, altrimenti `uuid_nil()`.
   * **Bypass disabilitato**:

     * **Se `v_session_tx_id` non è NULL**: verifica in `dbops.transaction_ids`.

       * Se esiste, lo riutilizza.
       * Se non esiste, logga warning (`W_TXID_NOT_REGISTERED`) e assegna `uuid_nil()`.
     * **Se `v_session_tx_id` è NULL**: genera uno nuovo con `dbops.fn_get_or_create_session_tx_id()`.

       * In caso di errori di generazione, logga errore (`E_TXID_GENERATION`) e usa `uuid_nil()`.

5. **Assegnazione a NEW\.tx\_id**

   ```plpgsql
   NEW.tx_id := v_new_tx_id;
   ```

   Garantisce che ogni riga inserita o aggiornata abbia sempre un `tx_id` valido secondo la logica centralizzata.

---

### 🔖 Esempio di Trigger DDL

```sql
DROP TRIGGER IF EXISTS trg_managed_tx_id ON my_schema.my_table;
CREATE TRIGGER trg_managed_tx_id
  BEFORE INSERT OR UPDATE
  ON my_schema.my_table
  FOR EACH ROW
  EXECUTE FUNCTION dbops.trgfn_tx_id_managed();
```

---

### Vantaggi Operativi

* **Centralizzazione logica**: nessuna duplicazione di codice di generazione/validazione del `tx_id` across tabelle.
* **Flessibilità**: gestisce bypass globali e di sessione per scenari di test, migrazione o debug.
* **Affidabilità**: verifica sempre l’esistenza del `tx_id` e assicura fallback pulito a `uuid_nil()`.
* **Tracciabilità avanzata**: associa ogni record al giusto `tx_id`, mantenendo coerenza con il registro centrale `transaction_ids`.

---

### 🛠️ Nota di manutenzione — 22-07-2026

**Cosa è stato fatto.** Il ramo «`tx_id` di sessione presente ma assente dal
registro» ora **avverte e prosegue**, come questo manuale ha sempre descritto
(«logga warning `W_TXID_NOT_REGISTERED` e assegna `uuid_nil()`»). Prima
**sollevava**. Migration `20260722-11`.

**Perché era un difetto e non una scelta.** Il ramo usava
`script.fn_log_and_raise_error`, che logga *e solleva*, dove serviva
`script.fn_log_error_only`, che logga soltanto. La prova sta nel codice: subito
dopo la chiamata c’era già `v_new_tx_id := script.uuid_nil();` — **una riga
irraggiungibile**, perché la funzione precedente non tornava mai. Tre fonti
indipendenti descrivevano il comportamento non bloccante — il commento nel
codice, questo manuale, e la guida `tx_id_implementation_guide.md` — contro
un’unica riga di codice che faceva il contrario.

**Non era stato allentato da nessuno.** Verificato sulle quattro versioni
storiche del trigger (`20250707-21`, `20250814-01`, `20251031-11`,
`20251114-04`): il ramo è identico in tutte, riga morta compresa. La discrepanza
è nata con la prima versione ed è stata ricopiata fedelmente.

**Convenzione applicata.** `E_` = errore bloccante (`fn_log_and_raise_error`),
`W_` = avvertimento (`fn_log_error_only`). Dopo la modifica il trigger la
rispetta: `E_SQL_READ_TABLE` ed `E_TXID_GENERATION` restano bloccanti — sono
errori veri — mentre `W_TXID_NOT_REGISTERED` avverte davvero. Il codice **non**
è stato rinominato in `E_`: il nome era già giusto, era il comportamento a non
rispettarlo. Regola completa in
[Messaggi di errore e generazione log](/it/guide/Messaggi-di-Errore-e-Generazione-Log).

**Dettaglio residuo, innocuo.** L’assegnazione finale è
`COALESCE(GUC dbops.tx_id, v_new_tx_id, uuidv7())`: la GUC ha la precedenza su
`v_new_tx_id`, quindi in questo ramo il valore scritto è l’id della GUC, non
`uuid_nil`. Dopo la correzione di
[dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/manual/fn_get_or_create_session_tx_id)
la GUC può contenere **solo** id registrati, quindi il caso non si presenta se
non impostandola a mano.

Verifiche: `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql` (7 test).
Approfondimento: `brief-db-coerenza-tx-id-non-registrato.md`.

---

> **“`trgfn_tx_id_managed` è il cuore della gestione transazionale in Zero ERP: garantisce consistenza, controlli configurabili e fallback sicuri, mantenendo la logica di correlazione centralizzata.”**
