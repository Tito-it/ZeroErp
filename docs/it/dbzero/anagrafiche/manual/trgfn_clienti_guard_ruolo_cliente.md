## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_clienti_guard_ruolo_cliente`

> 👀 **Vedi anche**

> Approfondimenti tabelle:  
>
[anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)   
>  [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) 

> Approfondimenti funzioni:   
>
[script.fn_guard_soggetto_ruolo ](/dbzero/script/funzioni/fn_guard_soggetto_ruolo ) 

La trigger function **`anagrafiche.trgfn_clienti_guard_ruolo_cliente()`** si attiva **BEFORE INSERT** e **BEFORE UPDATE** sulla tabella `anagrafiche.clienti`. Il suo scopo è garantire che, ogni volta che si crea o modifica il record del cliente, venga automaticamente gestita (verificata o creata) la corrispondente riga di relazione in `anagrafiche.soggetti_ruoli` con ruolo “cliente” (`codice_interno = 'GE'`).

---
### 🎯 Scopo Principale
(latest review 05-12-25)
- **Centralizzare l’assegnazione del ruolo “cliente”**  
  Delegare a `script.fn_guard_soggetto_ruolo ` la logica di inserimento o verifica del linking table, evitando duplicazioni di codice.

- **Mantenere coerenza referenziale**  
  Associare sempre correttamente il soggetto al ruolo di cliente, aggiornando `NEW.soggetto_ruolo_id` con l’ID valido, che sia preesistente o appena creato.

- **Semplificare i trigger client**  
  Qualunque operazione di INSERT o UPDATE su `anagrafiche.clienti` non deve preoccuparsi di controllare manualmente `soggetto_ruolo_id`; la trigger function ne gestisce la delega.

---

### Flusso Logico

1. **Chiamata automatica**  
   Attivata **BEFORE INSERT OR UPDATE** su `anagrafiche.clienti`.  

     p_cd_int_ruolo = 'GE' identifica il ruolo “cliente” in config.tipi_ruoli.

     La funzione verifica o crea il record in anagrafiche.soggetti_ruoli e restituisce l’ID.

### Utilizzo in DDL

Nel DDL di anagrafiche.clienti il trigger viene definito così:

CREATE OR REPLACE TRIGGER trg_clienti_guard_ruolo_cliente_ins_upd
  BEFORE INSERT OR UPDATE ON anagrafiche.clienti
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_clienti_guard_ruolo_cliente();

---
### Vantaggi Operativi

    Unica fonte di verità per l’assegnazione del ruolo
    Ogni modifica al cliente delega a una sola funzione centralizzata il compito di controllare/eseguire 
    l’inserimento del ruolo in linking table.

    Riduzione del codice boilerplate
    Non è necessario ripetere la logica di verifica/inserimento nei trigger o nelle procedure che 
    gestiscono anagrafiche.clienti.

    Coerenza e tracciabilità
    Grazie all’uso di script.fn_guard_soggetto_ruolo , ogni assegnazione di ruolo registra automaticamente 
    user_insert nel linking table e garantisce che soggetto_ruolo_id sia sempre valido.

    Flessibilità per ruoli futuri
    Il pattern può essere replicato in altre trigger function per tabelle analoghe 
    (es. anagrafiche.clienti, anagrafiche.fornitori), semplicemente cambiando il parametro p_cd_int_ruolo.

---
### 🚧 Nota di sviluppo
    Questa trigger function e la funzione generica fn_guard_soggetto_ruolo  costituiscono il 
    nucleo metodologico per la gestione dei ruoli in Zero ERP: saranno estese e replicate per ogni nuovo 
    tipo di ruolo oggetto di implementazione.