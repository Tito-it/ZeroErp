## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_lock_columns()`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)   
>  [dbops.error_log](/dbzero/dbops/tabelle/error_log)   
>
Approfondimenti funzioni:   
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)   
### 🎯 Scopo Principale
-  Trigger function generica per **bloccare modifiche non autorizzate** su colonne specificate, integrando:

* **Controllo dinamico** delle colonne PASSATE come argomenti al trigger
* **Logging remoto** tramite dblink, per tracciare l’evento prima del rollback
* **Messaggi parametrizzati** con placeholder e codici definiti in `config.messaggi_errore`

---

### GUC di override per manutenzione

La funzione supporta un **override via GUC** per consentire la modifica delle colonne
protette in contesti di manutenzione, senza dover DISABLE/ENABLE TRIGGER:

```sql
BEGIN;
SET LOCAL zeroerp.allow_lock_columns_override = 'on';
UPDATE anagrafiche.fornitori SET codice = 'NUOVO-CODICE' WHERE id = 123;
COMMIT;
```

- **GUC**: `zeroerp.allow_lock_columns_override`
- **Valore di attivazione**: `'on'`
- **Scope consigliato**: `SET LOCAL` (solo la transazione corrente)
- **Default**: assente o qualsiasi valore diverso da `'on'` → colonne protette
- **Pattern**: coerente con `trgfn_delete_block_by_guc` che usa GUC per l'override delle delete

---

### 🎯  Comportamento Chiave

1. **GUC override** — se `zeroerp.allow_lock_columns_override = 'on'`, ritorna `NEW` immediatamente senza controlli

2. **Validazione degli argomenti**

   * Accetta un numero pari di parametri (`colonna`, `msgcode`)
   * Se dispari, invoca `fn_log_and_raise_error(‘database’, TG_NAME, ‘E_ARGOMENTI_A_COPPIE’, {...})`

3. **Ciclo di verifica**

   * Per ogni coppia, estrae **OLD.col** e **NEW\.col** in modo dinamico
   * Confronta i valori: se **distinti**, scatta il blocco

4. **Gestione dell’errore**

   * Chiama `script.fn_log_and_raise_error` con:

     * **Area**: `database`
     * **Function\_name**: nome del trigger (TG\_NAME)
     * **Error\_code**: codice testuale passato
     * **Context**: JSON con `campo` (la colonna da evidenziare nel form), `column`, `old_value`, `new_value`
     * **Placeholder**: il nome della colonna per sostituire `%s`
   * La funzione logga su `dbops.error_log` (via dblink\_connect) e **rialza un’eccezione** con dettaglio e hint

5. **Permette UPDATE** solo se nessuna colonna protetta è stata modificata

---

### Punti di Interesse

* **TG\_ARGV**: array variadico; le posizioni pari/dispai determinano colonna e messaggio
* **EXECUTE dinamico**: `format('SELECT ($1).%I, ($2).%I', ... )` per ottenere valori senza hard‑coding
* **Logging isolato**: il dblink `logconn` inserisce il log in una sessione separata, garantendo il commit anche in caso di rollback nella sessione corrente
* **Placeholder variadico**: il quinto parametro di `fn_log_and_raise_error` permette di inserire il nome della colonna in `%s` dentro il messaggio predefinito

---

### Esempio di Utilizzo

```sql
CREATE TRIGGER trg_lock_sensitive
  BEFORE UPDATE ON app.orders
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_lock_columns(
    'customer_id',   'ERR_LOCK_CUSTID',
    'order_status',  'ERR_LOCK_STATUS'
  );
```

* **customer\_id** non può cambiare: userà `ERR_LOCK_CUSTID` e mostrerà in messaggio il campo stesso
* **order\_status** è protetto con `ERR_LOCK_STATUS`

---

### ✨ Vantaggi Operativi

* **Zero duplicazioni**: una sola function per più tabelle e colonne
* **Flessibilità totale**: basta passare argomenti diversi per replicare il pattern
* **Tracciabilità**: ogni blocco viene loggato con contesto e transazione (tx\_id)
* **Manutenibilità**: i messaggi di errore si aggiornano in `config.messaggi_errore` senza toccare il trigger

---

> **“Con `trgfn_lock_columns` gestisci centralmente i blocchi di sicurezza su colonne critiche, integrando log e messaggi dinamici in un’unica soluzione.”**