{% include-markdown "it/dbzero/acquisti/manual/ordini.md" %}
# 📚 Tabella `ordini`

> 📝 **Descrizione**
>
> Ordini di acquisto (testata) con campi già utili alla ricezione e DDT fornitore.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | YES | uuidv7() |
| soggetto_ruolo_id | bigint | NO |  |
| serie | character varying(8) | YES |  |
| numero | character varying(20) | YES |  |
| anno | smallint | YES |  |
| data | date | NO | script.fn_data_operativa() |
| stato_doc_ordine_id | bigint | NO |  |
| sorgente_tipo_id | bigint | YES |  |
| valuta_id | integer | YES |  |
| tasso_cambio | numeric(18,8) | NO | 1 |
| modalita_pagamento_id | integer | YES |  |
| giorni_pagamento | smallint | YES |  |
| fine_mese | boolean | YES |  |
| indirizzo_consegna_id | bigint | NO |  |
| indirizzo_cons_snapshot | jsonb | NO | '{}'::jsonb |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric(18,3) | YES |  |
| peso_netto | numeric(18,3) | YES |  |
| volume | numeric(18,3) | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| data_ora_consegna_prev | timestamp with time zone | YES |  |
| imponibile_tot_atteso | numeric(18,6) | YES |  |
| sconto_tot_atteso | numeric(18,6) | YES |  |
| iva_tot_atteso | numeric(18,6) | YES |  |
| totale_doc_atteso | numeric(18,6) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
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
| CHECK | chk_ordini_ao_totali_nonneg |  |
| CHECK | chk_ordini_imponibile_tot_atteso_finito |  |
| CHECK | chk_ordini_iva_tot_atteso_finito |  |
| CHECK | chk_ordini_peso_lordo_finito |  |
| CHECK | chk_ordini_peso_netto_finito |  |
| CHECK | chk_ordini_sconto_tot_atteso_finito |  |
| CHECK | chk_ordini_tasso_cambio_finito |  |
| CHECK | chk_ordini_totale_doc_atteso_finito |  |
| CHECK | chk_ordini_volume_finito |  |
| FOREIGN KEY | fk_ao_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_ao_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_ao_matr | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_ao_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_ao_stato_doc_ordine | stato_doc_ordine_id |
| FOREIGN KEY | fk_ordini_ao_fornitore_ruolo | soggetto_ruolo_id |
| FOREIGN KEY | fk_ordini_ao_indir_cons | indirizzo_consegna_id |
| FOREIGN KEY | fk_ordini_ao_modpag | modalita_pagamento_id |
| FOREIGN KEY | fk_ordini_ao_valute | valuta_id |
| PRIMARY KEY | pk_ordini_a | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_acquisti_ordini_stato_doc_ordine_id | `CREATE INDEX ix_acquisti_ordini_stato_doc_ordine_id ON acquisti.ordini USING btree (stato_doc_ordine_id)` |
| ix_ordini_ao_fornitore_stato_data | `CREATE INDEX ix_ordini_ao_fornitore_stato_data ON acquisti.ordini USING btree (soggetto_ruolo_id, stato_doc_ordine_id, data)` |
| pk_ordini_a | `CREATE UNIQUE INDEX pk_ordini_a ON acquisti.ordini USING btree (id)` |
| uq_ordini_ao_anno_serie_numero | `CREATE UNIQUE INDEX uq_ordini_ao_anno_serie_numero ON acquisti.ordini USING btree (anno, serie, numero) WHERE (numero IS NOT NULL)` |
| uq_ordini_ao_uid | `CREATE UNIQUE INDEX uq_ordini_ao_uid ON acquisti.ordini USING btree (uid)` |
| uq_ordini_v_sorgente_fk | `CREATE UNIQUE INDEX uq_ordini_v_sorgente_fk ON acquisti.ordini USING btree (sorgente_tipo_id, sorgente_uid) WITH (fillfactor='100', deduplicate_items='true') WHERE (sorgente_tipo_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_acquisti_ordini_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_ordini_a05_stato_iniziale_ins | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_doc_stato_iniziale('stato_doc_ordine_id', 'config.stati_doc_ordini')` |
| trg_ordini_a10_ao_only_consegna_tipo_con_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION acquisti.trgfn_acq_ordini_only_consegna_tipo_con()` |
| trg_ordini_a10_ao_only_consegna_tipo_con_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION acquisti.trgfn_acq_ordini_only_consegna_tipo_con()` |
| trg_ordini_a10_aspetti_beni_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id', 'id')` |
| trg_ordini_a10_aspetti_beni_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aspetti_beni', 'attivo', 'aspetto_bene_id', 'id')` |
| trg_ordini_a10_causali_trasporto_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id', 'id')` |
| trg_ordini_a10_causali_trasporto_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'causali_trasporto', 'attivo', 'causale_trasporto_id', 'id')` |
| trg_ordini_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'E_CODICE_NON_MODIFICABILE')` |
| trg_ordini_a10_modalita_addebito_trasporto_require_attiv_dc2c74 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id', 'id')` |
| trg_ordini_a10_modalita_addebito_trasporto_require_attiv_dc2c74 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'modalita_addebito_trasporto', 'attivo', 'modalita_addebito_trasporto_id', 'id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_a10_sorgenti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'sorgenti', 'attivo', 'sorgente_tipo_id', 'id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_a10_stati_doc_ordini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_ordini', 'attivo', 'stato_doc_ordine_id', 'id')` |
| trg_ordini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |
| trg_ordini_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ordini_id')` |

---
{% include-markdown "signature-core.md" %}
