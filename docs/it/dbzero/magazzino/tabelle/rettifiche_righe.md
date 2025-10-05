# 📚 Tabella `rettifiche_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| rettifica_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| qta_delta | numeric | NO |  |
| lotto | character varying | YES |  |
| seriale | character varying | YES |  |
| motivo | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_rettifiche_qta_non_zero |  |
| FOREIGN KEY | fk_mag_rettifiche_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_testata | rettifica_id |
| PRIMARY KEY | pk_mag_rettifiche_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_rettifiche_r_articolo | `CREATE INDEX ix_mag_rettifiche_r_articolo ON magazzino.rettifiche_righe USING btree (articolo_id)` |
| ix_mag_rettifiche_r_lotto_upper | `CREATE INDEX ix_mag_rettifiche_r_lotto_upper ON magazzino.rettifiche_righe USING btree (upper((lotto)::text))` |
| ix_mag_rettifiche_r_seriale_upper | `CREATE INDEX ix_mag_rettifiche_r_seriale_upper ON magazzino.rettifiche_righe USING btree (upper((seriale)::text))` |
| pk_mag_rettifiche_righe | `CREATE UNIQUE INDEX pk_mag_rettifiche_righe ON magazzino.rettifiche_righe USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
