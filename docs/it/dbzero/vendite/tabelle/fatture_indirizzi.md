{% include-markdown "it/dbzero/vendite/manual/fatture_indirizzi.md" %}
# 📚 Tabella `fatture_indirizzi`

> 📝 **Descrizione**
>
> Snapshot indirizzi collegati alla fattura; uno per tipo (fatturazione, spedizione, fornitura, residenza). Includere nello snapshot la mail.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| origine_indirizzo_id | bigint | YES |  |
| origine_soggetto_ruolo_id | bigint | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_indir_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_indir_tipo | tipo_indirizzo_id |
| FOREIGN KEY | fk_fatture_indirizzi_origine_indirizzo | origine_indirizzo_id |
| FOREIGN KEY | fk_fatture_indirizzi_origine_sog_ruolo | origine_soggetto_ruolo_id |
| PRIMARY KEY | pk_fatture_indirizzi | id |
| UNIQUE | uq_fatture_indirizzi_uno_per_tipo_ | fattura_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_fatture_indirizzi_origine_indirizzo_id | `CREATE INDEX ix_vendite_fatture_indirizzi_origine_indirizzo_id ON vendite.fatture_indirizzi USING btree (origine_indirizzo_id)` |
| ix_vendite_fatture_indirizzi_origine_soggetto_ruolo_id | `CREATE INDEX ix_vendite_fatture_indirizzi_origine_soggetto_ruolo_id ON vendite.fatture_indirizzi USING btree (origine_soggetto_ruolo_id)` |
| pk_fatture_indirizzi | `CREATE UNIQUE INDEX pk_fatture_indirizzi ON vendite.fatture_indirizzi USING btree (id)` |
| uq_fatture_indirizzi_uno_per_tipo_ | `CREATE UNIQUE INDEX uq_fatture_indirizzi_uno_per_tipo_ ON vendite.fatture_indirizzi USING btree (fattura_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_indirizzi_a10_guard_congelamento_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id')` |
| trg_fatture_indirizzi_a10_guard_congelamento_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id')` |
| trg_fatture_indirizzi_a10_guard_congelamento_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fattura_satellite_guard_congelamento('fattura_id')` |
| trg_fatture_indirizzi_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_id')` |
| trg_fatture_indirizzi_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fattura', 'fattura_id')` |
| trg_fatture_indirizzi_a10_guard_origine_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('FATTURA')` |
| trg_fatture_indirizzi_a10_guard_origine_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente('FATTURA')` |
| trg_fatture_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('FATTURA')` |
| trg_fatture_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('FATTURA')` |
| trg_fatture_indirizzi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_indirizzi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_indirizzi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_indirizzi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_indirizzi_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_indirizzi_id')` |
| trg_fatture_indirizzi_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_indirizzi_id')` |

---
{% include-markdown "signature-core.md" %}
