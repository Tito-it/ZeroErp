📘 Documentazione Concettuale – Tabella `public.version_info`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:   
> [internal.trgfn_audit_version_info](/dbzero/internal/funzioni/trgfn_audit_version_info)     

---
 
### 🎯 Scopo Principale

Mantenere un registro delle versioni dell’applicazione **ZeroErp**, conservando informazioni su:

* **version**: etichetta di release/deploy (es. `1.2.0`, `2025.07.11`).
* **created\_at**: data di inserimento del record.
* **last\_updated\_at** e **last\_updated\_by**: ultimo aggiornamento della versione e utente che lo ha effettuato.

---

### Vincoli

* **PRIMARY KEY**: `version_info_pkey` su `id` (auto-increment).
* **DEFAULT**: `app_name` è di default `'ZeroErp'`.

---

### 🚨 Trigger

* **`trg_version_info_audit`** (BEFORE UPDATE): invoca la funzione `internal.trgfn_audit_version_info()` per aggiornare automaticamente i campi di auditing `last_updated_at` e `last_updated_by` ad ogni modifica.

---

### Meccanismo di Utilizzo

1. **Inserimento versione**
   Ogni nuova release inserisce un record con il numero di `version`.

   ```sql
   INSERT INTO public.version_info(version) VALUES('2025.07.11');
   ```
2. **Aggiornamento**
   Per modificare la versione in uso (senza alterare la historicità), si esegue:

   ```sql
   UPDATE public.version_info
      SET version = '2025.07.12'
    WHERE id = <current_id>;
   ```

   Il trigger di auditing provvede ad aggiornare `last_updated_at` e `last_updated_by`.
3. **Lettura**
   Per recuperare l’ultima versione:

   ```sql
   SELECT *
     FROM public.version_info
    ORDER BY created_at DESC
    LIMIT 1;
   ```

---

### Vantaggi Operativi

* **Tracciabilità delle release**: ogni modifica rimane storicizzata con timestamp e utente.
* **Auditing automatico**: nessuna necessità di gestire manualmente i campi di update.
* **Centralità**: punto unico per consultare la versione corrente e passate del sistema.

> **“Un registro versioninfo ben gestito è fondamentale per deployment sicuri, rollback controllati e per supportare processi di monitoraggio e diagnostica.”**
