## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_scrivi_profilo_accesso`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [config.fn_scrivi_profilo_accesso](/dbzero/config/funzioni/fn_scrivi_profilo_accesso) — il verbo che chiama
> * [dbops.fn_pgtap_entra_come_super_admin](/dbzero/dbops/funzioni/fn_pgtap_entra_come_super_admin) / [dbops.fn_pgtap_rimetti_contesto](/dbzero/dbops/funzioni/fn_pgtap_rimetti_contesto) — il contesto del SUPER_ADMIN
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i builder dell'accesso

---

### 🎯 Scopo Principale

In un pgTAP, scrive un profilo di accesso, con le sue aree e azioni, dal verbo vero [fn_scrivi_profilo_accesso](/dbzero/config/funzioni/fn_scrivi_profilo_accesso), chiamato da un SUPER_ADMIN di
fixture ([fn_pgtap_entra_come_super_admin](/dbzero/dbops/funzioni/fn_pgtap_entra_come_super_admin)). Il contesto
di prima torna, anche in errore. Argomenti e risultato sono quelli del verbo, e un suo rifiuto arriva al test
com'è: il builder prova il verbo, non lo aggira.

Le tabelle dei profili sono in sola lettura per l'applicazione: un test che ha bisogno di un profilo come fixture
usa questo builder, al posto di un `INSERT` diretto.
