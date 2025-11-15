{% include-markdown "it/dbzero/config/manual/note_stili.md" %}
# 📚 Tabella `note_stili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | YES | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_cfg_note_stili_codice_interno_len |  |
| CHECK | chk_cfg_note_stili_codice_len |  |
| PRIMARY KEY | pk_config_note_stili | id |
| UNIQUE | uq_cfg_note_stili_codice | codice |
| UNIQUE | uq_cfg_note_stili_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_note_stili_attivo | `CREATE INDEX ix_cfg_note_stili_attivo ON config.note_stili USING btree (attivo)` |
| ix_cfg_note_stili_codice_interno_upper | `CREATE INDEX ix_cfg_note_stili_codice_interno_upper ON config.note_stili USING btree (upper((codice_interno)::text))` |
| ix_cfg_note_stili_codice_upper | `CREATE INDEX ix_cfg_note_stili_codice_upper ON config.note_stili USING btree (upper((codice)::text))` |
| ix_cfg_note_stili_descrizione_upper | `CREATE INDEX ix_cfg_note_stili_descrizione_upper ON config.note_stili USING btree (upper((descrizione)::text))` |
| pk_config_note_stili | `CREATE UNIQUE INDEX pk_config_note_stili ON config.note_stili USING btree (id)` |
| uq_cfg_note_stili_codice | `CREATE UNIQUE INDEX uq_cfg_note_stili_codice ON config.note_stili USING btree (codice)` |
| uq_cfg_note_stili_codice_interno | `CREATE UNIQUE INDEX uq_cfg_note_stili_codice_interno ON config.note_stili USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
