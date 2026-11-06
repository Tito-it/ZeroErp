{% include-markdown "it/dbzero/acquisti/manual/ddt.md" %}
# 📚 Tabella `ddt`

> 📝 **Descrizione**
>
> Documento di Trasporto (DDT) – acquisto (ricezione da fornitore).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| anno | smallint | YES |  |
| serie | character varying(8) | YES |  |
| numero | character varying(40) | YES |  |
| data | date | NO | script.fn_data_operativa() |
| stato_doc_ddt_id | bigint | NO |  |
| mittente_soggetto_ruolo_id | bigint | NO |  |
| destinatario_soggetto_ruolo_id | bigint | YES |  |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric(18,3) | YES |  |
| peso_netto | numeric(18,3) | YES |  |
| volume | numeric(18,3) | YES |  |
| data_ora_consegna_eff | timestamp with time zone | YES |  |
| ordine_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| hash_contenuto | character varying(64) | YES |  |
| sorgente_uid | uuid | YES |  |
| sorgente_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ddt_peso_lordo_finito |  |
| CHECK | chk_ddt_peso_netto_finito |  |
| CHECK | chk_ddt_volume_finito |  |
| FOREIGN KEY | fk_a_ddt_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_a_ddt_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_a_ddt_destinatario_ruolo | destinatario_soggetto_ruolo_id |
| FOREIGN KEY | fk_a_ddt_mittente_ruolo | mittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_a_ddt_mod_add_trasporto | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_a_ddt_ordine | ordine_id |
| FOREIGN KEY | fk_a_ddt_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_a_ddt_stato_ddt | stato_doc_ddt_id |
| PRIMARY KEY | pk_ddta | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_a_ddt_mittente_stato_data | `CREATE INDEX ix_a_ddt_mittente_stato_data ON acquisti.ddt USING btree (mittente_soggetto_ruolo_id, stato_doc_ddt_id, data)` |
| pk_ddta | `CREATE UNIQUE INDEX pk_ddta ON acquisti.ddt USING btree (id)` |
| uq_a_ddt_anno_serie_numero | `CREATE UNIQUE INDEX uq_a_ddt_anno_serie_numero ON acquisti.ddt USING btree (anno, serie, numero)` |
| uq_a_ddt_uid | `CREATE UNIQUE INDEX uq_a_ddt_uid ON acquisti.ddt USING btree (uid)` |
| uq_ddt_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ddt_v_sorgente_fk ON acquisti.ddt USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_ddt_id', 'config.stati_doc_ddt')` |
| trg_ddt_a10_aspetti_beni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id', 'id')` |
| trg_ddt_a10_aspetti_beni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id', 'id')` |
| trg_ddt_a10_causali_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id', 'id')` |
| trg_ddt_a10_causali_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id', 'id')` |
| trg_ddt_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'E_CODICE_NON_MODIFICABILE')` |
| trg_ddt_a10_modalita_addebito_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id', 'id')` |
| trg_ddt_a10_modalita_addebito_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id', 'id')` |
| trg_ddt_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ddt_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ddt_a10_stati_doc_ddt_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_doc_ddt_id', 'id')` |
| trg_ddt_a10_stati_doc_ddt_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ddt', 'attivo', 'stato_doc_ddt_id', 'id')` |
| trg_ddt_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ddt_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ddt_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_id')` |
| trg_ddt_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ddt_id')` |

---
{% include-markdown "signature-core.md" %}
