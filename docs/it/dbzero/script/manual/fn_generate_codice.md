## 📘 Documentazione Funzione – `script.fn_generate_codice(tipo TEXT)`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)      
>
> Approfondimento funzioni :    
> - [script.fn_get_messaggio](/dbzero/script/funzioni/fn_get_messaggio)    


La funzione **`script.fn_generate_codice(tipo TEXT)`** genera in modo parametrico un nuovo codice alfanumerico per uno specifico “tipo” (es. `ORDINE`, `CLIENTE`, `FATTURA`), basandosi sui parametri definiti nella tabella **`config.sistema_codici`**. Se la configurazione per quel tipo non esiste o è disattivata, viene sollevata un’eccezione.

---

### 🎯 Scopo Principale

* **Generazione di codici configurabili**
  Costruisce un codice concatenando un **prefisso**, un **separatore** e una **parte numerica** formattata, letti da **`config.sistema_codici`** in base al `codice_tipo` passato in input.

* **Unicità tramite sequenza**
  Invoca la sequenza database indicata in `nome_sequenza` per ottenere un valore numerico progressivo, garantendo codici unici e ordinati.

* **Verifica configurazione**
  Se la riga corrispondente a `codice_tipo = tipo` non esiste o `attivo = FALSE`, o se `nome_sequenza` è `NULL`, la funzione solleva un’eccezione con messaggio di errore.

---

### 📥 Parametri di input

| Nome   | Tipo   | Descrizione                                                                                              |
| ------ | ------ | -------------------------------------------------------------------------------------------------------- |
| `tipo` | `TEXT` | Identificativo del `codice_tipo` nella tabella `config.sistema_codici`. Esempi: `"ORDINE"`, `"CLIENTE"`. |

---

### 📤 Valore di ritorno

| Tipo restituito | Descrizione                                                                            |
| --------------- | -------------------------------------------------------------------------------------- |
| `TEXT`          | Stringa del codice generato, formata come `<prefisso><separatore><numero_formattato>`. |

```
               | Esempi: `ORD-000123`, `CL_000045`.                                                                                 |
```

---

### 🔍 Logica interna

1. **Lettura dei parametri**

   ```plpgsql
   SELECT prefisso, separatore, lunghezza_numero, nome_sequenza
     INTO prefix, sep, len, seq_name
     FROM config.sistema_codici
    WHERE codice_tipo = tipo
      AND attivo = TRUE;
   ```

   * Recupera da **`config.sistema_codici`** i valori di:

     * `prefisso` (testo da anteporre)
     * `separatore` (stringa di separazione)
     * `lunghezza_numero` (numero di cifre per la parte numerica)
     * `nome_sequenza` (nome della sequenza database)
   * Se non trova alcuna riga attiva per quel tipo, `seq_name` sarà `NULL`.

2. **Generazione del numero tramite sequenza**

   ```plpgsql
   IF seq_name IS NOT NULL THEN
     EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
     risultato := prefix || sep || lpad(seq_val::TEXT, len, '0');
     RETURN risultato;
   ELSE
     RAISE EXCEPTION '%',
       script.fn_get_messaggio('SEQUENZA_NON_CONFIGURATA', tipo);
   END IF;
   ```

   * Se `nome_sequenza` è valorizzato:

     1. Esegue dinamicamente `SELECT nextval('nome_sequenza')` per ottenere il prossimo valore numerico (`seq_val`).
     2. Converte `seq_val` in testo e lo riempie a sinistra con zeri fino a raggiungere la lunghezza `len`.
     3. Concatena `prefisso`, `separatore` e `numero_formattato`, restituendo il risultato.
   * Altrimenti:

     * Solleva un’eccezione con il messaggio da `script.fn_get_messaggio('SEQUENZA_NON_CONFIGURATA', tipo)`.

---

### 🚨 Possibili eccezioni

* **SEQUENZA\_NON\_CONFIGURATA**
  Viene sollevata quando:

  * Non esiste un record in **`config.sistema_codici`** per `codice_tipo = tipo` con `attivo = TRUE`.
  * Il campo `nome_sequenza` è `NULL` (anche se la riga esiste e `attivo = TRUE`).

  Il messaggio di errore è generato da:

  ```plpgsql
  script.fn_get_messaggio('SEQUENZA_NON_CONFIGURATA', tipo)
  ```

---

### 🔗 Dipendenze

* **Tabella di configurazione**

  * **`config.sistema_codici`** deve contenere una riga per ciascun `codice_tipo` con almeno:

    * `prefisso`: stringa testuale (es. `"ORD-"`).
    * `separatore`: carattere o stringa (es. `"-"`).
    * `lunghezza_numero`: numero intero (es. `6`).
    * `nome_sequenza`: nome di una sequenza SQL esistente (es. `"seq_ordine"`).
    * `attivo = TRUE`

* **Sequenza database**

  * La sequenza indicata in `nome_sequenza` deve esistere, ad esempio:

    ```sql
    CREATE SEQUENCE seq_ordine;
    ```

* **Funzione di supporto**

  * **`script.fn_get_messaggio(codice_errore TEXT, elemento TEXT)`**
    Restituisce il testo del messaggio di errore associato al codice di errore e all’elemento specificato.

---

### 💡 Vantaggi operativi

* **Parametricità**
  Consente di modificare prefisso, separatore e lunghezza numerica senza toccare il codice della funzione.
* **Unicità garantita**
  L’uso della sequenza database (`nextval`) assicura incrementi atomici e codici unici anche in contesti concorrenti.
* **Controllo di configurazione**
  Se `attivo = FALSE` o manca la riga di configurazione, viene immediatamente segnalato un errore, evitando generazioni spurie.
* **Estendibilità**
  Per nuovi tipi di codice, basta inserire in **`config.sistema_codici`** una nuova riga; la funzione li gestirà automaticamente.

---

> 🧠 **“Questa funzione restituisce un codice conforme alle specifiche di `config.sistema_codici`. Se la configurazione non è presente o è disattivata, solleva un’eccezione descrittiva.”**