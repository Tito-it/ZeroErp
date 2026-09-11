## 📘 Documentazione Funzione –  `dbops.fn_audit_log_once`

---

> 👀 **Vedi anche**     
>
Approdondimento tabelle:   
>
[`dbops.audit_log`](/dbzero/dbops/tabelle/audit_log)   
>
Approdondimento funzioni:   
>
[`dbops.fn_audit_begin`](/dbzero/dbops/funzioni/fn_audit_begin)   
> [dbops.fn_audit_end`](/dbzero/dbops/funzioni/fn_audit_end)   

---
### 🎯 Scopo Principale
(latest review 10-01-26)
La funzione **`fn_audit_log_once`** registra un singolo evento di audit senza richiedere una sessione completa (`fn_audit_begin`/`fn_audit_end`). È utile per eventi puntuali o messaggi informativi.


### 🔒 Privilegi — la porta dell'APPLICAZIONE (dal 2026-09-11)

È l'**unica** funzione di audit che `zeroerp_app` può eseguire: registra
l'evento intero in una volta, senza bisogno di riscrivere la riga dopo. La
coppia `fn_audit_begin` / `fn_audit_end` è riservata a chi possiede la
tabella, perché la chiusura è un `UPDATE` del registro.
Regola e motivazione: guida [Audit Logging](/guide/messaggi-audit), sezione
*Chi può scrivere*.

---

### Dettagli

* Inserisce direttamente un record in `audit_log`.
* Permette di indicare il livello (**INFO**, **WARN**, **ERROR**).
* Non necessita di un `audit_id` preesistente.

---

### Utilizzo tipico

* Trigger o funzioni che vogliono registrare eventi isolati.
* Automazioni leggere che non richiedono la gestione di una sessione completa.
* Segnalazione di anomalie minori o messaggi di servizio.

---

### Collegamento con `audit_log`

Ogni chiamata inserisce un record indipendente contenente:

* Timestamp.
* Utente che ha generato l’evento.
* Stato (INFO, WARN, ERROR).

---

### Esempio pratico

Durante la validazione di un dataset, una riga anomala ma non bloccante può essere registrata con `fn_audit_log_once` (stato **WARN**). In questo modo l’evento viene tracciato senza aprire un’intera sessione di audit.
