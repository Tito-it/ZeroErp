{% include-markdown "it/dbzero/config/manual/termini_pagamento.md" %}
# 📚 Tabella `termini_pagamento`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(32) | NO |  |
| codice_interno | character varying(32) | NO |  |
| descrizione | character varying(120) | NO |  |
| numero_rate | smallint | NO |  |
| intervallo | smallint | NO | 0 |
| primo_offset_giorni | smallint | NO | 0 |
| ripartizione | character varying(16) | NO | 'UGUALI'::character varying |
| arrotondamento_metodo | character varying(12) | NO | 'HALF_UP'::character varying |
| arrotondamento_decimali | smallint | NO | 2 |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| fine_mese | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_termini_pag_arrotond_dec |  |
| CHECK | chk_termini_pag_numero_rate_pos |  |
| CHECK | chk_termini_pagamento_arrotondamento_metodo |  |
| CHECK | chk_termini_pagamento_intervallo_range |  |
| CHECK | chk_termini_pagamento_ripartizione |  |
| PRIMARY KEY | pk_termini_pagamento | id |
| UNIQUE | uq_cfg_termini_pagamento_codice_interno | codice_interno |
| UNIQUE | uq_termini_pagamento_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_termini_pagamento_attivo | `CREATE INDEX ix_cfg_termini_pagamento_attivo ON config.termini_pagamento USING btree (attivo)` |
| pk_termini_pagamento | `CREATE UNIQUE INDEX pk_termini_pagamento ON config.termini_pagamento USING btree (id)` |
| uq_cfg_termini_pagamento_codice_interno | `CREATE UNIQUE INDEX uq_cfg_termini_pagamento_codice_interno ON config.termini_pagamento USING btree (codice_interno)` |
| uq_termini_pagamento_codice | `CREATE UNIQUE INDEX uq_termini_pagamento_codice ON config.termini_pagamento USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_termini_pagamento_a10_clienti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'clienti', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a10_commesse_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a10_fatture_arrotondamenti_scope_b_d4eb8f | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_arrotondamenti_scope', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a10_fornitori_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'fornitori', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_termini_pagamento_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a10_preventivi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'preventivi', 'termine_pagamento_id', 'id', 'attivo')` |
| trg_termini_pagamento_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_termini_pagamento_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_termini_pagamento_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_termini_pagamento_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
