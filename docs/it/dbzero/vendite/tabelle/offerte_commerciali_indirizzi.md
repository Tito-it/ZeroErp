{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali_indirizzi.md" %}
# 📚 Tabella `offerte_commerciali_indirizzi`

> 📝 **Descrizione**
>
> Snapshot indirizzi collegati all'offerta commerciale; uno per tipo (fatturazione, consegna, fornitura, residenza). Includere nello snapshot la mail.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| offerta_id | bigint | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |
| origine_indirizzo_id | bigint | YES |  |
| origine_soggetto_ruolo_id | bigint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_offerte_commerciali_indir_offerta | offerta_id |
| FOREIGN KEY | fk_offerte_commerciali_indir_origine_indirizzo | origine_indirizzo_id |
| FOREIGN KEY | fk_offerte_commerciali_indir_origine_sog_ruolo | origine_soggetto_ruolo_id |
| FOREIGN KEY | fk_offerte_commerciali_indir_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_offerte_commerciali_indirizzi | id |
| UNIQUE | uq_offerte_commerciali_indirizzi_uno_per_tipo | offerta_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_offerte_commerciali_indir_origine_indirizzo | `CREATE INDEX ix_offerte_commerciali_indir_origine_indirizzo ON vendite.offerte_commerciali_indirizzi USING btree (origine_indirizzo_id)` |
| ix_offerte_commerciali_indir_origine_sog_ruolo | `CREATE INDEX ix_offerte_commerciali_indir_origine_sog_ruolo ON vendite.offerte_commerciali_indirizzi USING btree (origine_soggetto_ruolo_id)` |
| pk_offerte_commerciali_indirizzi | `CREATE UNIQUE INDEX pk_offerte_commerciali_indirizzi ON vendite.offerte_commerciali_indirizzi USING btree (id)` |
| uq_offerte_commerciali_indirizzi_uno_per_tipo | `CREATE UNIQUE INDEX uq_offerte_commerciali_indirizzi_uno_per_tipo ON vendite.offerte_commerciali_indirizzi USING btree (offerta_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_offerte_commerciali_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_offerte_commerciali_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_offerte_commerciali_indirizzi_a05_doc_bozza_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA_COMMERCIALE', 'offerta_id', 'BOZZA', 'TESTATA', '', '', 'E_DOC_DATI_COLLEGATI_NON_BOZZA')` |
| trg_offerte_commerciali_indirizzi_a10_guard_origine_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_indirizzi_a10_guard_origine_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('OFFERTA_COMMERCIALE')` |
| trg_offerte_commerciali_indirizzi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_indirizzi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_offerte_commerciali_indirizzi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_offerte_commerciali_indirizzi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
