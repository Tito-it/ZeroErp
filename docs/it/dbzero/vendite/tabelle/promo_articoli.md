{% include-markdown "it/dbzero/vendite/manual/promo_articoli.md" %}
# 📚 Tabella `promo_articoli`

> 📝 **Descrizione**
>
> Overlay promo temporale per (articolo, uom) - STADIO 0 del resolver prezzi v5.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | character varying(255) | NO |  |
| articolo_id | uuid | NO |  |
| uom_id | bigint | NO |  |
| tipo_variazione | character varying(16) | NO |  |
| valore_variazione | numeric(10,4) | NO |  |
| valido_dal | date | NO |  |
| valido_al | date | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_promo_articoli_tipo_variazione |  |
| CHECK | chk_promo_articoli_valore_variazione_finito |  |
| FOREIGN KEY | fk_promo_articoli_articolo | articolo_id |
| FOREIGN KEY | fk_promo_articoli_uom | uom_id |
| PRIMARY KEY | pk_promo_articoli | id |
| UNIQUE | uq_promo_articoli_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_promo_articoli_no_overlap | `CREATE INDEX ex_promo_articoli_no_overlap ON vendite.promo_articoli USING gist (articolo_id, uom_id, validita) WHERE (attivo IS TRUE)` |
| ix_promo_articoli_attivo | `CREATE INDEX ix_promo_articoli_attivo ON vendite.promo_articoli USING btree (attivo)` |
| ix_promo_articoli_validita_gist | `CREATE INDEX ix_promo_articoli_validita_gist ON vendite.promo_articoli USING gist (validita)` |
| pk_promo_articoli | `CREATE UNIQUE INDEX pk_promo_articoli ON vendite.promo_articoli USING btree (id)` |
| uq_promo_articoli_codice | `CREATE UNIQUE INDEX uq_promo_articoli_codice ON vendite.promo_articoli USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_promo_articoli_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_promo_articoli_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_promo_articoli_a10_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'promo_id', 'id', 'attivo')` |
| trg_promo_articoli_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'promo_id', 'id', 'attivo')` |
| trg_promo_articoli_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_promo_articoli_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_promo_articoli_a10_guard_articolo_ammesso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('PROMO_ARTICOLO', 'id')` |
| trg_promo_articoli_a10_guard_articolo_ammesso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_righe_guard_articolo_ammesso('PROMO_ARTICOLO', 'id')` |
| trg_promo_articoli_a10_guard_data_driven_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_promo_articoli_guard_data_driven()` |
| trg_promo_articoli_a10_guard_data_driven_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_promo_articoli_guard_data_driven()` |
| trg_promo_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_promo_articoli_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_promo_articoli_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_promo_articoli_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_promo_articoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_promo_articoli_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_promo_articoli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_promo_articoli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
