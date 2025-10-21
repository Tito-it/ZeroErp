# 📚 Tabella `lingue`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_iso | character varying | NO |  |
| descrizione | text | NO |  |
| descrizione_locale | text | NO |  |
| attiva | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_cfg_lingue_codice_iso_len |  |
| PRIMARY KEY | pk_config_lingue | id |
| UNIQUE | uq_cfg_lingue_codice_iso | codice_iso |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_lingue_attiva | `CREATE INDEX ix_cfg_lingue_attiva ON config.lingue USING btree (attiva)` |
| pk_config_lingue | `CREATE UNIQUE INDEX pk_config_lingue ON config.lingue USING btree (id)` |
| uq_cfg_lingue_codice_iso | `CREATE UNIQUE INDEX uq_cfg_lingue_codice_iso ON config.lingue USING btree (codice_iso)` |

---
{% include-markdown "signature-core.md" %}
