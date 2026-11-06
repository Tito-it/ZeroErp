{% include-markdown "it/dbzero/acquisti/manual/ordini_righe.md" %}
# 📚 Tabella `ordini_righe`

> 📝 **Descrizione**
>
> Righe ordine di acquisto, con snapshot descrizione/UoM/IVA e campi di idempotenza.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_id | bigint | NO |  |
| riga_nr | integer | NO |  |
| articolo_id | uuid | NO |  |
| descrizione | character varying(150) | NO |  |
| uom_id | bigint | YES |  |
| qta | numeric(18,6) | NO |  |
| prezzo_unitario | numeric(18,6) | NO |  |
| sconto_percentuale | numeric(5,2) | YES | 0 |
| iva_id | integer | YES |  |
| stato_doc_ordine_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_riga | bigint | YES | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| hash_contenuto | character varying(64) | YES |  |
| sorgente_uid | uuid | YES |  |
| data_consegna_richiesta | date | YES |  |
| data_consegna_confermata_fornitore | date | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_ao_r_przz_pos |  |
| CHECK | chk_ordini_ao_r_qta_pos |  |
| CHECK | chk_ordini_ao_r_sconto |  |
| CHECK | chk_ordini_righe_prezzo_unitario_finito |  |
| CHECK | chk_ordini_righe_qta_finito |  |
| CHECK | chk_ordini_righe_sconto_percentuale_finito |  |
| FOREIGN KEY | fk_ao_r_articolo | articolo_id |
| FOREIGN KEY | fk_ao_r_iva | iva_id |
| FOREIGN KEY | fk_ao_r_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ao_r_stato_doc_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ao_r_testata | ordine_id |
| FOREIGN KEY | fk_ao_r_uom | uom_id |
| PRIMARY KEY | pk_ao_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acquisti_ordini_righe_articolo_id | `CREATE INDEX ix_acquisti_ordini_righe_articolo_id ON acquisti.ordini_righe USING btree (articolo_id)` |
| ix_acquisti_ordini_righe_stato_doc_ordine_id | `CREATE INDEX ix_acquisti_ordini_righe_stato_doc_ordine_id ON acquisti.ordini_righe USING btree (stato_doc_ordine_id)` |
| pk_ao_righe | `CREATE UNIQUE INDEX pk_ao_righe ON acquisti.ordini_righe USING btree (id)` |
| uq_ao_r_riga_nr | `CREATE UNIQUE INDEX uq_ao_r_riga_nr ON acquisti.ordini_righe USING btree (ordine_id, riga_nr)` |
| uq_ordini_righe_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_righe_v_sorgente_fk ON acquisti.ordini_righe USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_righe_a10_articoli_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ordini_righe_a10_articoli_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'articoli', 'attivo', 'articolo_id', 'id')` |
| trg_ordini_righe_a10_iva_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ordini_righe_a10_iva_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'iva', 'attivo', 'iva_id', 'id')` |
| trg_ordini_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_righe_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_righe_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_righe_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_ordini_righe_a10_unita_misura_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('catalogo', 'unita_misura', 'attivo', 'uom_id', 'id')` |
| trg_ordini_righe_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_righe_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_righe_id')` |
| trg_ordini_righe_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_righe_id')` |

---
{% include-markdown "signature-core.md" %}
