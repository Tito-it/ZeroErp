{% include-markdown "it/dbzero/vendite/manual/ddt_indirizzi.md" %}
# 📚 Tabella `ddt_indirizzi`

> 📝 **Descrizione**
>
> Snapshot indirizzi collegati al ddt; uno per tipo ( spedizione, fornitura, residenza). Includere nello snapshot la mail.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_id | bigint | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| origine_indirizzo_id | bigint | YES |  |
| origine_soggetto_ruolo_id | bigint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ddt_indirizzi_ddt | ddt_id |
| FOREIGN KEY | fk_ddt_indirizzi_origine_indirizzo | origine_indirizzo_id |
| FOREIGN KEY | fk_ddt_indirizzi_origine_sog_ruolo | origine_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_indirizzo_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_ddt_indirizzi | id |
| UNIQUE | uq_ddt_indirizzi_uno_per_tipo | ddt_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_ddt_indirizzi_origine_indirizzo_id | `CREATE INDEX ix_vendite_ddt_indirizzi_origine_indirizzo_id ON vendite.ddt_indirizzi USING btree (origine_indirizzo_id)` |
| ix_vendite_ddt_indirizzi_origine_soggetto_ruolo_id | `CREATE INDEX ix_vendite_ddt_indirizzi_origine_soggetto_ruolo_id ON vendite.ddt_indirizzi USING btree (origine_soggetto_ruolo_id)` |
| pk_ddt_indirizzi | `CREATE UNIQUE INDEX pk_ddt_indirizzi ON vendite.ddt_indirizzi USING btree (id)` |
| uq_ddt_indirizzi_uno_per_tipo | `CREATE UNIQUE INDEX uq_ddt_indirizzi_uno_per_tipo ON vendite.ddt_indirizzi USING btree (ddt_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_ddt_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_ddt_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT_VENDITA', 'ddt_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_ddt_indirizzi_a10_guard_origine_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('DDT_VENDITA')` |
| trg_ddt_indirizzi_a10_guard_origine_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('DDT_VENDITA')` |
| trg_ddt_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('DDT_VENDITA')` |
| trg_ddt_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('DDT_VENDITA')` |
| trg_ddt_indirizzi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_indirizzi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_indirizzi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_indirizzi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
