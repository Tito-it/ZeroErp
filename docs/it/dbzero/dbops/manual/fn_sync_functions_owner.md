## 📘 Documentazione Concettuale – Funzione `dbops.fn_sync_functions_owner`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.sec_functions_owner](/dbzero/dbops/tabelle/sec_functions_owner) — il registro che la funzione applica
>
> Approfondimento funzioni:
>
> * [dbops.fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore) — la domanda della guardia: la sessione è del migratore?
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — una delle funzioni che la sync tiene a `postgres`
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — la connessione del canale di log, anch'essa nel registro
>
> Guide:
>
> * [Linee guida SQL — 11.8 La postura più stretta di zeroerp_app](/linee-guida-sql#118-una-postura-piu-stretta-per-zeroerp_app-si-dichiara-nel-loop-dei-grant-non-in-un-revoke) — perché questa funzione si difende nel corpo e non con l'ACL

---

### 🎯 Scopo Principale

Allinea il proprietario di ogni funzione elencata in `dbops.sec_functions_owner` al ruolo
richiesto, con un `ALTER FUNCTION … OWNER TO`. Gira a ogni migrate e nella passata di provisioning
finale; la può eseguire solo il migratore o un superuser.

---

### Che cosa fa per ogni riga

* risolve la firma della riga in una funzione viva; se non la trova, avvisa e passa oltre;
* risolve il ruolo richiesto; se non esiste, avvisa e passa oltre;
* se il proprietario è già quello, non fa niente;
* altrimenti cambia il proprietario e lo dice con un avviso. Un cambio rifiutato (privilegi
  insufficienti o altro) diventa un avviso, non un errore.

La funzione non restituisce niente e non solleva per una riga: un registro con una voce rotta non
ferma il migrate. Il rovescio è che un cambio non riuscito resta solo negli avvisi; chi ha bisogno
del risultato lo verifica dopo, come fanno i changeSet che prendono una funzione in prestito.

---

### ⭐ È di `postgres`, e per questo è `SECURITY DEFINER`

Per cambiare il proprietario di una funzione di `postgres` bisogna essere `postgres`. La sync è
quindi una `SECURITY DEFINER` di `postgres`, col `search_path` fissato nella definizione (il
catalogo, `public`, `pg_temp`): un `CREATE OR REPLACE` che lo dimenticasse lo azzererebbe. È anche
lo strumento del **prestito**: un changeSet scrive il migratore come proprietario richiesto, lancia
la sync, sostituisce la funzione, rimette `postgres` e rilancia la sync.

---

### ⛔ Riservata al migratore, con una guardia nel corpo

Chi esegue la sync decide chi possiede le funzioni del canale di log. La prima riga del corpo
chiede a `dbops.fn_sessione_del_migratore` se la sessione è del migratore (membro del proprietario
dello schema `dbops`) o di un superuser; per chiunque altro, applicazione compresa, solleva `42501`.

* Il rifiuto è un `RAISE` nudo, fuori dal canale di log: quel canale è fra le funzioni che la sync
  protegge.
* ⚠️ Il chiamante si legge da `session_user`, il ruolo con cui la connessione è entrata: dentro una
  `SECURITY DEFINER` il ruolo corrente è il proprietario, e una guardia su di lui sarebbe sempre
  aperta. Limite dichiarato: una sessione aperta dal migratore che passa a un altro ruolo con
  `SET ROLE` resta del migratore. L'applicazione si collega come se stessa, quindi il caso non la
  riguarda.
* ⭐ `EXECUTE` a PUBLIC resta, per scelta. La difesa non sta nell'ACL: quella di una funzione di
  `postgres` la riscrive il loop dei grant e la rimappa ogni cambio di proprietario. Con la guardia
  nel corpo, poter chiamare la funzione non compra niente.

Il registro che la sync legge è in sola lettura per l'applicazione: le due difese insieme tolgono
entrambe le leve.

---

### Codici errore

* `42501` (privilegi insufficienti, SQLSTATE nudo, senza codice di catalogo) — la sessione non è
  del migratore né di un superuser.

---

### Test

* `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql` — come applicazione la sync è
  eseguibile per ACL (dichiarato) ma rifiutata dalla guardia, col suo messaggio, su un registro non
  vuoto; la guardia legge `session_user`.
* `db/pgtap/dbops/test-sec-functions-owner-migratore-passa-v1.sql` — come migratore la sync vive.
* `db/pgtap/dbops/test-security-definer-search-path-v1.sql` — nessuna `SECURITY DEFINER` senza
  `search_path`; le funzioni di `postgres`, sync compresa, hanno il loro.
* `db/pgtap/config/test-totp-disabilita-migratore-v1.sql` — dopo l'estrazione della domanda nel
  building block, il migratore passa ancora la guardia.

---

### Note di migrazione

* 2025-11-23 — nasce, col registro, dopo i fallimenti delle funzioni del canale di log rimaste senza
  i diritti per aprire `dblink`.
* 2026-09-12 — il `search_path` fissato nella definizione.
* 2026-09-26 — riservata al migratore con la guardia nel corpo
  (`brief-db-registro-owner-e-sync-riservati-al-migratore`).
* 2026-09-29 — la domanda passa in `dbops.fn_sessione_del_migratore`, perché la fa anche lo
  spegnimento del secondo fattore dal server (`brief-db-secondo-fattore-totp`).

---

{% include-markdown "signature-core.md" %}
