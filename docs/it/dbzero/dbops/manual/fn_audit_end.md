## 📘 Documentazione Funzione –  `dbops.fn_audit_end`

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
> [dbops.fn_audit_log_once`](/dbzero/dbops/funzioni/fn_audit_log_once)   

---
### 🎯 Scopo Principale
La funzione **`fn_audit_end`** chiude una sessione di auditing avviata da `fn_audit_begin`, registrando lo stato finale nel record corrispondente in `dbops.audit_log`.


### 🔒 Privilegi — porta RISERVATA (dal 2026-09-11)

La modalità sessione (`fn_audit_begin` → `fn_audit_end`) chiude la riga con un
`UPDATE` del registro. Per questo la coppia **non è eseguibile da `zeroerp_app`
né da `PUBLIC`**: la eseguono chi possiede la tabella (il migratore, i job di
manutenzione) e i ruoli che il provisioning autorizza in modo esplicito.
L'applicazione scrive l'audit con la sola `fn_audit_log_once`.
La postura è dichiarata nel loop dei grant `90_end/ci_apply/20260205-41` e
presidiata da `db/pgtap/dbops/test-registri-append-only-postura-v1.sql`.
Motivazione e regola: guida [Audit Logging](/guide/messaggi-audit), sezione
*Chi può scrivere*.

---

### Dettagli

* Aggiorna il record con `audit_id` associato.
* Registra il **timestamp di fine** e l’esito dell’operazione (**END**, **SUCCESS**, **ERROR**).
* Consente di aggiungere messaggi riepilogativi o note finali.

---

### Utilizzo tipico

1. Una procedura complessa apre la sessione con `fn_audit_begin`.
2. Durante l’esecuzione, step ed errori vengono loggati.
3. Alla fine, `fn_audit_end` marca la chiusura e l’esito finale.

---

### Collegamento con `audit_log`

La tabella `audit_log` conterrà:

* Timestamp di chiusura.
* Utente che ha chiuso la sessione.
* Stato conclusivo (successo, errore, interruzione).

---

### Esempio pratico

In un processo di migrazione dati:

* `fn_audit_begin` apre la sessione.
* Vari step intermedi registrano log.
* `fn_audit_end` conclude, segnando se la migrazione è stata completata correttamente o meno.
