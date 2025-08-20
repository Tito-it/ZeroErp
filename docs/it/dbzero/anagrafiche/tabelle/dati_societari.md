{% include-markdown "it/dbzero/anagrafiche/manual/dati_societari.md" %}
# 📚 Tabella `dati_societari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('anagrafiche.dati_societari_id_seq'::regclass) |
| soggetto_id | uuid | NO |  |
| forma_giuridica | text | NO |  |
| capitale_sociale | numeric | NO |  |
| id_prov_iscri_rea | integer | NO |  |
| iscrizione_rea | character varying | NO |  |
| socio_unico | USER-DEFINED | NO | 'SU'::anagrafiche.socio_unico_enum |
| liquidazione | USER-DEFINED | NO | 'LN'::anagrafiche.liquidazione_enum |
| destinatario_fe | character | NO |  |
| pec_fatturazione | character varying | YES |  |
| codice_sdi | character varying | YES |  |
| data_costituzione | date | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_province_config | id_prov_iscri_rea |
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id, soggetto_id, soggetto_id, soggetto_id |
| PRIMARY KEY | pk_dati_societari | id |
| UNIQUE | uq_ds_codice_sdi | codice_sdi |
| UNIQUE | uq_ds_pec_fatt | pec_fatturazione |
| UNIQUE | uq_ds_prov_cea | id_prov_iscri_rea, iscrizione_rea |
| UNIQUE | uq_ds_soggetto | soggetto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_dati_societari_id_prov_iscri_rea | `CREATE INDEX ix_dati_societari_id_prov_iscri_rea ON anagrafiche.dati_societari USING btree (id_prov_iscri_rea)` |
| pk_dati_societari | `CREATE UNIQUE INDEX pk_dati_societari ON anagrafiche.dati_societari USING btree (id)` |
| uq_ds_codice_sdi | `CREATE UNIQUE INDEX uq_ds_codice_sdi ON anagrafiche.dati_societari USING btree (codice_sdi)` |
| uq_ds_pec_fatt | `CREATE UNIQUE INDEX uq_ds_pec_fatt ON anagrafiche.dati_societari USING btree (pec_fatturazione)` |
| uq_ds_prov_cea | `CREATE UNIQUE INDEX uq_ds_prov_cea ON anagrafiche.dati_societari USING btree (id_prov_iscri_rea, iscrizione_rea)` |
| uq_ds_soggetto | `CREATE UNIQUE INDEX uq_ds_soggetto ON anagrafiche.dati_societari USING btree (soggetto_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_dati_societari_ins_upd_check_tipo_soggetto | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_ins_upd_check_tipo_soggetto()` |
| trg_dati_societari_ins_upd_check_tipo_soggetto | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_ins_upd_check_tipo_soggetto()` |
| trg_dati_societari_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_societari_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_dati_societari_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_dati_societari_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('dati_societari_id')` |
| trg_z90_dati_societari_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('dati_societari_id')` |

---
{% include-markdown "signature-core.md" %}
