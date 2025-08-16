
## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:   
>
> * [config.stati](/dbzero/config/tabelle/stati)   
>
> Approfondimenti funzioni:   
>
> * [script.validate_cf_piva_it](/dbzero/script/funzioni/fn_validate_cf_piva_it)   


### 🎯 Scopo Principale

La trigger function **`anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()`** viene eseguita **`BEFORE INSERT OR UPDATE`** sulla tabella **`anagrafiche.soggetti`** e instrada la validazione di codice fiscale e partita IVA in base allo Stato e al dettaglio di soggetto.

---

### ⚙️ Obiettivi e Ruolo

1. **Selezione del contesto nazionale**
   Recuperare il `codice_iso2` dello Stato (`stato_id`) per identificare il Paese di validazione.
2. **Dispatch su validazione specifica**
   Per lo Stato IT, invocare la funzione `script.fn_validate_cf_piva_it`, passando il dettaglio di soggetto e i campi fiscali.
3. **Estendibilità**
   Consentire in futuro di aggiungere branch per altri paesi, invocando funzioni di validazione dedicate.


---

### 🔍 Flusso di Esecuzione Dettagliato

1. **Recupero Stato**

   ```
   SELECT codice_iso2 INTO country
     FROM config.stati
    WHERE id = NEW.stato_id;

   ```
2. **Controllo branch IT**
   Se `country = 'IT'`, viene eseguita:

   ```
   PERFORM script.fn_validate_cf_piva_it(
     NEW.tipo_soggetto_dettaglio_id,
     NEW.partita_iva,
     NEW.piva_gruppo_acquisto,
     NEW.codice_fiscale
   );

   ```
3. **Ritorno del record**
   Quando la validazione termina senza eccezioni, la riga viene restituita a INSERT/UPDATE.

---

### 🔖 Esempio di Trigger DDL

```
DROP TRIGGER IF EXISTS trg_soggetti_ins_upd_dispatch_valida_cf_piva
  ON anagrafiche.soggetti;

CREATE TRIGGER trg_soggetti_ins_upd_dispatch_valida_cf_piva
  BEFORE INSERT OR UPDATE
  ON anagrafiche.soggetti
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch();

```

---

### 💡 Vantaggi Operativi

* **Centralizzazione validation**: tutta la logica di CF/P.IVA per l’Italia è in un’unica funzione.
* **Manutenibilità**: nuove regole per altri paesi si aggiungono semplicemente con nuovi branch o funzioni dedicate.
* **Coerenza dati**: errori di formato e regole specifiche sono applicate a livello database, riducendo la complessità lato applicazione.

---

> 🧠 “Con il dispatch centralizzato in `trgfn_soggetti_valida_cf_piva_dispatch`, Zero ERP assicura controlli locali e internazionali sui dati fiscali in modo modulare e a prova di evoluzioni future.”
