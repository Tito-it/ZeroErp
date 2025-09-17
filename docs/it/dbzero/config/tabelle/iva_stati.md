{% include-markdown "it/dbzero/config/manual/iva_stati.md" %}
# 📚 Tabella `iva_stati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| iva_id | integer | NO |  |
| stato_id | integer | NO |  |
| aliquota_override | numeric | NO |  |
| assoggettamento_override | character | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | 'CURRENT_USER'::text |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | 'CURRENT_USER'::text |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_iva_assoggettamento_aliquota_iva_stati |  |
| FOREIGN KEY | fk_iva_stati_iva | iva_id |
| FOREIGN KEY | fk_iva_stati_stato | stato_id |
| PRIMARY KEY | pk_iva_stati | iva_id, stato_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_iva_stati_stato | `CREATE INDEX ix_iva_stati_stato ON config.iva_stati USING btree (stato_id)` |
| pk_iva_stati | `CREATE UNIQUE INDEX pk_iva_stati ON config.iva_stati USING btree (iva_id, stato_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_stati_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_iva_stati_ins_upd_clean_fields()` |
| trg_iva_stati_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_iva_stati_ins_upd_clean_fields()` |
| trg_upd_iva_stati_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
