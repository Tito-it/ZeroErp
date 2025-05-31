# Tabella `tipi_indirizzi`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.tipi_indirizzi_id_seq'::regclass) |
| cod_int_tipo_indirizzo | character varying | NO |  |
| descrizione | text | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_19020_1_not_null |  |
| CHECK | 16601_19020_2_not_null |  |
| CHECK | 16601_19020_3_not_null |  |
| CHECK | 16601_19020_4_not_null |  |
| CHECK | 16601_19020_5_not_null |  |
| CHECK | 16601_19020_6_not_null |  |
| CHECK | 16601_19020_7_not_null |  |
| CHECK | chk_cod_int_tipo_indirizzo |  |
| PRIMARY KEY | pk_tipi_indirizzi | id |
| UNIQUE | uq_tipi_indirizzi_cod_int_tipo_indirizzo | cod_int_tipo_indirizzo |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_indirizzi | `CREATE UNIQUE INDEX pk_tipi_indirizzi ON config.tipi_indirizzi USING btree (id)` |
| uq_tipi_indirizzi_cod_int_tipo_indirizzo | `CREATE UNIQUE INDEX uq_tipi_indirizzi_cod_int_tipo_indirizzo ON config.tipi_indirizzi USING btree (cod_int_tipo_indirizzo)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_indirizzi_upd_lock_cod_interno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cod_int_tipo_indirizzo', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_indirizzi_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |