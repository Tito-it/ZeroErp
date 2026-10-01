{% include-markdown "it/dbzero/catalogo/manual/unita_misura_conversioni.md" %}
# 📚 Tabella `unita_misura_conversioni`

> 📝 **Descrizione**
>
> Conversioni globali tra unita di misura con validita temporale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uom_from_id | bigint | NO |  |
| uom_to_id | bigint | NO |  |
| fattore | numeric | NO |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_uom_conv_fattore_pos |  |
| CHECK | chk_uom_conv_no_self |  |
| FOREIGN KEY | fk_uom_conv_from | uom_from_id |
| FOREIGN KEY | fk_uom_conv_to | uom_to_id |
| PRIMARY KEY | pk_unita_misura_conversioni | id |
| UNIQUE | uq_uom_conv_no_overlap | uom_from_id, uom_to_id, validita |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_uom_conv_from_to | `CREATE INDEX ix_uom_conv_from_to ON catalogo.unita_misura_conversioni USING btree (uom_from_id, uom_to_id, valido_dal, valido_al)` |
| ix_uom_conv_to_from | `CREATE INDEX ix_uom_conv_to_from ON catalogo.unita_misura_conversioni USING btree (uom_to_id, uom_from_id, valido_dal, valido_al)` |
| pk_unita_misura_conversioni | `CREATE UNIQUE INDEX pk_unita_misura_conversioni ON catalogo.unita_misura_conversioni USING btree (id)` |
| uq_uom_conv_no_overlap | `CREATE UNIQUE INDEX uq_uom_conv_no_overlap ON catalogo.unita_misura_conversioni USING gist (uom_from_id, uom_to_id, validita)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_unita_misura_conversioni_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_unita_misura_conversioni_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_unita_misura_conversioni_a10_unita_misura_require_at_2627db | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_to_id', 'id')` |
| trg_unita_misura_conversioni_a10_unita_misura_require_at_2627db | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_to_id', 'id')` |
| trg_unita_misura_conversioni_a10_unita_misura_require_at_3ec9a9 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_from_id', 'id')` |
| trg_unita_misura_conversioni_a10_unita_misura_require_at_3ec9a9 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_from_id', 'id')` |
| trg_unita_misura_conversioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_unita_misura_conversioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_uom_conversioni_a10_guard_tipo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()` |
| trg_uom_conversioni_a10_guard_tipo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()` |

---
{% include-markdown "signature-core.md" %}
