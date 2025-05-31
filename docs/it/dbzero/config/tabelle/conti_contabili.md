{% include-markdown "it/dbzero/config/manual/conti_contabili.md" %}
# Tabella `conti_contabili`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.conti_contabili_id_seq'::regclass) |
| codice_conto | character varying | NO |  |
| descrizione | character varying | NO |  |
| tipo_conto | character | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_19555_1_not_null |  |
| CHECK | 16601_19555_2_not_null |  |
| CHECK | 16601_19555_3_not_null |  |
| CHECK | 16601_19555_4_not_null |  |
| CHECK | 16601_19555_5_not_null |  |
| CHECK | 16601_19555_6_not_null |  |
| CHECK | 16601_19555_7_not_null |  |
| CHECK | 16601_19555_8_not_null |  |
| CHECK | chk_ftcc_tipo_conto |  |
| PRIMARY KEY | pk_conti_contabili | id |
| UNIQUE | uq_conti_contabili_codice_conto | codice_conto |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_conti_contabili_descrizione | `CREATE INDEX ix_conti_contabili_descrizione ON config.conti_contabili USING btree (descrizione)` |
| ix_conti_contabili_tipo_conto | `CREATE INDEX ix_conti_contabili_tipo_conto ON config.conti_contabili USING btree (tipo_conto)` |
| pk_conti_contabili | `CREATE UNIQUE INDEX pk_conti_contabili ON config.conti_contabili USING btree (id)` |
| uq_conti_contabili_codice_conto | `CREATE UNIQUE INDEX uq_conti_contabili_codice_conto ON config.conti_contabili USING btree (codice_conto)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_conti_contabili_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |