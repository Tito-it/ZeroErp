{% include-markdown "it/dbzero/config/manual/comuni.md" %}
# Tabella `comuni`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.comuni_id_seq'::regclass) |
| descrizione | character varying | NO | ''::character varying |
| provincia_id | integer | YES |  |
| stato_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |
| storicizza | boolean | NO | false |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_16907_10_not_null |  |
| CHECK | 16601_16907_11_not_null |  |
| CHECK | 16601_16907_15_not_null |  |
| CHECK | 16601_16907_1_not_null |  |
| CHECK | 16601_16907_2_not_null |  |
| CHECK | 16601_16907_6_not_null |  |
| CHECK | 16601_16907_8_not_null |  |
| CHECK | 16601_16907_9_not_null |  |
| FOREIGN KEY | fk_provincia | provincia_id |
| FOREIGN KEY | fk_stato | stato_id |
| PRIMARY KEY | pk_comuni | id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_descrizione_comune | `CREATE INDEX ix_descrizione_comune ON config.comuni USING btree (descrizione)` |
| ix_provincia_id | `CREATE INDEX ix_provincia_id ON config.comuni USING btree (provincia_id)` |
| ix_stato_id | `CREATE INDEX ix_stato_id ON config.comuni USING btree (stato_id)` |
| pk_comuni | `CREATE UNIQUE INDEX pk_comuni ON config.comuni USING btree (id)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_comuni_upd_dlt_storico_comuni | BEFORE | DELETE | `EXECUTE FUNCTION config.trgfn_comuni_upd_dlt_storico_comuni()` |
| trg_comuni_upd_dlt_storico_comuni | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_comuni_upd_dlt_storico_comuni()` |
| trg_upd_comuni_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |