# Tabella `soggetti_ruoli`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.soggetti_ruoli_id_seq'::regclass) |
| soggetto_id | uuid | NO |  |
| ruolo_id | integer | NO |  |
| extra | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO |  |
| user_update | character varying | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | 18368_18809_10_not_null |  |
| CHECK | 18368_18809_1_not_null |  |
| CHECK | 18368_18809_2_not_null |  |
| CHECK | 18368_18809_3_not_null |  |
| CHECK | 18368_18809_6_not_null |  |
| CHECK | 18368_18809_9_not_null |  |
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id, soggetto_id, soggetto_id, soggetto_id |
| FOREIGN KEY | fk_tipi_ruoli_config | ruolo_id, ruolo_id |
| PRIMARY KEY | pk_soggetti_ruoli | id |
| UNIQUE | uq_soggetto_ruolo | ruolo_id, soggetto_id |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_soggetti_ruoli | `CREATE UNIQUE INDEX pk_soggetti_ruoli ON anagrafiche.soggetti_ruoli USING btree (id)` |
| uq_soggetto_ruolo | `CREATE UNIQUE INDEX uq_soggetto_ruolo ON anagrafiche.soggetti_ruoli USING btree (soggetto_id, ruolo_id)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_soggetti_ruoli_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |