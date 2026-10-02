## 📘 Documentazione Concettuale – Funzione `script.fn_credenziali()`

> 👀 **Vedi anche**
>
> [script.fn_get_auth_user_stato](/dbzero/script/funzioni/fn_get_auth_user_stato)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-A2)

**L'elenco di tutte le credenziali** (`django.auth_user`), anche spente e **senza alcuna
veste**: `auth_user_id`, `username`, `email`, `nome`, `cognome` (le stringhe vuote di Django
rese `NULL`), `is_active`, `last_login`.

⭐ **Perché una funzione.** Le credenziali senza veste non stanno in nessuna tabella del
database: l'unica sorgente che le elenca è Django. Una **vista** però non può nominare
`django.*` — si risolve alla `CREATE`, e le tabelle di Django le crea `manage.py migrate`
dopo Liquibase — mentre una funzione `plpgsql` si risolve alla prima esecuzione. Le viste
dell'area «Accessi» passano da qui. È la gemella «per elenco» di
[fn_get_auth_user_stato](/dbzero/script/funzioni/fn_get_auth_user_stato), che risponde per
un id.

Niente password né flag di Django che il database non governa.
