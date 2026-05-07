# Brief Team DB — Estensione whitelist schemi in `provision_db_roles.sql`

**Data:** 2026-05-07
**Riferimento:** [`sviluppo-personalizzazioni-liste.md`](sviluppo-personalizzazioni-liste.md) §10.2-bis (DB-5)
**Branch:** `dev/db-tid` (provisioning script vive in `scripts/sql/`, non in `db/changelog/`)
**Priorita':** alta — bloccante per smoke test E5 e per Blocco F

---

## Sintomo

Backend Django solleva `ProgrammingError: permesso negato per lo schema ui` quando legge `ui.lista_definizione`. Riprodotto 2026-05-07 con query test via Django ORM dopo il completamento Blocchi A-D + seed E.

## Causa

[`scripts/sql/provision_db_roles.sql`](../../../../scripts/sql/provision_db_roles.sql) ha una whitelist hardcoded di schemi applicativi a cui concedere i grant runtime per `zeroerp_app`. La whitelist attuale e':

```text
public, script, dbops, config, anagrafiche, catalogo, vendite, acquisti,
magazzino, pagamenti, contabilita, storico
```

Mancano **`ui`** (Blocco A 2026-05-06), **`documenti`** (atterrato in altre tranche), **`pratiche`** (idem). Documenti e pratiche oggi funzionano probabilmente per fix mirati one-off; `ui` e' arrivato dopo e non ha avuto il fix → blocca runtime.

## Patch proposta

In `provision_db_roles.sql`, aggiungere `'documenti'`, `'pratiche'`, `'ui'` (in ordine alfabetico) a tutte le 5 whitelist `IN (...)` del file:

1. `GRANT USAGE ON SCHEMA ... TO :app_role` (~riga 46)
2. `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ... TO :app_role` (~riga 64)
3. `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ... TO :app_role` (~riga 82)
4. `GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ... TO :app_role` (~riga 100)
5. Tre `ALTER DEFAULT PRIVILEGES FOR ROLE :migrator_role IN SCHEMA ...` per TABLES / SEQUENCES / FUNCTIONS (~righe 121, 142, 163)

Ogni whitelist ha la sua copia: aggiungere le 3 voci a tutte e 5.

## Esecuzione

Lo script e' idempotente. Eseguire dal solito host con admin DB:

```bash
psql "host=$DB_HOST port=5432 dbname=zeroerp user=$ADMIN_DB_USER" \
  -v app_role=zeroerp_app \
  -v app_password='<PASSWORD_FOR_ZEROERP_APP>' \
  -v migrator_role=titodb \
  -f scripts/sql/provision_db_roles.sql
```

## Verifica

```bash
psql "host=$DB_HOST port=5432 dbname=zeroerp user=$ADMIN_DB_USER" \
  -v app_role=zeroerp_app \
  -f scripts/sql/check_db_role_access.sql
```

Atteso: nessun "permesso negato" per `ui`, `documenti`, `pratiche` nelle righe USAGE/SELECT.

Smoke check immediato lato backend (no restart Gunicorn richiesto, i grant sono per ruolo PG):

```bash
cd backend && set -a && source .env.systemd && set +a
.venv/bin/python -c "
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT count(*) FROM ui.lista_definizione')
    print('ui.lista_definizione count:', c.fetchone()[0])
"
```

## Cosa NON si chiede

- Nessuna modifica a DDL / migrations / dati.
- Nessun nuovo schema. La whitelist registra solo i grant runtime per gli schemi gia' esistenti.

## Risposta attesa

Confermare l'esecuzione dello script aggiornato + il superamento del check di accesso. A quel punto il backend agent puo' lanciare `./scripts/tests/smoke-test-ui-personalizzazioni-liste.sh` end-to-end e procedere con il Blocco F.
