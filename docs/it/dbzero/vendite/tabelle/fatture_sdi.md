{% include-markdown "it/dbzero/vendite/manual/fatture_sdi.md" %}
# 📚 Tabella `fatture_sdi`

> 📝 **Descrizione**
>
> Testata tentativi SDI per fattura con stato corrente e dati di invio/esito.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| tentativo_num | smallint | NO | 1 |
| stato_sdi_id | bigint | NO |  |
| data_invio | timestamp with time zone | YES |  |
| data_ricezione | timestamp with time zone | YES |  |
| identificativo_sdi | character varying(64) | YES |  |
| nome_file | text | YES |  |
| messaggio_errore | text | YES |  |
| critical | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_sdi_tentativo_num |  |
| FOREIGN KEY | fk_fatture_sdi_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_sdi_stato_sdi | stato_sdi_id |
| PRIMARY KEY | pk_fatture_sdi | id |
| UNIQUE | uq_fatture_sdi_fattura_tentativo | fattura_id, tentativo_num |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatture_sdi | `CREATE UNIQUE INDEX pk_fatture_sdi ON vendite.fatture_sdi USING btree (id)` |
| uq_fatture_sdi_fattura_tentativo | `CREATE UNIQUE INDEX uq_fatture_sdi_fattura_tentativo ON vendite.fatture_sdi USING btree (fattura_id, tentativo_num)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_sdi_a10_stati_sdi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_sdi', 'attivo', 'stato_sdi_id', 'id')` |
| trg_fatture_sdi_a10_stati_sdi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_sdi', 'attivo', 'stato_sdi_id', 'id')` |
| trg_fatture_sdi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_sdi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_sdi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_sdi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
