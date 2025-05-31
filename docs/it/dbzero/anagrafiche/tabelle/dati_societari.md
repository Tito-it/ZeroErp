# Tabella `dati_societari`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id_dati_societari | bigint | NO | nextval('anagrafiche.dati_societari_id_seq'::regclass) |
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

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 18368_18636_13_not_null |  |
| CHECK | 18368_18636_14_not_null |  |
| CHECK | 18368_18636_15_not_null |  |
| CHECK | 18368_18636_16_not_null |  |
| CHECK | 18368_18636_1_not_null |  |
| CHECK | 18368_18636_2_not_null |  |
| CHECK | 18368_18636_3_not_null |  |
| CHECK | 18368_18636_4_not_null |  |
| CHECK | 18368_18636_5_not_null |  |
| CHECK | 18368_18636_6_not_null |  |
| CHECK | 18368_18636_7_not_null |  |
| CHECK | 18368_18636_8_not_null |  |
| CHECK | 18368_18636_9_not_null |  |
| FOREIGN KEY | fk_province_config | id_prov_iscri_rea |
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id, soggetto_id, soggetto_id, soggetto_id |
| PRIMARY KEY | pk_dati_societari | id_dati_societari |
| UNIQUE | uq_ds_codice_sdi | codice_sdi |
| UNIQUE | uq_ds_pec_fatt | pec_fatturazione |
| UNIQUE | uq_ds_prov_cea | id_prov_iscri_rea, iscrizione_rea |
| UNIQUE | uq_ds_soggetto | soggetto_id |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_dati_societari | `CREATE UNIQUE INDEX pk_dati_societari ON anagrafiche.dati_societari USING btree (id_dati_societari)` |
| uq_ds_codice_sdi | `CREATE UNIQUE INDEX uq_ds_codice_sdi ON anagrafiche.dati_societari USING btree (codice_sdi)` |
| uq_ds_pec_fatt | `CREATE UNIQUE INDEX uq_ds_pec_fatt ON anagrafiche.dati_societari USING btree (pec_fatturazione)` |
| uq_ds_prov_cea | `CREATE UNIQUE INDEX uq_ds_prov_cea ON anagrafiche.dati_societari USING btree (id_prov_iscri_rea, iscrizione_rea)` |
| uq_ds_soggetto | `CREATE UNIQUE INDEX uq_ds_soggetto ON anagrafiche.dati_societari USING btree (soggetto_id)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_dati_societari_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |