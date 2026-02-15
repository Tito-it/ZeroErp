{% include-markdown "it/dbzero/pagamenti/manual/centri_riscossione.md" %}
# 📚 Tabella `centri_riscossione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | YES |  |
| descrizione | character varying | NO |  |
| is_compensazione | boolean | NO | false |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| is_fondo_fattura | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_centri_riscossione | id |
| UNIQUE | uq_centri_riscossione_codice | codice |
| UNIQUE | uq_centri_riscossione_compensazione | is_compensazione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_centri_riscossione | `CREATE UNIQUE INDEX pk_centri_riscossione ON pagamenti.centri_riscossione USING btree (id)` |
| uq_centri_riscossione_codice | `CREATE UNIQUE INDEX uq_centri_riscossione_codice ON pagamenti.centri_riscossione USING btree (codice)` |
| uq_centri_riscossione_compensazione | `CREATE UNIQUE INDEX uq_centri_riscossione_compensazione ON pagamenti.centri_riscossione USING btree (is_compensazione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_centri_riscossione_a10_enti_incasso_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'enti_incasso', 'centro_riscossione_id', 'id')` |
| trg_centri_riscossione_a10_vendite_contabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_contabili', 'centro_riscossione_id', 'id')` |
| trg_centri_riscossione_a10_vendite_movimenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pagamenti', 'vendite_movimenti', 'centro_riscossione_id', 'id')` |
| trg_centri_riscossione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
