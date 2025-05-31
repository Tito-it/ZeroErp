{% include-markdown "it/dbzero/config/manual/utilities.md" %}
# Tabella `utilities`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.utilities_id_seq'::regclass) |
| cod_utility | character varying | NO |  |
| descrizione | character varying | NO |  |
| cd_int_utility | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_16634_1_not_null |  |
| CHECK | 16601_16634_2_not_null |  |
| CHECK | 16601_16634_3_not_null |  |
| CHECK | 16601_16634_4_not_null |  |
| CHECK | 16601_16634_5_not_null |  |
| CHECK | 16601_16634_6_not_null |  |
| CHECK | 16601_16634_7_not_null |  |
| CHECK | 16601_16634_8_not_null |  |
| CHECK | chk_cd_int_utility |  |
| CHECK | chk_cod_utility_non_vuoto |  |
| CHECK | chk_descrizione_non_vuota |  |
| PRIMARY KEY | pk_utilities | id |
| UNIQUE | uq_utilities_cd_int_utility | cd_int_utility |
| UNIQUE | uq_utilities_cod_utility | cod_utility |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_utilities | `CREATE UNIQUE INDEX pk_utilities ON config.utilities USING btree (id)` |
| uq_utilities_cd_int_utility | `CREATE UNIQUE INDEX uq_utilities_cd_int_utility ON config.utilities USING btree (cd_int_utility)` |
| uq_utilities_cod_utility | `CREATE UNIQUE INDEX uq_utilities_cod_utility ON config.utilities USING btree (cod_utility)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_utilities_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_utilities_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cd_int_utility', 'CODICE_NON_MODIFICABILE')` |