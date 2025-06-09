## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_lock_columns`

> 👀 **Vedi anche**

> Approfondimenti funzioni:   
>  - [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)   


La trigger function **`script.trgfn_lock_columns()`** impedisce la modifica di una o più colonne specificate, sollevando un errore personalizzato se si tenta di aggiornare un valore bloccato. I parametri da passare sono coppie di colonne e relativi codici messaggio di errore.

---

### 🎯 Scopo Principale

* **Prevenire modifiche non autorizzate**
  Garantire che determinati campi di una riga non vengano modificati dopo l’inserimento iniziale, eseguendo controlli `OLD vs NEW` e scatenando eccezioni in caso di variazione.

* **Centralizzare la logica di locking**
  Utilizzare un’unica trigger function per tutti i casi in cui una colonna debba essere resa immutabile, evitando boilerplate in ciascun trigger.

* **Messaggi di errore contestualizzati**
  Fornire feedback chiaro e localizzato usando codici di messaggio personalizzati e la funzione `script.fn_get_messaggio` per gestire i testi (placeholder `%s`).

---

### 🔍 Parametri di Configurazione (TG\_ARGV)

I parametri vanno passati **a coppie** nell’ordine:

```
PER ESEMPIO:
ARGV[0] = 'cd_int_ruolo'           -- nome colonna da bloccare
ARGV[1] = 'E_COLONNA_NON_MODIFICABILE'  -- codice messaggio di errore
ARGV[2] = 'altra_colonna'
ARGV[3] = 'E_ALTRO_ERRORE'
```

* `n_args := array_length(TG_ARGV,1)` deve essere pari; altrimenti viene sollevata eccezione `E_ARGOMENTI_A_COPPIE`.
* Ogni coppia: **colonna**, **codice messaggio**.

---

### ⚙️ Flusso Logico

1. **Verifica coppie argomenti**
   Se il numero di elementi in `TG_ARGV` è dispari, solleva eccezione:

   ```plpgsql
   RAISE EXCEPTION '%', script.fn_get_messaggio('E_ARGOMENTI_A_COPPIE');
   ```
2. **Loop sulle coppie**
   Per ogni `i` da 1 a `n_args` con passo 2:

   * `col := TG_ARGV[i-1]`
   * `msgcode := TG_ARGV[i]`
   * Esegue:

     ```plpgsql
     EXECUTE format(
       'SELECT ($1).%I::text, ($2).%I::text', col, col
     ) USING OLD, NEW INTO oldval, newval;
     ```
3. **Confronto valori**

   ```plpgsql
   IF oldval IS DISTINCT FROM newval THEN
       RAISE EXCEPTION '%',
         script.fn_get_messaggio(
           p_codice => msgcode,
           p_valore => col
         );
   END IF;
   ```
4. **Ritorno**
   Se nessuna colonna è stata modificata, restituisce `NEW` per proseguire l’operazione.

---

### 🔒 Error Handling

* **`E_ARGOMENTI_A_COPPIE`**
  Parametri `TG_ARGV` forniti in numero dispari (devono essere coppie).

* **`E_COLONNA_NON_MODIFICABILE`**
  Placeholder `%s` verrà sostituito con il nome della colonna non modificabile.

I messaggi reali sono recuperati tramite `script.fn_get_messaggio`, con possibilità di localizzazione (`p_lingua`) e sostituzione dinamica di `%s`.

---

### 💡 Vantaggi Operativi

* **Modularità**
  Un’unica trigger function per bloccare qualsiasi colonna specificata, riutilizzabile in molti contesti.

* **Coerenza dei messaggi**
  Tutti gli errori vengono generati con codici e testi centralizzati in `config.messaggi_errore`.

* **Manutenzione semplice**
  Aggiungere o rimuovere colonne bloccate cambia solo i parametri `TG_ARGV`, senza modificare lo script PL/pgSQL.

* **Localizzazione**
  Grazie a `script.fn_get_messaggio`, i testi di errore possono essere forniti in più lingue.

---

> 🧠 **“Una trigger function flessibile e centralizzata per rendere immutabili campi critici, con messaggi di errore parametrizzati e localizzati.”**