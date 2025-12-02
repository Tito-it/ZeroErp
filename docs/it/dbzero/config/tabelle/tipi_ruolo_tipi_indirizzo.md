# 📚 Tabella `tipi_ruolo_tipi_indirizzo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_ruolo_id | bigint | NO |  |
| tipo_indirizzo_id | bigint | NO |  |
| obbligatorio | boolean | NO | false |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| storicizza | boolean | NO | false |
| fallback_tipo_indirizzo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ruoli_tipi_indirizzo_validita |  |
| CHECK | chk_tipi_ruolo_tipi_indirizzo_fallback_not_self |  |
| FOREIGN KEY | fk_ruoli_tipi_indirizzo_tipo_indirizzo | tipo_indirizzo_id |
| FOREIGN KEY | fk_tipi_ruoli_tipi_indirizzo_ruolo | tipo_ruolo_id |
| FOREIGN KEY | fk_tipi_ruolo_tipi_indirizzo_fallback_tipo | fallback_tipo_indirizzo_id |
| FOREIGN KEY | fk_tipi_ruolo_tipi_indirizzo_tipo_ruolo | tipo_ruolo_id |
| PRIMARY KEY | pk_ruoli_tipi_indirizzo | id |
| UNIQUE | uq_tipi_ruolo_tipi_indirizzo_tipo_ruolo_tipo | tipo_ruolo_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_ruolo_tipi_indirizzo_tipo | `CREATE INDEX ix_tipi_ruolo_tipi_indirizzo_tipo ON config.tipi_ruolo_tipi_indirizzo USING btree (tipo_indirizzo_id)` |
| ix_tipi_ruolo_tipi_indirizzo_tipo_ruolo | `CREATE INDEX ix_tipi_ruolo_tipi_indirizzo_tipo_ruolo ON config.tipi_ruolo_tipi_indirizzo USING btree (tipo_ruolo_id)` |
| pk_ruoli_tipi_indirizzo | `CREATE UNIQUE INDEX pk_ruoli_tipi_indirizzo ON config.tipi_ruolo_tipi_indirizzo USING btree (id)` |
| uq_tipi_ruolo_tipi_indirizzo_tipo_ruolo_tipo | `CREATE UNIQUE INDEX uq_tipi_ruolo_tipi_indirizzo_tipo_ruolo_tipo ON config.tipi_ruolo_tipi_indirizzo USING btree (tipo_ruolo_id, tipo_indirizzo_id)` |

---
{% include-markdown "signature-core.md" %}
