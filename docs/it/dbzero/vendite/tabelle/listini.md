{% include-markdown "it/dbzero/vendite/manual/listini.md" %}
# 📚 Tabella `listini`

> 📝 **Descrizione**
>
> Anagrafica listini di vendita.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | character varying(255) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| utility_id | integer | NO |  |
| tipologia_id | smallint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_listini_emittente_soggetto_ruolo | emittente_soggetto_ruolo_id |
| FOREIGN KEY | listini_tipologia_id_fkey | tipologia_id |
| FOREIGN KEY | listini_utility_id_fkey | utility_id |
| PRIMARY KEY | pk_listini | id |
| UNIQUE | uq_listini_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_listini_emittente_soggetto_ruolo | `CREATE INDEX ix_listini_emittente_soggetto_ruolo ON vendite.listini USING btree (emittente_soggetto_ruolo_id)` |
| ix_listini_tipologia | `CREATE INDEX ix_listini_tipologia ON vendite.listini USING btree (tipologia_id)` |
| ix_listini_utility | `CREATE INDEX ix_listini_utility ON vendite.listini USING btree (utility_id)` |
| pk_listini | `CREATE UNIQUE INDEX pk_listini ON vendite.listini USING btree (id)` |
| uq_listini_codice | `CREATE UNIQUE INDEX uq_listini_codice ON vendite.listini USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_a05_guard_spegnimento_storia_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_guard_spegnimento_storia()` |
| trg_listini_a10_categorie_clienti_listini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'categorie_clienti_listini', 'listino_id', 'id', 'attivo')` |
| trg_listini_a10_contratti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'contratti', 'listino_id', 'id', 'attivo')` |
| trg_listini_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_listini_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_listini_a10_guard_tipologia_utility_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_listini_guard_tipologia_utility()` |
| trg_listini_a10_guard_tipologia_utility_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_listini_guard_tipologia_utility()` |
| trg_listini_a10_listini_tipologie_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'tipologia_id', 'id')` |
| trg_listini_a10_listini_tipologie_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'tipologia_id', 'id')` |
| trg_listini_a10_listini_versioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_versioni', 'listino_id', 'id', 'attivo')` |
| trg_listini_a10_offerte_commerciali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'offerte_commerciali', 'listino_id', 'id', 'attivo')` |
| trg_listini_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_listini_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_listini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
