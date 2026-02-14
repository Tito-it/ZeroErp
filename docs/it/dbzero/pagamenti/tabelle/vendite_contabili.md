{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili.md" %}
# 📚 Tabella `vendite_contabili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| centro_riscossione_id | bigint | NO |  |
| data_contabile | date | NO |  |
| data_registrazione | date | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| ente_incasso_id | bigint | YES |  |
| stato_id | smallint | YES |  |
| data_conferma | timestamp with time zone | YES |  |
| user_conferma | text | YES |  |
| compensazione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_vendite_contabili_centro_riscossione | centro_riscossione_id |
| FOREIGN KEY | fk_vendite_contabili_compensazione | compensazione_id |
| FOREIGN KEY | fk_vendite_contabili_ente_incasso | ente_incasso_id |
| FOREIGN KEY | fk_vendite_contabili_stato | stato_id |
| PRIMARY KEY | pk_vendite_contabili | id |
| UNIQUE | uq_vendite_contabili_codice | codice |
| UNIQUE | uq_vendite_contabili_compensazione | compensazione_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_contabili | `CREATE UNIQUE INDEX pk_vendite_contabili ON pagamenti.vendite_contabili USING btree (id)` |
| uq_vendite_contabili_codice | `CREATE UNIQUE INDEX uq_vendite_contabili_codice ON pagamenti.vendite_contabili USING btree (codice)` |
| uq_vendite_contabili_compensazione | `CREATE UNIQUE INDEX uq_vendite_contabili_compensazione ON pagamenti.vendite_contabili USING btree (compensazione_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_a10_centri_riscossione_require_att_2ae3a9 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id')` |
| trg_vendite_contabili_a10_centri_riscossione_require_att_2ae3a9 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id')` |
| trg_vendite_contabili_a10_guard_ente_centro_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_ente_centro()` |
| trg_vendite_contabili_a10_guard_ente_centro_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_ente_centro()` |
| trg_vendite_contabili_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vendite_contabili_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
