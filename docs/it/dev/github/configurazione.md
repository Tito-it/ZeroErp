# 📘 Documentazione Configurazione GitHub — ZeroERP

## Struttura finale delle cartelle

La repository **ZeroErp** su GitHub ha la seguente organizzazione logica:

```
ZeroErp/
├── db/                  # Migrazioni Liquibase (gestite da DBDEV)
├── docs/                # Documentazione MkDocs
├── scripts/             # Script di supporto
├── requirements/        # Requirements Python
│   ├── backbase.txt     # Requisiti base runtime Django backend
│   └── backdev.txt      # Requisiti sviluppo (lint, test, mkdocs, ecc.)
├── backend/             # Server Django backend-dev
│   ├── manage.py
│   ├── zeroerp_backend/ # Moduli Django
│   ├── static/
│   ├── media/
│   └── .venv/           # Virtualenv locale (escluso da Git)
└── .github/
    └── workflows/
        ├── ci.yml        # CI principale (Liquibase + Docs)
        └── ci-validate.yml # CI validate (Liquibase + Django backend)
```

---

## Workflow CI

### `ci.yml` (DBDEV)

* Lanciato da **DBDEV** quando fai push su `Tito-dev`.
* Applica le migrazioni Liquibase.
* Genera documentazione.
* Build immagine Docker.

### `ci-validate.yml` (Backend)

* Lanciato sempre su `Tito-dev` quando tocchi `backend/` o `requirements/`.
* Crea DB effimero PostgreSQL con PostGIS.
* Applica migrazioni Liquibase.
* Installa requirements Django (`backbase.txt`).
* Lancia `python manage.py migrate` per creare lo schema Django.

---

## Punti critici corretti

1. **Nomi delle cartelle**:

   * Usa sempre `ZeroErp` con maiuscole coerenti (anche nei `settings.py`).
   * `backend/` contiene il progetto Django con `manage.py`.

2. **Requirements**:

   * `backbase.txt`: runtime Django.
   * `backdev.txt`: strumenti dev (opzionale).

3. **CI separate**:

   * DB gestito solo da Liquibase (DBDEV).
   * Django backend usa `migrate` solo per schema `django`.

4. **.gitignore** aggiornato per backend:

```gitignore
# Virtualenv backend
/backend/.venv/

# Config locali VS Code
/backend/.vscode/

# Database SQLite (solo dev)
/backend/db.sqlite3

# File statici/media generati
/backend/static/
/backend/media/

# File compilati Python
__pycache__/
*.pyc

# Log
*.log

# Ambiente/secret locali
/backend/env.sh
```

---

✅ Con questa configurazione:

* **DBDEV** continua a gestire tutto via Liquibase.
* **Backend-dev** gestisce solo lo schema `django`.
* **GitHub Actions** validano entrambe le parti senza conflitti.
