## 📘 Documentazione Concettuale – Funzione `dbops.fn_sync_functions_owner()`

> 👀 **Vedi anche**
>
Approfondimenti collegati:   
>
Documento["Estensione PostgreSQL: dblink"](/postgresql/dblink) – Configurazione connessione tecnica    
>
Approfondimenti tabelle:   
>
[dbops.sec_functions_owner](/dbzero/dbops/tabelle/sec_functions_owner) – Policy owner funzioni sensibili    
>
Approfondimenti funzioni:    
>
[`dbops.fn_get_or_create_session_tx_id`](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) – Gestione session_tx_id   
> [`script.fn_ensure_logconn`](/dbzero/script/funzioni/fn_ensure_logconn) – Verifica connessione `dblink` di logging    

---

La funzione **`dbops.fn_sync_functions_owner()`** implementa il meccanismo di *hardening* per le **funzioni sensibili** di Zero ERP.

Legge la configurazione definita nella tabella `dbops.sec_functions_owner` e, per ciascuna funzione elencata, verifica che l’**owner effettivo coincida con quello richiesto** (tipicamente `postgres`). In caso di differenze, tenta di eseguire un `ALTER FUNCTION ... OWNER TO ...`, mantenendo così allineati i permessi rispetto alla policy di sicurezza.

Questa funzione nasce in risposta alle problematiche emerse durante la **riconfigurazione di `dblink`** e di altre funzioni tecniche (logging, gestione TX ID) che fallivano perché eseguite con owner/permessi non adeguati.

---
### 🎯 Scopo Principale
* **Applicare automaticamente la policy di sicurezza** definita in `dbops.sec_functions_owner`.
* **Rilevare e correggere** owner incoerenti di funzioni critiche.
* Rendere ripetibile e idempotente il processo di *hardening* dopo:

  * migrazioni Liquibase,
  * restore/clonazioni del database,
  * refactor o modifiche manuali non controllate.
* Separare chiaramente la **definizione della policy** (tabella) dalla **sua applicazione** (funzione).

> *"`dbops.fn_sync_functions_owner()` è il motore che traduce le regole di sicurezza dichiarate nella tabella in permessi effettivi sulle funzioni."*

---

### Firma e Comportamento

**Firma:**

```sql
SELECT dbops.fn_sync_functions_owner();
```

* **Schema:** `dbops`
* **Argomenti:** nessuno
* **Valore di ritorno:** `void` (esegue operazioni, non restituisce dati)
* **Sicurezza:** `SECURITY DEFINER`

Idealmente la funzione deve essere **possessa da `postgres`** (o comunque da un ruolo con privilegi elevati), così da poter eseguire `ALTER FUNCTION` anche su funzioni possedute da altri ruoli.

---

### Flusso Logico Operativo

A livello concettuale, la funzione esegue il seguente flusso per ogni riga di `dbops.sec_functions_owner`:

1. **Lettura configurazione**:

   * Per ogni record (`schema_name`, `function_name`, `arg_types`, `required_owner`), costruisce la *signature* completa della funzione.

2. **Risoluzione della funzione**:

   * Utilizza `to_regprocedure()` per individuare l’OID della funzione in `pg_proc`.
   * Se la funzione non esiste:

     * emette un `WARNING` e passa alla funzione successiva.

3. **Verifica owner attuale**:

   * Recupera l’owner corrente (`pg_get_userbyid(proowner)`).

4. **Verifica ruolo richiesto**:

   * Risolve `required_owner` in OID (`pg_roles.oid`).
   * Se il ruolo non esiste:

     * emette un `WARNING` e continua.

5. **Allineamento owner**:

   * Se l’owner corrente **coincide** con quello richiesto → non fa nulla.

   * Se è **diverso** → tenta un:

     ```sql
     ALTER FUNCTION schema_name.function_name(arg_types) OWNER TO required_owner;
     ```

   * In caso di successo, può emettere un `NOTICE` informativo.

6. **Gestione errori**:

   * `insufficient_privilege` → `WARNING` con dettaglio funzione/owner.
   * Altre eccezioni → `WARNING` con `SQLSTATE` e `SQLERRM`.

---

### Integrazione con Liquibase (Hardening)

La funzione è pensata per essere richiamata **automaticamente** a fine pipeline Liquibase, tramite un changeSet dedicato, spesso con `runAlways: true`.

Esempio concettuale:

```sql
SELECT dbops.fn_sync_functions_owner();
```

Questo consente di:

* Garantire che, dopo ogni `update`, l’owner delle funzioni sensibili sia riallineato alla policy.
* Applicare il controllo anche dopo restore/cloni, senza intervento manuale ripetuto.
* Far sì che in CI la funzione produca solo `WARNING` in caso di permessi insufficienti, senza bloccare la pipeline.

---

### Considerazioni di Sicurezza

* La funzione deve essere:

  * **`SECURITY DEFINER`**,
  * idealmente **owned by `postgres`** in ambienti definitivi (dev/prod veri).
* In CI o ambienti non-superuser:

  * l’`ALTER FUNCTION` può fallire per privilegio insufficiente;
  * la funzione gestisce il caso con `EXCEPTION WHEN insufficient_privilege` → nessun errore bloccante verso Liquibase.
* L’elenco delle funzioni che può modificare è **limitato** a quelle elencate in `dbops.sec_functions_owner`, che funge da policy esplicita e revisionabile.

#### ⛔ Riservata al migratore (dal 2026-09-26)

Chi esegue questa funzione decide **chi possiede** le funzioni sensibili: bastava
riscrivere una riga del registro e lanciarla, e le funzioni del canale di log
passavano a un altro proprietario. Per questo la funzione **si difende da sola**,
con una guardia in testa al corpo:

* **passa** chi possiede lo schema `dbops` (il ruolo che lancia le migrazioni, in
  ogni ambiente) e un superuser (la passata provision-post);
* **tutti gli altri**, applicazione compresa, ricevono un errore `42501`
  (*permesso negato*). L’errore non passa dal canale di log: quel canale è fra le
  funzioni che la sync protegge.

⚠️ **Il chiamante si legge da `session_user`, non da `current_user`.** Dentro una
`SECURITY DEFINER` `current_user` è il proprietario della funzione (`postgres`),
e una guardia su di lui sarebbe sempre aperta. **Limite dichiarato**:
`session_user` è il ruolo con cui la sessione si è **collegata**, e un `SET ROLE`
non lo cambia — una sessione aperta dal migratore che passa a `zeroerp_app`
supererebbe la guardia. L’applicazione si collega come `zeroerp_app`, quindi il
caso non la riguarda; PostgreSQL non offre un modo di leggere «chi ha chiamato»
una `SECURITY DEFINER` senza questo limite.

⭐ **`EXECUTE` a PUBLIC resta, per scelta.** La difesa non sta nei permessi della
funzione: essendo di `postgres`, quei permessi vengono riscritti a ogni passata
del loop dei grant e rimappati a ogni cambio di proprietario. Con la guardia nel
corpo, poter chiamare la funzione non compra niente.

Il registro che la funzione legge è in **sola lettura** per l’applicazione: vedi
[dbops.sec_functions_owner](/dbzero/dbops/tabelle/sec_functions_owner). I due
presidi pgTAP sono `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql`
(l’applicazione è respinta) e `test-sec-functions-owner-migratore-passa-v1.sql`
(il migratore passa ancora).

---

### Relazione con `dbops.sec_functions_owner`

La tabella `dbops.sec_functions_owner` rappresenta la **sorgente di verità** per la policy owner funzioni.
`dbops.fn_sync_functions_owner()` è l’**esecutore** di quella policy.

Relazione logica:

* Tabella → dichiara *quali* funzioni sono sensibili e *chi* deve possederle.
* Funzione → applica quella dichiarazione alle definizioni reali nel catalogo di sistema (`pg_proc`).

---

### Vantaggi Operativi

* **Riduzione errori manuali**: non è necessario ricordarsi ogni volta quali funzioni devono essere owner `postgres`.
* **Recupero post-restore/clone**: eventuali cambiamenti di owner introdotti da procedure di dump/restore vengono corretti automaticamente.
* **Governance chiara**: la combinazione tabella + funzione offre un punto unico dove leggere e applicare le regole di sicurezza sulle funzioni.
* **Compatibilità CI**: la funzione è progettata per non interrompere le pipeline, pur segnalando problemi di permessi.

---

> *"Standardizzare la gestione degli owner delle funzioni sensibili permette di mantenere nel tempo un ambiente robusto, ripetibile e coerente con le politiche di sicurezza di Zero ERP."*

---

{% include-markdown "signature-core.md" %}
