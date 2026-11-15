{% include-markdown "it/dbzero/catalogo/manual/articoli_uom_operativa.md" %}
# 📚 Tabella `articoli_uom_operativa`

> 📝 **Descrizione**
>
> Le unita' operative ammesse per ciascun articolo, col fattore verso l'unita' base (factor_to_base: quante unita' base vale una unita' operativa) e le regole della quantita' (qty_step, max_decimals, forbid_fraction). Versionata: per articolo e unita' le validita' non si sovrappongono (uq_articoli_uom_operativa_no_overlap), e il fattore si legge alla data del documento (catalogo.fn_uom_operativa_alla_data). La riga is_base e' l'unita' dell'articolo: fattore 1, nessuna data, la crea catalogo.trgfn_articoli_seed_uom_base e la protegge catalogo.trgfn_articoli_uom_operativa_guard_base. Un'unita' senza riga qui si converte con catalogo.unita_misura_conversioni (catalogo.fn_get_uom_factor).

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
| max_decimals | integer | YES | 6 |
| forbid_fraction | boolean | YES | false |
| gtin | character varying(32) | YES |  |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_articoli_uom_operativa_base_fissa |  |
| CHECK | chk_articoli_uom_operativa_factor_to_base_finito |  |
| CHECK | chk_articoli_uom_operativa_qty_step_finito |  |
| CHECK | ck_artuomop_factor_pos |  |
| CHECK | ck_artuomop_forbid_fraction_rules |  |
| CHECK | ck_artuomop_max_decimals_range |  |
| CHECK | ck_artuomop_qty_step_pos |  |
| FOREIGN KEY | fk_artuomop_articolo | articolo_id |
| FOREIGN KEY | fk_artuomop_uom | uom_id |
| PRIMARY KEY | pk_articoli_uom_operativa | id |
| UNIQUE | uq_articoli_uom_operativa_no_overlap | articolo_id, uom_id, validita |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_artuomop_art_isbase | `CREATE INDEX ix_artuomop_art_isbase ON catalogo.articoli_uom_operativa USING btree (articolo_id, is_base)` |
| ix_artuomop_meta_gin | `CREATE INDEX ix_artuomop_meta_gin ON catalogo.articoli_uom_operativa USING gin (meta)` |
| pk_articoli_uom_operativa | `CREATE UNIQUE INDEX pk_articoli_uom_operativa ON catalogo.articoli_uom_operativa USING btree (id)` |
| uq_articoli_uom_operativa_no_overlap | `CREATE UNIQUE INDEX uq_articoli_uom_operativa_no_overlap ON catalogo.articoli_uom_operativa USING gist (articolo_id, uom_id, validita)` |
| uq_artuomop_one_base | `CREATE UNIQUE INDEX uq_artuomop_one_base ON catalogo.articoli_uom_operativa USING btree (articolo_id) WHERE (is_base IS TRUE)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_uom_operativa_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_articoli_uom_operativa_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_articoli_uom_operativa_a10_guard_base_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_articoli_uom_operativa_guard_base()` |
| trg_articoli_uom_operativa_a10_guard_base_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_articoli_uom_operativa_guard_base()` |
| trg_articoli_uom_operativa_a10_guard_base_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION catalogo.trgfn_articoli_uom_operativa_guard_base()` |
| trg_articoli_uom_operativa_a10_guard_listini_attivi_dlt | AFTER | DELETE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_listini_attivi()` |
| trg_articoli_uom_operativa_a10_guard_listini_attivi_upd | AFTER | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_listini_attivi()` |
| trg_articoli_uom_operativa_a10_guard_storia_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_storia()` |
| trg_articoli_uom_operativa_a10_guard_storia_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_storia()` |
| trg_articoli_uom_operativa_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('articolo_id', 'E_UOM_STORIA_IMMUTABILE', 'factor_to_base', 'E_UOM_STORIA_IMMUTABILE', 'uom_id', 'E_UOM_STORIA_IMMUTABILE', 'valido_dal', 'E_UOM_STORIA_IMMUTABILE')` |
| trg_articoli_uom_operativa_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_uom_operativa_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_articoli_uom_operativa_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_uom_operativa_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_uom_operativa_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_uom_operativa_id')` |
| trg_articoli_uom_operativa_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('articoli_uom_operativa_id')` |

---
{% include-markdown "signature-core.md" %}
