## 📘 Documentazione Concettuale – Funzione `script.fn_check_ins_soggetto_ruolo`

> 👀 **Vedi anche**

>  Approfondimenti tabelle:   
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)  

La funzione **`script.fn_check_ins_soggetto_ruolo(p_soggetto_id, p_soggetto_ruolo_id, p_cd_int_ruolo)`** centralizza e semplifica la gestione della relazione tra un **soggetto** e il suo **ruolo**. Garantisce che, ogni volta che si assegna un ruolo a un soggetto, la tabella `anagrafiche.soggetti_ruoli` sia mantenuta correttamente e senza duplicati.

---

### 🎯 Scopo Principale

- **Verifica esistenza**  
  Controlla se esiste già un’associazione tra il soggetto e il codice interno del ruolo in `anagrafiche.soggetti_ruoli`.


- **Ritorno dell’ID**  
  Restituisce sempre l’ID valido della relazione soggetto–ruolo, sia esso appena creato o già esistente.

- **Centralizzazione della logica**  
  Evita duplicazioni di codice nei trigger o procedure: ogni assegnazione di ruolo utilizza questa funzione.

---

### 🔍 Parametri di Input

| Nome                  | Tipo      | Descrizione
|-----------------------|-----------|---------------------------------------------------------------------------|
| `p_soggetto_id`       | `UUID`    | ID del soggetto in `anagrafiche.oggetti` ---> Opzionale.                                                  |
| `p_soggetto_ruolo_id` | `INTEGER` | ID esistente della relazione in `anagrafiche.soggetti_ruoli`; se `NULL` o 0`,
                                      verrà      creato un nuovo record. 
| `p_cd_int_ruolo`      | `VARCHAR` | Codice interno del ruolo (`codice_interno` in `config.tipi_ruoli`) da associare al 
                                      soggetto.  

---

### ⚙️ Flusso Logico

1. **Recupero ID ruolo**  
   Cerca in `config.tipi_ruoli` il record con `codice_interno = p_cd_int_ruolo`. Se non trovato, solleva eccezione `E_COD_INT_RUOLO`.


2. **Verifica esistenza**  
   Altrimenti:
   - Controlla che esista un record in `anagrafiche.soggetti_ruoli` con:
     - `id = p_soggetto_ruolo_id`
     - `soggetto_id = p_soggetto_id`
     - `ruolo_id = <id recuperato>`
   - Se non esiste, solleva eccezione `E_SOGGETTI_RUOLI`.
   - Se esiste, restituisce `p_soggetto_ruolo_id`.

---

### 🔒 Error Handling

- **`E_COD_INT_RUOLO`**  
  Ruolo con codice interno `p_cd_int_ruolo` non trovato in `config.tipi_ruoli`.

- **`E_SOGGETTI_RUOLI`**  
  Record in `anagrafiche.soggetti_ruoli` con ID, soggetto e ruolo specificati non esiste.


---

### 🔗 Integrazione con Trigger

Utilizzare all’interno di trigger `BEFORE INSERT` o `BEFORE UPDATE` sulle tabelle di assegnazione ruoli:

```plpgsql
NEW.soggetto_ruolo_id := script.fn_check_ins_soggetto_ruolo(
  NULL,
  NEW.soggetto_ruolo_id,
  'CL'            -- o altro codice interno di ruolo
);
```

---

###  💡 Vantaggi Operativi

 -    Unica fonte di verità
       Tutti i controlli e inserimenti di relazioni soggetto–ruolo passano da un unico punto, migliorando coerenza e manutenzione.

 -   Riduzione di duplicazioni
       Evita boilerplate di verifica/inserimento in più trigger o procedure.

 -   Audit automatico
      Ogni inserimento registra user_insert = current_user, facilitando tracciabilità e debugging.


### 🚧 Nota di sviluppo
    Questa  la funzione generica costituisce il nucleo metodologico per la gestione dei ruoli in Zero ERP: sarà estese e replicate per ogni nuovo tipo di ruolo oggetto di implementazione.

---



Versione aggiornata il 21/11/2025. Da completare.