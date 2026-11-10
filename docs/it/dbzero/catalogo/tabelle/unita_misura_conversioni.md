{% include-markdown "it/dbzero/catalogo/manual/unita_misura_conversioni.md" %}
# 📚 Tabella `unita_misura_conversioni`

> 📝 **Descrizione**
>
> Le conversioni generali fra due unita' della stessa tipologia (catalogo.trgfn_uom_conversioni_guard_tipo), con validita': una uom_from vale fattore uom_to. Una conversione per coppia di unita', in un verso o nell'altro, per ogni periodo (ex_unita_misura_conversioni_coppia_no_overlap): l'inversa la calcola catalogo.fn_get_uom_factor. La legge quella funzione quando l'articolo non ha una mappatura per l'unita' (catalogo.articoli_uom_operativa).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uom_from_id | bigint | NO |  |
| uom_to_id | bigint | NO |  |
| fattore | numeric(18,6) | NO |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_unita_misura_conversioni_fattore_finito |  |
| CHECK | chk_uom_conv_fattore_pos |  |
| CHECK | chk_uom_conv_no_self |  |
| FOREIGN KEY | fk_uom_conv_from | uom_from_id |
| FOREIGN KEY | fk_uom_conv_to | uom_to_id |
| PRIMARY KEY | pk_unita_misura_conversioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_unita_misura_conversioni_coppia_no_overlap | `CREATE INDEX ex_unita_misura_conversioni_coppia_no_overlap ON catalogo.unita_misura_conversioni USING gist (LEAST(uom_from_id, uom_to_id), GREATEST(uom_from_id, uom_to_id), validita)` |
| ix_uom_conv_from_to | `CREATE INDEX ix_uom_conv_from_to ON catalogo.unita_misura_conversioni USING btree (uom_from_id, uom_to_id, valido_dal, valido_al)` |
| ix_uom_conv_to_from | `CREATE INDEX ix_uom_conv_to_from ON catalogo.unita_misura_conversioni USING btree (uom_to_id, uom_from_id, valido_dal, valido_al)` |
| pk_unita_misura_conversioni | `CREATE UNIQUE INDEX pk_unita_misura_conversioni ON catalogo.unita_misura_conversioni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_unita_misura_conversioni_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_unita_misura_conversioni_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_unita_misura_conversioni_a10_guard_listini_attivi_dlt | AFTER | DELETE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_listini_attivi()` |
| trg_unita_misura_conversioni_a10_guard_listini_attivi_upd | AFTER | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_listini_attivi()` |
| trg_unita_misura_conversioni_a10_guard_storia_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_storia('uom_from_id', 'uom_to_id', 'fattore', 'valido_dal')` |
| trg_unita_misura_conversioni_a10_guard_storia_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_uom_guard_storia('uom_from_id', 'uom_to_id', 'fattore', 'valido_dal')` |
| trg_unita_misura_conversioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_unita_misura_conversioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_uom_conversioni_a10_guard_tipo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()` |
| trg_uom_conversioni_a10_guard_tipo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()` |

---
{% include-markdown "signature-core.md" %}
