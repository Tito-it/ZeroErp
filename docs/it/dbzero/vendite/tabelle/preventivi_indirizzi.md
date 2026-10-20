{% include-markdown "it/dbzero/vendite/manual/preventivi_indirizzi.md" %}
# 📚 Tabella `preventivi_indirizzi`

> 📝 **Descrizione**
>
> Snapshot indirizzi collegati alla preventivo; uno per tipo (preventivozione, spedizione, fornitura, residenza). Includere nello snapshot la mail.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
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
| FOREIGN KEY | fk_preventivi_indir_preventivo | preventivo_id |
| FOREIGN KEY | fk_preventivi_indir_tipo | tipo_indirizzo_id |
| FOREIGN KEY | fk_preventivi_indirizzi_origine_indirizzo | origine_indirizzo_id |
| FOREIGN KEY | fk_preventivi_indirizzi_origine_sog_ruolo | origine_soggetto_ruolo_id |
| PRIMARY KEY | pk_preventivi_indirizzi | id |
| UNIQUE | uq_preventivi_indirizzi_uno_per_tipo_ | preventivo_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_preventivi_indirizzi_origine_indirizzo_id | `CREATE INDEX ix_vendite_preventivi_indirizzi_origine_indirizzo_id ON vendite.preventivi_indirizzi USING btree (origine_indirizzo_id)` |
| ix_vendite_preventivi_indirizzi_origine_soggetto_ruolo_id | `CREATE INDEX ix_vendite_preventivi_indirizzi_origine_soggetto_ruolo_id ON vendite.preventivi_indirizzi USING btree (origine_soggetto_ruolo_id)` |
| pk_preventivi_indirizzi | `CREATE UNIQUE INDEX pk_preventivi_indirizzi ON vendite.preventivi_indirizzi USING btree (id)` |
| uq_preventivi_indirizzi_uno_per_tipo_ | `CREATE UNIQUE INDEX uq_preventivi_indirizzi_uno_per_tipo_ ON vendite.preventivi_indirizzi USING btree (preventivo_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('PREVENTIVO', 'preventivo_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_preventivi_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('PREVENTIVO', 'preventivo_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_preventivi_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('PREVENTIVO', 'preventivo_id', 'DRAFT', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_preventivi_indirizzi_a10_guard_origine_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('PREVENTIVO')` |
| trg_preventivi_indirizzi_a10_guard_origine_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('PREVENTIVO')` |
| trg_preventivi_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('PREVENTIVO')` |
| trg_preventivi_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('PREVENTIVO')` |
| trg_preventivi_indirizzi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_indirizzi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_indirizzi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_preventivi_indirizzi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
