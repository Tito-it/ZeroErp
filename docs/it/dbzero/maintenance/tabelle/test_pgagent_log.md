{% include-markdown "it/dbzero/maintenance/manual/test_pgagent_log.md" %}
# 📚 Tabella `test_pgagent_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| fired_at | timestamp with time zone | NO | now() |
| jobname | text | NO |  |
| status | integer | NO |  |
| message | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | test_pgagent_log_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| test_pgagent_log_pkey | `CREATE UNIQUE INDEX test_pgagent_log_pkey ON maintenance.test_pgagent_log USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
