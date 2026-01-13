{% include-markdown "it/dbzero/anagrafiche/manual/contatti.md" %}
# 📚 Tabella `contatti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_contatto_id | integer | YES |  |
| soggetto_id | uuid | NO |  |
| soggetto_ruolo_id | bigint | YES |  |
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
| tx_id | uuid | YES |  |
| unita_organizzativa_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_contatti_unita_organizzative_config | unita_organizzativa_id |
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id, soggetto_id, soggetto_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id, soggetto_ruolo_id |
| FOREIGN KEY | fk_tipi_contatti_config | tipo_contatto_id |
| FOREIGN KEY | fk_titoli_cortesia_config | titolo_cortesia_id, titolo_cortesia_id |
| FOREIGN KEY | fk_utilities_config | utility_id, utility_id, utility_id, utility_id |
| PRIMARY KEY | pk_contatti | id |
| UNIQUE | uq_contatti_multilevel | utility_id, tipo_contatto_id, soggetto_id, soggetto_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_contatti_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_contatti_soggetto_ruolo_id ON anagrafiche.contatti USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_contatti_titolo_cortesia_id | `CREATE INDEX ix_anagrafiche_contatti_titolo_cortesia_id ON anagrafiche.contatti USING btree (titolo_cortesia_id)` |
| ix_contatti_soggetto | `CREATE INDEX ix_contatti_soggetto ON anagrafiche.contatti USING btree (soggetto_id)` |
| ix_contatti_tipo | `CREATE INDEX ix_contatti_tipo ON anagrafiche.contatti USING btree (tipo_contatto_id)` |
| ix_contatti_unita_organizzativa_id | `CREATE INDEX ix_contatti_unita_organizzativa_id ON anagrafiche.contatti USING btree (unita_organizzativa_id)` |
| pk_contatti | `CREATE UNIQUE INDEX pk_contatti ON anagrafiche.contatti USING btree (id)` |
| uq_contatti_multilevel | `CREATE UNIQUE INDEX uq_contatti_multilevel ON anagrafiche.contatti USING btree (soggetto_id, soggetto_ruolo_id, utility_id, tipo_contatto_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contatti_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id')` |
| trg_contatti_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id')` |
| trg_contatti_a10_unita_organizzative_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id')` |
| trg_contatti_a10_unita_organizzative_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id')` |
| trg_contatti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contatti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contatti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contatti_set_default_contatto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()` |
| trg_contatti_set_default_contatto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()` |

---
{% include-markdown "signature-core.md" %}
