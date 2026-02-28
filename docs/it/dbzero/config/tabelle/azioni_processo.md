{% include-markdown "it/dbzero/config/manual/azioni_processo.md" %}
# 📚 Tabella `azioni_processo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| area_id | integer | NO |  |
| permission_codename | character varying | NO |  |
| descrizione | character varying | NO |  |
| pericolosa | boolean | NO | false |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_azioni_processo_aree_funzionali | area_id |
| PRIMARY KEY | pk_azioni_processo | id |
| UNIQUE | uq_azioni_processo_permission_codename | permission_codename |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_azioni_processo_area_id | `CREATE INDEX ix_azioni_processo_area_id ON config.azioni_processo USING btree (area_id)` |
| pk_azioni_processo | `CREATE UNIQUE INDEX pk_azioni_processo ON config.azioni_processo USING btree (id)` |
| uq_azioni_processo_permission_codename | `CREATE UNIQUE INDEX uq_azioni_processo_permission_codename ON config.azioni_processo USING btree (permission_codename)` |

---
{% include-markdown "signature-core.md" %}
