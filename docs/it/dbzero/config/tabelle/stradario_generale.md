{% include-markdown "it/dbzero/config/manual/stradario_generale.md" %}
# Tabella `stradario_generale`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.stradario_generale_id_seq'::regclass) |
| toponomastica_id | integer | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 16601_16755_1_not_null |  |
| CHECK | 16601_16755_2_not_null |  |
| CHECK | 16601_16755_3_not_null |  |
| CHECK | 16601_16755_4_not_null |  |
| CHECK | 16601_16755_5_not_null |  |
| CHECK | 16601_16755_6_not_null |  |
| CHECK | 16601_16755_7_not_null |  |
| CHECK | 16601_16755_8_not_null |  |
| FOREIGN KEY | fk_stradario_generale_toponomastica_id | toponomastica_id |
| PRIMARY KEY | pk_stradario_generale | id |
| UNIQUE | uq_toponomastica_descr | descrizione, toponomastica_id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_toponomastica_id | `CREATE INDEX ix_toponomastica_id ON config.stradario_generale USING btree (toponomastica_id)` |
| pk_stradario_generale | `CREATE UNIQUE INDEX pk_stradario_generale ON config.stradario_generale USING btree (id)` |
| uq_toponomastica_descr | `CREATE UNIQUE INDEX uq_toponomastica_descr ON config.stradario_generale USING btree (toponomastica_id, descrizione)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_stradario_generale_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |