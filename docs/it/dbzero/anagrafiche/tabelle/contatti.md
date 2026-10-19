{% include-markdown "it/dbzero/anagrafiche/manual/contatti.md" %}
# 📚 Tabella `contatti`

> 📝 **Descrizione**
>
> Contatti generici e specifici (soggetto/ruolo/servizio)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_contatto_id | integer | NO |  |
| soggetto_id | uuid | NO |  |
| soggetto_ruolo_id | bigint | YES |  |
| nominativo | character varying(100) | NO |  |
| email | character varying(100) | YES |  |
| telefono | character varying(20) | YES |  |
| cellulare | character varying(20) | YES |  |
| pec | character varying(100) | YES |  |
| note | text | YES |  |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| is_default | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| titolo_cortesia_id | integer | YES |  |
| default_context | character varying(20) | YES |  |
| tx_id | uuid | YES |  |
| unita_organizzativa_id | integer | YES |  |
| istanza_utility_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_contatti_istanze_utilities | istanza_utility_id |
| FOREIGN KEY | fk_contatti_unita_organizzative_config | unita_organizzativa_id |
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id |
| FOREIGN KEY | fk_soggetti_ruoli_anagrafiche | soggetto_ruolo_id |
| FOREIGN KEY | fk_tipi_contatti_config | tipo_contatto_id |
| FOREIGN KEY | fk_titoli_cortesia_config | titolo_cortesia_id |
| PRIMARY KEY | pk_contatti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_contatti_soggetto_id | `CREATE INDEX ix_anagrafiche_contatti_soggetto_id ON anagrafiche.contatti USING btree (soggetto_id)` |
| ix_anagrafiche_contatti_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_contatti_soggetto_ruolo_id ON anagrafiche.contatti USING btree (soggetto_ruolo_id)` |
| ix_anagrafiche_contatti_tipo_contatto_id | `CREATE INDEX ix_anagrafiche_contatti_tipo_contatto_id ON anagrafiche.contatti USING btree (tipo_contatto_id)` |
| ix_anagrafiche_contatti_titolo_cortesia_id | `CREATE INDEX ix_anagrafiche_contatti_titolo_cortesia_id ON anagrafiche.contatti USING btree (titolo_cortesia_id)` |
| ix_anagrafiche_contatti_unita_organizzativa_id | `CREATE INDEX ix_anagrafiche_contatti_unita_organizzativa_id ON anagrafiche.contatti USING btree (unita_organizzativa_id)` |
| ix_contatti_istanza_utility_id | `CREATE INDEX ix_contatti_istanza_utility_id ON anagrafiche.contatti USING btree (istanza_utility_id)` |
| pk_contatti | `CREATE UNIQUE INDEX pk_contatti ON anagrafiche.contatti USING btree (id)` |
| uq_contatti_ruolo_istanza_tipo | `CREATE UNIQUE INDEX uq_contatti_ruolo_istanza_tipo ON anagrafiche.contatti USING btree (soggetto_id, soggetto_ruolo_id, istanza_utility_id, tipo_contatto_id) WHERE ((soggetto_ruolo_id IS NOT NULL) AND (istanza_utility_id IS NOT NULL))` |
| uq_contatti_ruolo_tipo_no_istanza | `CREATE UNIQUE INDEX uq_contatti_ruolo_tipo_no_istanza ON anagrafiche.contatti USING btree (soggetto_id, soggetto_ruolo_id, tipo_contatto_id) WHERE ((soggetto_ruolo_id IS NOT NULL) AND (istanza_utility_id IS NULL))` |
| uq_contatti_soggetto_tipo | `CREATE UNIQUE INDEX uq_contatti_soggetto_tipo ON anagrafiche.contatti USING btree (soggetto_id, tipo_contatto_id) WHERE ((soggetto_ruolo_id IS NULL) AND (istanza_utility_id IS NULL))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contatti_a10_guard_contesto_soggetto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_guard_contesto_soggetto()` |
| trg_contatti_a10_guard_contesto_soggetto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_guard_contesto_soggetto()` |
| trg_contatti_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_contatti_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_contatti_a10_unita_organizzative_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_contatti_a10_unita_organizzative_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_contatti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contatti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contatti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contatti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_contatti_set_default_contatto_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()` |
| trg_contatti_set_default_contatto_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()` |

---
{% include-markdown "signature-core.md" %}
