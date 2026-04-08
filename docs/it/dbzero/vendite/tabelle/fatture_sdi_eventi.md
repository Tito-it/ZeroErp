{% include-markdown "it/dbzero/vendite/manual/fatture_sdi_eventi.md" %}
# 📚 Tabella `fatture_sdi_eventi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_sdi_id | bigint | NO |  |
| stato_sdi_id | bigint | YES |  |
| data_evento | timestamp with time zone | NO | now() |
| codice_evento | character varying | YES |  |
| messaggio | text | YES |  |
| origine | character varying | NO | 'SDI'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_sdi_eventi_origine |  |
| FOREIGN KEY | fk_fatture_sdi_eventi_fattura_sdi | fattura_sdi_id |
| FOREIGN KEY | fk_fatture_sdi_eventi_stato_sdi | stato_sdi_id |
| PRIMARY KEY | pk_fatture_sdi_eventi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatture_sdi_eventi | `CREATE UNIQUE INDEX pk_fatture_sdi_eventi ON vendite.fatture_sdi_eventi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_sdi_eventi_a10_stati_sdi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_sdi', 'attivo', 'stato_sdi_id', 'id')` |
| trg_fatture_sdi_eventi_a10_stati_sdi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_sdi', 'attivo', 'stato_sdi_id', 'id')` |
| trg_fatture_sdi_eventi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_sdi_eventi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_sdi_eventi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_sdi_eventi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
