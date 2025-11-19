## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_contatti_ins_upd_set_default_contatto`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)    
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)    
>
> Approfondimento funzioni :    
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)     


La trigger function **`anagrafiche.trgfn_contatti_ins_upd_set_default_contatto()`** gestisce automaticamente il contatto predefinito per un soggetto, tenendo conto di un **contesto** dinamico (`soggetto`, `ruolo` o `utility`). Assicura che esista al massimo un contatto default per soggetto e contesto, ed aggiorna il riferimento `default_contatto_id` in `anagrafiche.soggetti` quando richiesto.

---

### 🎯 Scopo Principale

* **Impostare il contatto default**
  Garantire che il primo contatto (o quello marcato explicitamente) diventi predefinito all’interno del suo contesto.

* **Contesto dinamico**
  Utilizzare il campo `default_context` (valori: `soggetto`, `ruolo`, `utility`) per isolare i default per diversi ambiti di utilizzo.

* **Sincronizzazione con anagrafica soggetti**
  Se il contesto è `soggetto`, aggiornare in automatico `anagrafiche.soggetti.default_contatto_id` per mantenere il collegamento principale.

---

### 🔍 Parametri e Contesto

* **Trigger associato**: `BEFORE INSERT OR UPDATE` su `anagrafiche.contatti`.
* **Colonne coinvolte**:

  * `NEW.is_default BOOLEAN`
  * `NEW.default_context TEXT`
  * `NEW.utility_id` (opzionale)
  * `NEW.soggetto_ruolo_id` (opzionale)
  * `NEW.soggetto_id UUID`

---

### ⚙️ Flusso Logico

1. **Azzeramento contesto**

   ```plpgsql
   NEW.default_context := NULL;
   ```

2. **Determinazione contesto**

   ```plpgsql
   ctx := CASE
     WHEN NEW.utility_id        IS NOT NULL THEN 'utility'
     WHEN NEW.soggetto_ruolo_id IS NOT NULL THEN 'ruolo'
     ELSE 'soggetto'
   END;
   ```

3. **Gestione contatto marcato default**
   Se `NEW.is_default = TRUE`:

   * Disabilita (`is_default = FALSE`) tutti i contatti esistenti dello stesso `soggetto_id` e `default_context` = `ctx`, eccetto `NEW.id`.
   * Imposta `NEW.default_context := ctx`.
   * Se `ctx = 'soggetto'`, aggiorna `anagrafiche.soggetti.default_contatto_id = NEW.id`.
   * Restituisce `NEW`.

4. **Assegnazione primo default**
   Se `NEW.is_default = FALSE` e non esistono contatti default per `soggetto_id` e `ctx`:

   * Imposta `NEW.is_default := TRUE` e `NEW.default_context := ctx`.
   * Se `ctx = 'soggetto'`, aggiorna `anagrafiche.soggetti.default_contatto_id = NEW.id`.

5. **Chiusura**
   Restituisce `NEW` con i valori aggiornati.

---

### 🔒 Vincoli e Assunzioni

* **Contesto obbligatorio**: `default_context` viene sempre valorizzato a uno dei tre valori.
* **Unico default per contesto**: la funzione garantisce un solo contatto `is_default = TRUE` per coppia (`soggetto_id`, `default_context`).
* **Aggiornamento referenza soggetto**: solo per `default_context = 'soggetto'` si propaga l’ID contatto.

---

### 💡 Vantaggi Operativi

* **Gestione semplificata dei default**
  Automatizza l’impostazione del contatto principale per soggetti e ruoli.
* **Contesti indipendenti**
  Consente di avere contatti di default distinti per scopi diversi (`soggetto`, `ruolo`, `utility`) senza mescolarli.
* **Sincronizzazione diretta**
  Tiene coerente il campo `default_contatto_id` in `anagrafiche.soggetti` senza ulteriori query esterne.
* **Manutenibilità**
  Centralizza la logica di default in un’unica function, riutilizzabile in più trigger.

---

> 🧠 **“Una trigger function flessibile che assegna e mantiene automaticamente il contatto predefinito in base a contesti distinti, semplificando la gestione dei dati di contatto.”**
