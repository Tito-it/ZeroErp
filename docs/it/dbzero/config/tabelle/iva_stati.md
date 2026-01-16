{% include-markdown "it/dbzero/config/manual/iva_stati.md" %}
# 📚 Tabella `iva_stati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| iva_id | integer | NO |  |
| stato_id | integer | NO |  |
| aliquota_override | numeric | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| assoggettamento_id_override | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_iva_aliquota_pos_no_assogg |  |
| CHECK | chk_iva_stati_zero_requires_assogg |  |
| FOREIGN KEY | fk_iva_stati_assoggettamento_override | assoggettamento_id_override |
| FOREIGN KEY | fk_iva_stati_iva | iva_id |
| FOREIGN KEY | fk_iva_stati_stato | stato_id |
| PRIMARY KEY | pk_iva_stati | stato_id, iva_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_iva_stati_stato_id | `CREATE INDEX ix_config_iva_stati_stato_id ON config.iva_stati USING btree (stato_id)` |
| pk_iva_stati | `CREATE UNIQUE INDEX pk_iva_stati ON config.iva_stati USING btree (iva_id, stato_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_stati_a10_iva_assoggettamenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva_assoggettamenti', 'attivo', 'assoggettamento_id_override')` |
| trg_iva_stati_a10_iva_assoggettamenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva_assoggettamenti', 'attivo', 'assoggettamento_id_override')` |
| trg_iva_stati_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id')` |
| trg_iva_stati_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id')` |
| trg_iva_stati_a10_protect_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('aliquota_override', 'E_PERC_IVA_NO_MOD', 'assoggettamento_id_override', 'E_ASSOGGETTAMENTO_NO_MOD')` |
| trg_iva_stati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_stati_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_iva_stati_normalize()` |
| trg_iva_stati_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_iva_stati_normalize()` |

---
{% include-markdown "signature-core.md" %}
