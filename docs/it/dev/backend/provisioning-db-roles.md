# Provisioning ruoli DB (runtime + migrator)

## Scopo
Definire un processo unico e ripetibile per configurare gli utenti DB in dev/stage/prod senza dipendere da utenti personali.

## Ruoli standard
- `zeroerp_app`: utente runtime usato da Django (`DB_USER`).
- `titodb` (o altro migrator): utente CI/deploy che applica migration e crea oggetti DB.

`zeroerp_app` **non** e` un utente Django (`auth_user`): e` solo un ruolo PostgreSQL.

## Script disponibili
- Provisioning idempotente: `scripts/sql/provision_db_roles.sql`
- Verifica rapida permessi: `scripts/sql/check_db_role_access.sql`

## Esecuzione provisioning (admin DB)
Eseguire da host che raggiunge PostgreSQL con un utente amministrativo.

```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v app_role=zeroerp_app \
  -v app_password='<PASSWORD_FOR_ZEROERP_APP>' \
  -v migrator_role=titodb \
  -f scripts/sql/provision_db_roles.sql
```

## Verifica accessi
```bash
psql "host=<DB_HOST> port=5432 dbname=zeroerp user=<ADMIN_DB_USER>" \
  -v app_role=zeroerp_app \
  -f scripts/sql/check_db_role_access.sql
```

## Configurazione Django
In `backend/env.sh` e `backend/.env.systemd` usare:

```bash
DB_NAME=zeroerp
DB_USER=zeroerp_app
DB_PASSWORD=<PASSWORD_FOR_ZEROERP_APP>
DB_HOST=<DB_HOST>
DB_PORT=5432
```

Dopo modifiche variabili:
```bash
sudo systemctl restart zeroerp-gunicorn
```

## Note operative
- Le `ALTER DEFAULT PRIVILEGES` vengono applicate per il ruolo migrator (`titodb`) cosi` gli oggetti futuri ereditano i grant runtime.
- In caso di nuovo schema applicativo, aggiornare la whitelist schema in `scripts/sql/provision_db_roles.sql`.
