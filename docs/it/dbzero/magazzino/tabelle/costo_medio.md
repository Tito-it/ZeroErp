# 📚 Tabella `costo_medio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| qta | numeric | NO | 0 |
| valore | numeric | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_costo_medio_magazzino | magazzino_id |
| PRIMARY KEY | pk_mag_costo_medio | id |
| UNIQUE | uq_mag_costo_medio_art_mag | articolo_id, magazzino_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_cmedio_articolo | `CREATE INDEX ix_mag_cmedio_articolo ON magazzino.costo_medio USING btree (articolo_id)` |
| ix_mag_cmedio_magazzino | `CREATE INDEX ix_mag_cmedio_magazzino ON magazzino.costo_medio USING btree (magazzino_id)` |
| pk_mag_costo_medio | `CREATE UNIQUE INDEX pk_mag_costo_medio ON magazzino.costo_medio USING btree (id)` |
| uq_mag_costo_medio_art_mag | `CREATE UNIQUE INDEX uq_mag_costo_medio_art_mag ON magazzino.costo_medio USING btree (articolo_id, magazzino_id)` |

---
{% include-markdown "signature-core.md" %}
