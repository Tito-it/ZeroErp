{% include-markdown "it/dbzero/config/manual/iva_assoggettamenti.md" %}
# 📚 Tabella `iva_assoggettamenti`

> 📝 **Descrizione**
>
> Dominio tipi assoggettamenti iva .

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(120) | NO |  |
| attivo | boolean | NO | true |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | YES | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_config_iva_assoggettamenti | id |
| UNIQUE | uq_cfg_iva_assoggettamenti_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_iva_assoggettamenti_attivo | `CREATE INDEX ix_cfg_iva_assoggettamenti_attivo ON config.iva_assoggettamenti USING btree (attivo)` |
| pk_config_iva_assoggettamenti | `CREATE UNIQUE INDEX pk_config_iva_assoggettamenti ON config.iva_assoggettamenti USING btree (id)` |
| uq_cfg_iva_assoggettamenti_codice | `CREATE UNIQUE INDEX uq_cfg_iva_assoggettamenti_codice ON config.iva_assoggettamenti USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_assoggettamenti_a10_iva_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'iva', 'assoggettamento_id', 'id', 'attivo')` |
| trg_iva_assoggettamenti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_iva_assoggettamenti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_iva_assoggettamenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_assoggettamenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_assoggettamenti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('iva_assoggettamenti_id')` |
| trg_iva_assoggettamenti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('iva_assoggettamenti_id')` |

---
{% include-markdown "signature-core.md" %}
