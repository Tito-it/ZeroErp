# 📘 Estensione PostgreSQL: **pgcrypto**

> 👀 **Vedi anche**
>
> * Schema utilità: **maintenance**
> * Estensioni correlate: [`dblink`](/postgresql/dblink)
> * Funzioni di servizio: `maintenance.run_and_log(...)`

`pgcrypto` fornisce primitive crittografiche direttamente in PostgreSQL: **hash**, **HMAC**, **UUID random**, **byte casuali**, **cifratura PGP simmetrica/asimmetrica**, e **hash sicuri per password**.

---

## 🎯 Scopi principali

* Generare **UUID** e **byte casuali** crittograficamente sicuri.
* Calcolare **digest** (SHA‑256, SHA‑512, …) e **HMAC**.
* Cifrare/decifrare dati con **PGP simmetrica/asimmetrica**.
* Gestire **password** con `crypt()`/`gen_salt()` (bcrypt).

---

## ⚙️ Installazione

> Da eseguire **per ogni database** dove serve usare le funzioni (es.: `zeroerp`).

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- crea in schema "public" (default)
-- oppure, se vuoi collocarla in uno schema dedicato
-- CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA public;
```

> In CI/Liquibase crea l’estensione **prima** di tabelle/funzioni che la usano.

### Changeset Liquibase (esempio)

```yaml
databaseChangeLog:
  - changeSet:
      id: 20250810-01-ext-pgcrypto
      author: mctit
      changes:
        - sql:
            stripComments: true
            splitStatements: false
            sql: |
              CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

---

## 🧰 Funzioni più usate

###  Random

```sql

SELECT gen_random_bytes(32);             -- bytea
```

### Digest / HMAC

```sql
-- SHA-256 in esadecimale
SELECT encode(digest('hello','sha256'),'hex');

-- HMAC-SHA256 (chiave app):
SELECT encode(hmac('payload', current_setting('app.crypto.key', true), 'sha256'),'hex');
```

### Password hashing (bcrypt)

> **Non** usare MD5 per password. Usa `crypt()` + `gen_salt('bf')`.

```sql
-- Creazione
INSERT INTO app.users(username, password_hash)
VALUES ($1, crypt($2, gen_salt('bf')));

-- Verifica
SELECT 1
FROM app.users
WHERE username = $1
  AND password_hash = crypt($2, password_hash);
```

### Cifratura PGP simmetrica

```sql
-- Cifra testo con passphrase (meglio leggere da GUC)
INSERT INTO secret_docs(content_enc)
VALUES (pgp_sym_encrypt('testo chiaro', current_setting('app.crypto.pass', true)));

-- Decifra
SELECT pgp_sym_decrypt(content_enc, current_setting('app.crypto.pass', true))
FROM secret_docs
WHERE id = $1;
```

### Cifratura PGP asimmetrica (pub/priv)

```sql
-- Cifra con chiave pubblica (armored)
SELECT pgp_pub_encrypt('payload', dearmor(pubkey_text)) FROM keyring WHERE id=$1;

-- Decifra con chiave privata + passphrase
SELECT pgp_pub_decrypt(payload_enc, dearmor(privkey_text), 'passphrase') FROM inbox WHERE id=$1;
```

> Suggerito: conservare **solo** chiavi pubbliche nel DB; chiavi private protette fuori dal DB o custodite con policy rigide.

---

## 🧱 Pattern utili

### Colonna UUID di default

```sql
ALTER TABLE app.orders
  ADD COLUMN id uuid PRIMARY KEY DEFAULT uuidv7();
```

### Indice su digest (ricerca rapida per hash)

```sql
ALTER TABLE app.events ADD COLUMN payload_sha256 bytea;
UPDATE app.events SET payload_sha256 = digest(payload::text,'sha256');
CREATE INDEX ON app.events (payload_sha256);
```

### Logging robusto (con `maintenance.run_and_log`)

```sql
CALL maintenance.run_and_log(
  p_jobname  := 'rebuild_materialized',
  p_stepname := 'refresh_view_x',
  p_sql      := 'REFRESH MATERIALIZED VIEW CONCURRENTLY app.view_x;',
  p_lock_key := hashtextextended('refresh_view_x', 0)
);
```

---

## 🔒 Buone pratiche di sicurezza

* **Password**: usa `crypt()` + `gen_salt('bf')` (bcrypt). Evita `md5()`/`sha1()` per password.
* **Chiavi/Passphrase**: non hardcodare. Leggile da **GUC** applicativi:

  ```sql
  ALTER DATABASE zeroerp SET app.crypto.pass = '...';
  ALTER DATABASE zeroerp SET app.crypto.key  = '...';
  -- poi current_setting('app.crypto.pass', true)
  ```

  Meglio ancora: impostare a runtime (sessione) via application server.
* **Rotazione**: prevedi la rotazione passphrase/chiavi (versiona i segreti e i record cifrati, es. colonna `key_version`).
* **Least privilege**: concedi `EXECUTE` solo alle funzioni necessarie e ai ruoli che ne hanno bisogno.
* **Mascheramento**: i campi `bytea` cifrati non vanno mostrati in log; usa viste che omettono i dati sensibili.

---

## 🏎️ Performance & tipi

* `digest()`/`hmac()` sono CPU‑bound: valuta **index su colonne hash** e batch update.
* Per archiviazione hash **testuale**, usa `encode(...,'hex')` → `text`/`varchar(64)` (SHA‑256) se serve leggibilità; altrimenti lascia `bytea`.
* PGP aggiunge overhead (header, salt, compressione opzionale): pianifica dimensioni e I/O.

---

## 🐞 Troubleshooting

* `function ... does not exist` → estensione non creata nel **database corrente**.
* `ERROR: Wrong key or corrupt data` → passphrase/chiave errata o dato danneggiato.
* Output incomprensibile → campi PGP sono `bytea`: usa `dearmor(...)`/`armor(...)` o `encode(...,'hex')` per debug.
* In Liquibase: usa `splitStatements:false` per definizioni complesse; evita apici tipografici.

---

## 🧪 CI (Ubuntu/GitHub Actions)

Esegui il changeset **prima** delle migrazioni che richiedono `pgcrypto`:

```yaml
- name: Create pgcrypto extension
  run: |
    export PGPASSWORD=secret
    psql -h localhost -p 5432 -U zeroerp -d zeroerp -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
```

---

## ✅ Checklist rapida

* [ ] `CREATE EXTENSION pgcrypto;` nel DB target
* [ ] Password -> `crypt()` + `gen_salt('bf')`
* [ ] UUID -> `uuidv7()`
* [ ] Chiavi/Passphrase via **GUC** o segreti applicativi
* [ ] Indici su hash se usati per ricerca
* [ ] Liquibase: changeset dedicato e ordinato prima dei consumatori

---

> 🧠 **Regola d’oro**: usa `pgcrypto` per *primitive* (hash/HMAC/UUID/random) e **PGP** per cifratura applicativa; gestisci segreti fuori dal codice SQL e versiona solo la struttura (non le chiavi).

---
{% include-markdown "signature-core.md" %}
