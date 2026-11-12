## 📘 Documentazione Concettuale – Tabella `config.messaggi_errore`

> **Ultimo aggiornamento**: 13 novembre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[dbops.error_log](/dbzero/dbops/tabelle/error_log)    
> [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)    
>
Approfondimenti funzioni:   
>
[script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)  

La tabella **`config.messaggi_errore`** è il **catalogo centralizzato** dei testi applicativi (errori, avvisi, messaggi informativi) con supporto per internazionalizzazione (i18n). Ogni record definisce un messaggio univoco, differenziato per codice e lingua, corredato di causa e suggerimenti di soluzione.

---
### 🎯 Scopo Principale
* **Centralizzare i messaggi**: evitare hard‑coding nei sorgenti SQL, trigger o procedure.
* **Supporto multilingua**: gestire versioni localizzate tramite il campo `lingua` (es. `it`, `en`).
* **Placeholder dinamici**: usare `%s` nel campo `messaggio`, sostituiti a runtime dalla funzione `script.fn_get_messaggio` con valori contestuali.
* **Collegamento ai log**: tabelle come `dbops.error_log` e `dbops.audit_log` fanno riferimento a `config.messaggi_errore` per arricchire i record di log con testi coerenti.

---

### Struttura dei Campi

| Nome        | Tipo   | Dettagli                                                                             |
| ----------- | ------ | ------------------------------------------------------------------------------------ |
| `codice`    | text   | Codice logico del messaggio (es. `ERR001`, `WARN_TIMEOUT`); parte della PK           |
| `lingua`    | text   | ISO code della lingua (default: `it`); parte della PK                                |
| `messaggio` | text   | Testo principale, può contenere placeholder `%s`                                     |
| `causa`     | text   | Causa del messaggio: breve descrizione del problema riscontrato                      |
| `soluzione` | text   | Suggerimenti o passi per risolvere il problema indicato nella causa                  |
| `id`        | bigint | PK surrogata, generata automaticamente da sequenza (`config.messaggi_errore_id_seq`) |

---

### Vincoli di Integrità

* **Primary Key**: `pk_messaggi_errore (id)` garantisce l’identificativo univoco.
* **Unique Constraint**: `uq_messaggi_errore_codice_lingua (codice, lingua)` per evitare duplicati della medesima traduzione.
* **Causa e soluzione assenti** (dal 2026-11-13, `90_end/20261112-55`): un messaggio senza causa o
  senza soluzione le ha `NULL`, mai la stringa vuota. Due `CHECK`
  (`chk_messaggi_errore_causa_non_vuota`, `chk_messaggi_errore_soluzione_non_vuota`) rifiutano `''`,
  anche di soli spazi. Nel CSV del seed la cella senza valore porta il token `NULL`: una cella vuota
  arriverebbe come stringa vuota (linee-guida-sql §11.2), e il guardrail delle forme la rifiuta.

---

### Relazioni Operative ed Esempi

1. **Collegamento con error\_log**

   ```sql
   SELECT e.id,
          me.codice,
          me.messaggio,
          e.context
     FROM dbops.error_log e
     JOIN config.messaggi_errore me
       ON e.messaggio_errore_id = me.id;
   ```
2. **Uso in audit\_log o procedure**

   ```sql
   -- Recupera e formatta un messaggio con placeholder
   SELECT script.fn_get_messaggio(
     'ERR001', 'it', ARRAY[e.order_id::text]
   );
   ```
3. **Inserimento di un nuovo messaggio**

   ```sql
   INSERT INTO config.messaggi_errore(
     codice, lingua, messaggio, causa, soluzione
   ) VALUES (
     'WARN_DISCOUNT', 'en',
     'Order %s has no discount applied',
     'Nessuna regola di sconto trovata',
     'Verificare la configurazione delle promozioni'
   );
   ```

---

### Vantaggi Operativi

* **Manutenzione semplificata**: testi gestiti in un’unica tabella.
* **Consistenza e coerenza**: unico punto di verità per i messaggi.
* **Internazionalizzazione**: aggiunta di nuove lingue facile e veloce.
* **Parametrizzazione**: placeholder `%s` consentono messaggi contestualizzati.
* **Integrazione con log**: collegamento trasparente a tabelle di log per ricostruire flussi e storici.

---

> **“Un catalogo centralizzato, multilingua e parametrizzato dei messaggi applicativi favorisce coerenza, facilità di manutenzione e miglior supporto agli utenti.”**
