## 📘 Documentazione Funzione – `script.fn_generate_codice(tipo TEXT)`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
>
[config.sistema_codici](/dbzero/config/tabelle/sistema_codici)      
>
Approfondimento funzioni :    
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    


La funzione **`script.fn_generate_codice(tipo TEXT)`** genera in modo parametrico un nuovo codice alfanumerico per uno specifico “tipo” (es. `ORDINE`, `CLIENTE`, `FATTURA`), basandosi sui parametri definiti nella tabella **`config.sistema_codici`**. Se la configurazione per quel tipo non esiste, viene sollevata un’eccezione.

---
### 🎯 Scopo Principale
(latest review 04-02-26)
* **Generazione di codici configurabili**
  Costruisce un codice concatenando un **prefisso**, un **separatore** e una **parte numerica** formattata, letti da **`config.sistema_codici`** in base al `codice_interno` passato in input.

* **Unicità tramite sequenza**
  Invoca la sequenza database derivata da `schema_tabella/nome_tabella/nome_colonna` per ottenere un valore numerico progressivo, garantendo codici unici e ordinati.

* **Verifica configurazione**
  Se la riga corrispondente a `codice_interno = tipo` non esiste, la funzione solleva un’eccezione con messaggio di errore. Se `usa_sequenza = FALSE`, la funzione restituisce `NULL`.

---

### Parametri di input

| Nome   | Tipo   | Descrizione                                                                                                 |
| ------ | ------ | ----------------------------------------------------------------------------------------------------------- |
| `tipo` | `TEXT` | Identificativo del `codice_interno` nella tabella `config.sistema_codici`. Esempi: `"ORDINE"`, `"CLIENTE"`. |

---

### Valore di ritorno

| Tipo restituito | Descrizione                                                                            |
| --------------- | -------------------------------------------------------------------------------------- |
| `TEXT`          | Stringa del codice generato, formata come `<prefisso><separatore><numero_formattato>`. |

```
               | Esempi: `ORD-000123`, `CL_000045`.                                                                                 |
```

---

### Logica interna

1. **Lettura dei parametri**

   ```plpgsql
   SELECT prefisso,
          separatore,
          lunghezza_numero,
          usa_sequenza,
          schema_tabella,
          nome_tabella,
          nome_colonna
     INTO prefix,
          sep,
          len,
          v_usa_sequenza,
          v_schema_tabella,
          v_nome_tabella,
          v_nome_colonna
     FROM config.sistema_codici
    WHERE codice_interno = tipo;
   ```

   * Recupera da **`config.sistema_codici`** i valori di:

     * `prefisso` (testo da anteporre)
     * `separatore` (stringa di separazione)
     * `lunghezza_numero` (numero di cifre per la parte numerica)
     * `usa_sequenza` (abilitazione sequenza)
     * `schema_tabella`, `nome_tabella`, `nome_colonna` (metadati per il nome sequenza)
   * Se non trova alcuna riga per quel tipo, la funzione solleva un’eccezione.

2. **Generazione del numero tramite sequenza**

   ```plpgsql
   IF v_usa_sequenza IS DISTINCT FROM TRUE THEN
     RETURN NULL;
   END IF;

   seq_name := format('%I.%I_%I_seq', v_schema_tabella, v_nome_tabella, v_nome_colonna);

   IF to_regclass(seq_name) IS NULL THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       v_context_name,
       'SEQUENZA_NON_CONFIGURATA',
       jsonb_build_object('codice_interno', tipo, 'sequence_name', seq_name),
       NULL::uuid,
       tipo::TEXT
     );
   END IF;

   EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
   risultato := prefix || sep || lpad(seq_val::TEXT, len, '0');
   RETURN risultato;
   ```

   * La sequenza deve essere pre-provisionata e viene usata per ottenere il prossimo valore numerico.
   * Converte `seq_val` in testo e lo riempie a sinistra con zeri fino a raggiungere la lunghezza `len`.
   * Concatena `prefisso`, `separatore` e `numero_formattato`, restituendo il risultato.

---

### 🚨 Possibili eccezioni

* **SEQUENZA_NON_CONFIGURATA**
  Viene sollevata quando:

  * Non esiste un record in **`config.sistema_codici`** per `codice_interno = tipo`.
  * `usa_sequenza = TRUE` ma non è possibile determinare una sequenza valida.

  Il messaggio di errore è generato da:

  ```plpgsql
  script.fn_log_and_raise_error(...)
  ```

---

### Dipendenze

* **Tabella di configurazione**

  * **`config.sistema_codici`** deve contenere una riga per ciascun `codice_interno` con almeno:

    * `prefisso`: stringa testuale (es. `"ORD-"`).
    * `separatore`: carattere o stringa (es. `"-"`).
    * `lunghezza_numero`: numero intero (es. `6`).
    * `schema_tabella`, `nome_tabella`, `nome_colonna`: usati per derivare il nome sequenza di default.

* **Sequenza database**

  * La sequenza calcolata deve esistere gia'. Se manca, la funzione solleva errore (`SEQUENZA_NON_CONFIGURATA`).

* **Funzione di supporto**

  * **`script.fn_log_and_raise_error(...)`**
    Registra e solleva l’errore con il contesto della funzione e i dettagli del codice interno.

---

### Vantaggi operativi

* **Parametricità**
  Consente di modificare prefisso, separatore e lunghezza numerica senza toccare il codice della funzione.
* **Unicità garantita**
  L’uso della sequenza database (`nextval`) assicura incrementi atomici e codici unici anche in contesti concorrenti.
* **Controllo di configurazione**
  Se manca la riga di configurazione viene immediatamente segnalato un errore; se `usa_sequenza = FALSE` la funzione restituisce `NULL`, evitando generazioni spurie.
* **Estendibilità**
  Per nuovi tipi di codice, basta inserire in **`config.sistema_codici`** una nuova riga; la funzione li gestirà automaticamente.

---

> **“Questa funzione restituisce un codice conforme alle specifiche di `config.sistema_codici`. Se la configurazione non è presente o non è possibile determinare la sequenza, solleva un’eccezione descrittiva.”**
