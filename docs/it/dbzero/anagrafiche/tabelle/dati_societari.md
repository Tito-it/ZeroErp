{% include-markdown "it/dbzero/anagrafiche/manual/dati_societari.md" %}
# 📚 Tabella `dati_societari`

> 📝 **Descrizione**
>
> Dati societari estesi per i soggetti di tipo aziendali

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_id | uuid | NO |  |
| capitale_sociale | numeric(15,2) | YES |  |
| id_prov_iscri_rea | integer | YES |  |
| iscrizione_rea | character varying(30) | YES |  |
| socio_unico | anagrafiche.socio_unico_enum | NO | 'SU'::anagrafiche.socio_unico_enum |
| liquidazione | anagrafiche.liquidazione_enum | NO | 'LN'::anagrafiche.liquidazione_enum |
| destinatario_fe | character varying(1) | YES |  |
| pec_fatturazione | character varying(100) | YES |  |
| codice_sdi | character varying(7) | YES |  |
| data_costituzione | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | false |
| forma_giuridica_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_dati_societari_canale_fe_coerente |  |
| CHECK | chk_dati_societari_capitale_sociale_finito |  |
| CHECK | chk_dati_societari_codice_sdi_forma |  |
| CHECK | chk_dati_societari_destinatario_fe_canale |  |
| CHECK | chk_dati_societari_rea_coppia |  |
| FOREIGN KEY | fk_dati_societari_forme_giuridiche | forma_giuridica_id |
| FOREIGN KEY | fk_province_config | id_prov_iscri_rea |
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id |
| PRIMARY KEY | pk_dati_societari | id |
| UNIQUE | uq_ds_prov_cea | id_prov_iscri_rea, iscrizione_rea |
| UNIQUE | uq_ds_soggetto | soggetto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_dati_societari_forma_giuridica_id | `CREATE INDEX ix_anagrafiche_dati_societari_forma_giuridica_id ON anagrafiche.dati_societari USING btree (forma_giuridica_id)` |
| pk_dati_societari | `CREATE UNIQUE INDEX pk_dati_societari ON anagrafiche.dati_societari USING btree (id)` |
| uq_ds_prov_cea | `CREATE UNIQUE INDEX uq_ds_prov_cea ON anagrafiche.dati_societari USING btree (id_prov_iscri_rea, iscrizione_rea)` |
| uq_ds_soggetto | `CREATE UNIQUE INDEX uq_ds_soggetto ON anagrafiche.dati_societari USING btree (soggetto_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_dati_societari_a10_forme_giuridiche_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'forme_giuridiche', 'attivo', 'forma_giuridica_id', 'id')` |
| trg_dati_societari_a10_forme_giuridiche_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'forme_giuridiche', 'attivo', 'forma_giuridica_id', 'id')` |
| trg_dati_societari_a10_guard_canale_fe_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_canale_fe()` |
| trg_dati_societari_a10_guard_canale_fe_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_canale_fe()` |
| trg_dati_societari_a10_guard_forma_giuridica_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica()` |
| trg_dati_societari_a10_guard_forma_giuridica_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica()` |
| trg_dati_societari_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_dati_societari_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_dati_societari_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_dati_societari_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_dati_societari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_societari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_societari_guard_tipo_soggetto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()` |
| trg_dati_societari_guard_tipo_soggetto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()` |
| trg_dati_societari_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('dati_societari_id')` |
| trg_dati_societari_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('dati_societari_id')` |

---
{% include-markdown "signature-core.md" %}
