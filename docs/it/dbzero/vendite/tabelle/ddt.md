{% include-markdown "it/dbzero/vendite/manual/ddt.md" %}
# 📚 Tabella `ddt`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| anno | smallint | YES |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ddt_id | bigint | NO |  |
| mittente_soggetto_ruolo_id | bigint | YES |  |
| destinatario_soggetto_ruolo_id | bigint | NO |  |
| vettore_soggetto_ruolo_id | bigint | YES |  |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric | YES |  |
| peso_netto | numeric | YES |  |
| volume | numeric | YES |  |
| targa | character varying | YES |  |
| autista | character varying | YES |  |
| data_ora_partenza | timestamp with time zone | YES |  |
| data_ora_consegna_prev | timestamp with time zone | YES |  |
| tracking_code | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ddt_v_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_ddt_v_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_ddt_v_mod_add_trasporto | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_ddt_v_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ddt_v_stato_ddt | stato_doc_ddt_id |
| FOREIGN KEY | fk_ddt_vendita_destinatario_ruolo | destinatario_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_vendita_mittente_ruolo | mittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_vendita_vettore_ruolo | vettore_soggetto_ruolo_id |
| PRIMARY KEY | pk_ddtv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_vendita_dest_stato_data | `CREATE INDEX ix_ddt_vendita_dest_stato_data ON vendite.ddt USING btree (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data)` |
| ix_ddt_vendita_stato | `CREATE INDEX ix_ddt_vendita_stato ON vendite.ddt USING btree (stato_doc_ddt_id)` |
| pk_ddtv | `CREATE UNIQUE INDEX pk_ddtv ON vendite.ddt USING btree (id)` |
| uq_ddt_v_anno_serie_numero | `CREATE UNIQUE INDEX uq_ddt_v_anno_serie_numero ON vendite.ddt USING btree (anno, serie, numero) WHERE (numero IS NOT NULL)` |
| uq_ddt_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ddt_v_sorgente_fk ON vendite.ddt USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |
| uq_ddt_vendita_uid | `CREATE UNIQUE INDEX uq_ddt_vendita_uid ON vendite.ddt USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_a10_aspetti_beni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id')` |
| trg_ddt_a10_aspetti_beni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id')` |
| trg_ddt_a10_causali_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id')` |
| trg_ddt_a10_causali_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id')` |
| trg_ddt_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')` |
| trg_ddt_a10_modalita_addebito_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id')` |
| trg_ddt_a10_modalita_addebito_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id')` |
| trg_ddt_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_ddt_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id')` |
| trg_ddt_a10_stati_doc_ddt_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_doc_ddt_id')` |
| trg_ddt_a10_stati_doc_ddt_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_doc_ddt_id')` |
| trg_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ddt_normalize()` |
| trg_ddt_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ddt_normalize()` |
| trg_ddt_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_id')` |
| trg_ddt_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_id')` |

---
{% include-markdown "signature-core.md" %}
