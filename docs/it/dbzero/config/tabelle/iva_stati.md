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
| ix_iva_stati_stato | `CREATE INDEX ix_iva_stati_stato ON config.iva_stati USING btree (stato_id)` |
| pk_iva_stati | `CREATE UNIQUE INDEX pk_iva_stati ON config.iva_stati USING btree (iva_id, stato_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_config_iva_a10_upd_stati_protect_columns | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('aliquota_override', 'E_PERC_IVA_NO_MOD', 'assoggettamento_id_override', 'E_ASSOGGETTAMENTO_NO_MOD')` |
| trg_iva_stati_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_iva_stati_ins_upd_clean_fields()` |
| trg_iva_stati_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_iva_stati_ins_upd_clean_fields()` |
| trg_iva_stati_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
