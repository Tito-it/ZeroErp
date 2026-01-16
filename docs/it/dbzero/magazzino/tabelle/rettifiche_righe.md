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
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| ubicazione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_mag_rettifiche_qta_non_zero |  |
| FOREIGN KEY | fk_mag_rettifiche_righe_articolo | articolo_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_testata | rettifica_id |
| FOREIGN KEY | fk_mag_rettifiche_righe_ubicazione | ubicazione_id |
| PRIMARY KEY | pk_mag_rettifiche_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_rettifiche_righe_articolo_id | `CREATE INDEX ix_magazzino_rettifiche_righe_articolo_id ON magazzino.rettifiche_righe USING btree (articolo_id)` |
| ix_magazzino_rettifiche_righe_ubicazione_id | `CREATE INDEX ix_magazzino_rettifiche_righe_ubicazione_id ON magazzino.rettifiche_righe USING btree (ubicazione_id)` |
| pk_mag_rettifiche_righe | `CREATE UNIQUE INDEX pk_mag_rettifiche_righe ON magazzino.rettifiche_righe USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
