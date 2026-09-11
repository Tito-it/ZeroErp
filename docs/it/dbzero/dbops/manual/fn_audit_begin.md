## 📘 Documentazione Funzione –  `dbops.fn_audit_begin`

---
 
> 👀 **Vedi anche**     
>
Approdondimento tabelle:   
>
[`dbops.audit_log`](/dbzero/dbops/tabelle/audit_log)   
>
Approdondimento funzioni:   
>
[`dbops.fn_audit_end`](/dbzero/dbops/funzioni/fn_audit_end)   
> [`dbops.fn_audit_log_once`](/dbzero/dbops/funzioni/fn_audit_log_once)   

---
### 🎯 Scopo Principale
La funzione **`fn_audit_begin`** avvia una nuova sessione di auditing registrando un evento iniziale nella tabella `dbops.audit_log`. È utilizzata come punto di partenza per tracciare processi o automazioni che richiedono visibilità sull’intero ciclo di esecuzione.


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

* Inserisce un record in `audit_log` con stato **BEGIN**.
* Restituisce un identificativo (`audit_id`) che deve essere propagato alle operazioni successive.
* Può includere metadati addizionali come contesto applicativo, note o origine.

---

### Utilizzo tipico

1. Una procedura invoca `fn_audit_begin` all’inizio di un processo.
2. L’identificativo generato viene passato a step e funzioni successive.
3. Al termine, `fn_audit_end` chiude la sessione.

---

### Collegamento con `audit_log`

La tabella `audit_log` memorizza:

* Timestamp di inizio.
* Utente che ha avviato la sessione.
* Stato iniziale (**BEGIN**).

---

### Esempio pratico

Durante l’avvio di un batch di caricamento dati, `fn_audit_begin` registra l’inizio del processo e genera un ID di audit. Tutti gli step collegati scriveranno log riferiti a questo ID, garantendo tracciabilità completa.
