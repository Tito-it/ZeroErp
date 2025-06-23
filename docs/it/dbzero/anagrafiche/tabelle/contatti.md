{% include-markdown "it/dbzero/anagrafiche/manual/contatti.md" %}
# Tabella `contatti`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('anagrafiche.contatti_id_seq'::regclass) |
| tipo_contatto_id | integer | NO |  |
| soggetto_id | uuid | NO |  |
| soggetto_ruolo_id | integer | YES |  |
| utility_id | integer | YES |  |
| nominativo | character varying | NO |  |
| email | character varying | YES |  |
| telefono | character varying | YES |  |
| cellulare | character varying | YES |  |
| pec | character varying | YES |  |
| note | text | YES |  |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| is_default | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| titolo_cortesia_id | integer | YES |  |
| default_context | character varying | YES |  |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id, soggetto_id, soggetto_id, soggetto_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_tipi_contatti_config | tipo_contatto_id |
| FOREIGN KEY | fk_titoli_cortesia_config | titolo_cortesia_id, titolo_cortesia_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_contatti | id |
| UNIQUE | uq_contatti_multilevel | soggetto_ruolo_id, utility_id, soggetto_id, tipo_contatto_id |

## Indici
| Nome | Definizione |
|------|-------------|
| ix_contatti_soggetto | `CREATE INDEX ix_contatti_soggetto ON anagrafiche.contatti USING btree (soggetto_id)` |
| ix_contatti_tipo | `CREATE INDEX ix_contatti_tipo ON anagrafiche.contatti USING btree (tipo_contatto_id)` |
| ix_contatti_utility | `CREATE INDEX ix_contatti_utility ON anagrafiche.contatti USING btree (utility_id)` |
| pk_contatti | `CREATE UNIQUE INDEX pk_contatti ON anagrafiche.contatti USING btree (id)` |
| uq_contatti_multilevel | `CREATE UNIQUE INDEX uq_contatti_multilevel ON anagrafiche.contatti USING btree (soggetto_id, soggetto_ruolo_id, utility_id, tipo_contatto_id)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contatti_ins_upd_set_default_contatto | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_ins_upd_set_default_contatto()` |
| trg_contatti_ins_upd_set_default_contatto | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_ins_upd_set_default_contatto()` |
| trg_upd_contatti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |