# 📚 Tabella `gestori_utilities_ruoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.gestori_utilities_ruoli_id_seq'::regclass) |
| gestore_id | integer | NO |  |
| utility_id | integer | NO |  |
| ruolo_id | integer | NO |  |
| extra | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_gestori_anagrafiche | gestore_id |
| FOREIGN KEY | fk_tipi_ruoli_config | ruolo_id, ruolo_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_gestori_utilities_ruoli | id |
| UNIQUE | uq_gest_util_ruolo | ruolo_id, utility_id, gestore_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_gestori_utilities_ruoli_gestore_id | `CREATE INDEX ix_anagrafiche_gestori_utilities_ruoli_gestore_id ON anagrafiche.gestori_utilities_ruoli USING btree (gestore_id)` |
| ix_anagrafiche_gestori_utilities_ruoli_ruolo_id | `CREATE INDEX ix_anagrafiche_gestori_utilities_ruoli_ruolo_id ON anagrafiche.gestori_utilities_ruoli USING btree (ruolo_id)` |
| ix_anagrafiche_gestori_utilities_ruoli_utility_id | `CREATE INDEX ix_anagrafiche_gestori_utilities_ruoli_utility_id ON anagrafiche.gestori_utilities_ruoli USING btree (utility_id)` |
| ix_gur_utility | `CREATE INDEX ix_gur_utility ON anagrafiche.gestori_utilities_ruoli USING btree (utility_id)` |
| pk_gestori_utilities_ruoli | `CREATE UNIQUE INDEX pk_gestori_utilities_ruoli ON anagrafiche.gestori_utilities_ruoli USING btree (id)` |
| uq_gest_util_ruolo | `CREATE UNIQUE INDEX uq_gest_util_ruolo ON anagrafiche.gestori_utilities_ruoli USING btree (gestore_id, utility_id, ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_gestori_utilities_ruoli_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |