## 📘 Documentazione Concettuale – Trigger Function `script.trgfn_audit_data_user_generic`

(latest review 27-02-2026)

> **Aggiornamento 27-02-2026**: la funzione e` stata aggiornata per registrare il **vero utente**
> (JWT) sulle tabelle di audit, invece del ruolo DB della connessione (`CURRENT_USER`).
> Il trigger e` stato esteso da `BEFORE UPDATE` a `BEFORE INSERT OR UPDATE` per gestire
> anche il campo `user_insert`.

---

### 🎯 Scopo Principale

* **Audit automatico su INSERT e UPDATE**
  Assicura che ogni inserimento e modifica sia registrato con timestamp (`data_update`) e utente reale (`user_update` / `user_insert`).
* **Centralizzare la logica di audit**
  Un'unica trigger function per tutte le tabelle, evitando duplicazione di logica.
* **Tracciare l'utente reale (JWT)**
  Utilizza la GUC `app.jwt_user` impostata dal middleware Django per registrare
  l'utente che ha effettuato la chiamata API, non il ruolo DB della connessione.

---

### 🔍 Parametri e Contesto

* **Nessun parametro**: la funzione opera su `NEW`, modificando in-place i campi di audit.
* **Trigger associati**: va utilizzata con `BEFORE INSERT OR UPDATE` su qualsiasi tabella che possieda i campi:

  * `data_update TIMESTAMP WITH TIME ZONE`
  * `user_update TEXT` (o VARCHAR)
  * `user_insert TEXT` (o VARCHAR) — per il tracciamento utente su INSERT

Esempio di associazione DDL:

```sql
CREATE TRIGGER trg_<nome_tabella>_audit_data_user_upd
  BEFORE INSERT OR UPDATE ON <nome_schema>.<nome_tabella>
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_audit_data_user_generic();
```

---

### ⚙️ Comportamento

#### Su INSERT

1. **Imposta `user_insert`** con l'utente reale (JWT) o fallback a `CURRENT_USER`
2. **Imposta `data_update`** con il timestamp corrente
3. **Imposta `user_update`** con l'utente reale (JWT) o fallback a `CURRENT_USER`

#### Su UPDATE

1. **Imposta `data_update`** con il timestamp corrente
2. **Imposta `user_update`** con l'utente reale (JWT) o fallback a `CURRENT_USER`

#### Risoluzione utente

```plpgsql
COALESCE(
  NULLIF(current_setting('app.jwt_user', true), ''),
  CURRENT_USER
)
```

* **`current_setting('app.jwt_user', true)`**: legge la GUC `app.jwt_user` impostata dal middleware Django. Il secondo parametro `true` evita errori se la GUC non esiste (restituisce NULL).
* **`NULLIF(..., '')`**: gestisce il caso in cui la GUC sia impostata a stringa vuota.
* **Fallback `CURRENT_USER`**: usato quando la GUC non e` impostata (script, cron, psql, migrazione).

---

### 🔧 GUC `app.jwt_user`

La GUC viene impostata dal middleware Django sulla connessione PostgreSQL:

```python
cursor.execute("SELECT set_config('app.jwt_user', %s, true)", [str(request.user)])
```

* `set_config(..., true)` = ambito transazione, si resetta automaticamente alla fine della transazione.
* Se il middleware non e` attivo (es. script, cron), la GUC non esiste e il fallback a `CURRENT_USER` garantisce il funzionamento.

---

### 🔒 Valore di Ritorno

* **`trigger`**
  Restituisce il record `NEW` con i campi di audit aggiornati.

---

### 💡 Vantaggi Operativi

* **Uniformita`**
  Un'unica trigger function per tutte le tabelle, comportamento omogeneo.
* **Utente reale**
  Registra l'utente JWT che ha effettuato la chiamata API, non il ruolo DB generico.
* **Backward-compatible**
  Se la GUC `app.jwt_user` non e` impostata, il comportamento e` identico a prima (`CURRENT_USER`).
* **Sicurezza e tracciabilita`**
  Ogni inserimento e modifica viene marcato con data e utente reale, migliorando compliance e debugging.
* **Provisioning automatico**
  L'automazione `dbops.fn_run_automations_audit_update` crea il trigger `BEFORE INSERT OR UPDATE` automaticamente su tutte le tabelle con colonne di audit.

---

### 📋 Cronologia

| Data | Modifica |
|------|----------|
| 19-11-2025 | Rinominata da `trgfn_upd_audit_data_user_generic` a `trgfn_audit_data_user_generic` |
| 27-02-2026 | Aggiornata per usare JWT (`app.jwt_user`) con fallback `CURRENT_USER`. Estesa a `BEFORE INSERT OR UPDATE` per gestire `user_insert`. |
