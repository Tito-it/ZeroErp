# Tabella `comuni`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.comuni_id_seq'::regclass) |
| descrizione | text | YES |  |
| extra_country | jsonb | YES |  |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| stato | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| comune_id | integer | YES |  |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16962_16972_1_not_null |  |
| CHECK | 16962_16972_4_not_null |  |
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id, comune_id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_storico_comuni_descrizione | `CREATE INDEX ix_storico_comuni_descrizione ON storico.comuni USING btree (descrizione)` |
| ix_storico_comuni_valid | `CREATE INDEX ix_storico_comuni_valid ON storico.comuni USING btree (valid_from, valid_to)` |