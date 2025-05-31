{% include-markdown "it/dbzero/config/manual/valute.md" %}
# Tabella `valute`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.valute_id_seq'::regclass) |
| cd_valuta | character | NO |  |
| iso_code | character | NO |  |
| iso_num_code | smallint | YES |  |
| descrizione_valuta | character varying | NO |  |
| simbolo | character varying | NO |  |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_18760_11_not_null |  |
| CHECK | 16601_18760_12_not_null |  |
| CHECK | 16601_18760_1_not_null |  |
| CHECK | 16601_18760_2_not_null |  |
| CHECK | 16601_18760_3_not_null |  |
| CHECK | 16601_18760_5_not_null |  |
| CHECK | 16601_18760_6_not_null |  |
| CHECK | 16601_18760_8_not_null |  |
| PRIMARY KEY | pk_valute | id |
| UNIQUE | uq_cd_valuta | cd_valuta |
| UNIQUE | uq_iso_code | iso_code |

## Indici
| Nome | Definizione |
|------|-------------|
| idx_valute_desc_valuta | `CREATE INDEX idx_valute_desc_valuta ON config.valute USING btree (descrizione_valuta)` |
| pk_valute | `CREATE UNIQUE INDEX pk_valute ON config.valute USING btree (id)` |
| uq_cd_valuta | `CREATE UNIQUE INDEX uq_cd_valuta ON config.valute USING btree (cd_valuta)` |
| uq_iso_code | `CREATE UNIQUE INDEX uq_iso_code ON config.valute USING btree (iso_code)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_valute_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |