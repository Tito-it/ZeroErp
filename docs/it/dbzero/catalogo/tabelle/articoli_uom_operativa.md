{% include-markdown "it/dbzero/catalogo/manual/articoli_uom_operativa.md" %}
# 📚 Tabella `articoli_uom_operativa`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| uom_id | bigint | NO |  |
| is_base | boolean | NO | false |
| factor_to_base | numeric | NO | 1 |
| is_sell_uom | boolean | YES | false |
| is_purchase_uom | boolean | YES | false |
| is_logistic_uom | boolean | YES | false |
| qty_step | numeric | YES | 1 |
| rounding_mode | character varying | YES | 'HALF_UP'::character varying |
| max_decimals | integer | YES | 6 |
| forbid_fraction | boolean | YES | false |
| require_lot | boolean | YES | false |
| gtin | character varying | YES |  |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_artuomop_factor_pos |  |
| CHECK | ck_artuomop_forbid_fraction_rules |  |
| CHECK | ck_artuomop_max_decimals_range |  |
| CHECK | ck_artuomop_qty_step_pos |  |
| CHECK | ck_artuomop_rounding_mode |  |
| FOREIGN KEY | fk_artuomop_articolo | articolo_id |
| FOREIGN KEY | fk_artuomop_uom | uom_id |
| PRIMARY KEY | pk_articoli_uom_operativa | id |
| UNIQUE | uq_artuomop_articolo_uom | articolo_id, uom_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_artuomop_art_isbase | `CREATE INDEX ix_artuomop_art_isbase ON catalogo.articoli_uom_operativa USING btree (articolo_id, is_base)` |
| ix_artuomop_meta_gin | `CREATE INDEX ix_artuomop_meta_gin ON catalogo.articoli_uom_operativa USING gin (meta)` |
| pk_articoli_uom_operativa | `CREATE UNIQUE INDEX pk_articoli_uom_operativa ON catalogo.articoli_uom_operativa USING btree (id)` |
| uq_artuomop_articolo_uom | `CREATE UNIQUE INDEX uq_artuomop_articolo_uom ON catalogo.articoli_uom_operativa USING btree (articolo_id, uom_id)` |
| uqidx_artuomop_one_base | `CREATE UNIQUE INDEX uqidx_artuomop_one_base ON catalogo.articoli_uom_operativa USING btree (articolo_id) WHERE (is_base IS TRUE)` |

---
{% include-markdown "signature-core.md" %}
