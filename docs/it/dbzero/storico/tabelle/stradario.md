{% include-markdown "it/dbzero/storico/manual/stradario.md" %}
# 📚 Tabella `stradario`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.stradario_id_seq'::regclass) |
| stradario_generale_id | integer | NO |  |
| comune_id | integer | NO |  |
| codice_postale_id | integer | YES |  |
| descrizione_via | text | YES |  |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| stato | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| stradario_id | integer | YES |  |
| geoloc | USER-DEFINED | YES |  |
| extra_info | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_codici_postali_config | codice_postale_id, codice_postale_id |
| FOREIGN KEY | fk_comuni_config | comune_id, comune_id, comune_id |
| FOREIGN KEY | fk_storico_stradario_stradario_generale_id_config | stradario_generale_id |
| FOREIGN KEY | fk_stradario_config | via_id_nuovo, stradario_id |
| PRIMARY KEY | pk_stradario | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_storico_stradario_codice_postale_id | `CREATE INDEX ix_storico_stradario_codice_postale_id ON storico.stradario USING btree (codice_postale_id)` |
| ix_storico_stradario_comune | `CREATE INDEX ix_storico_stradario_comune ON storico.stradario USING btree (comune_id)` |
| ix_storico_stradario_stradario_generale_id | `CREATE INDEX ix_storico_stradario_stradario_generale_id ON storico.stradario USING btree (stradario_generale_id)` |
| ix_storico_stradario_stradario_id | `CREATE INDEX ix_storico_stradario_stradario_id ON storico.stradario USING btree (stradario_id)` |
| ix_storico_stradario_valid_periodo | `CREATE INDEX ix_storico_stradario_valid_periodo ON storico.stradario USING btree (valid_from, valid_to)` |
| pk_stradario | `CREATE UNIQUE INDEX pk_stradario ON storico.stradario USING btree (id)` |