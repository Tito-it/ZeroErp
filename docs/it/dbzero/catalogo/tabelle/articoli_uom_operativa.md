{% include-markdown "it/dbzero/catalogo/manual/articoli_uom_operativa.md" %}
# 📚 Tabella `articoli_uom_operativa`

> 📝 **Descrizione**
>
> Mappa le UoM operative ammesse per ciascun articolo e il fattore di conversione verso la UoM base (stock).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| uom_id | bigint | NO |  |
| is_base | boolean | NO | false |
| factor_to_base | numeric(18,6) | NO | 1 |
| is_sell_uom | boolean | YES | false |
| is_purchase_uom | boolean | YES | false |
| is_logistic_uom | boolean | YES | false |
| qty_step | numeric(18,6) | YES | 1 |
| rounding_mode | character varying(16) | YES | 'HALF_UP'::character varying |
| max_decimals | integer | YES | 6 |
| forbid_fraction | boolean | YES | false |
| require_lot | boolean | YES | false |
| gtin | character varying(32) | YES |  |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| validita | daterange | NO |  |

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
| uq_artuomop_one_base | `CREATE UNIQUE INDEX uq_artuomop_one_base ON catalogo.articoli_uom_operativa USING btree (articolo_id) WHERE (is_base IS TRUE)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_uom_operativa_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_articoli_uom_operativa_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_articoli_uom_operativa_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_articoli_uom_operativa_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_articoli_uom_operativa_a10_unita_misura_require_atti_d071d1 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_articoli_uom_operativa_a10_unita_misura_require_atti_d071d1 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_articoli_uom_operativa_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_uom_operativa_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_uom_operativa_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_uom_operativa_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_uom_operativa_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_uom_operativa_id')` |
| trg_articoli_uom_operativa_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_uom_operativa_id')` |

---
{% include-markdown "signature-core.md" %}
