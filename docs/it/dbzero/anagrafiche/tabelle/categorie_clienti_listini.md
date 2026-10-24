{% include-markdown "it/dbzero/anagrafiche/manual/categorie_clienti_listini.md" %}
# 📚 Tabella `categorie_clienti_listini`

> 📝 **Descrizione**
>
> Matrice categoria cliente x utility x emittente x classe_utenza -&gt; listino con variazione opzionale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| categoria_cliente_id | smallint | NO |  |
| utility_id | integer | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| classe_utenza_id | integer | YES |  |
| listino_id | bigint | NO |  |
| tipo_variazione | character varying(16) | YES |  |
| valore_variazione | numeric(10,4) | YES |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_categ_cli_listini_tipo_variazione |  |
| CHECK | chk_categ_cli_listini_variazione_coerente |  |
| CHECK | chk_categorie_clienti_listini_valore_variazione_finito |  |
| FOREIGN KEY | fk_categ_cli_listini_categoria | categoria_cliente_id |
| FOREIGN KEY | fk_categ_cli_listini_classe_utenza | classe_utenza_id |
| FOREIGN KEY | fk_categ_cli_listini_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_categ_cli_listini_listino | listino_id |
| FOREIGN KEY | fk_categ_cli_listini_utility | utility_id |
| PRIMARY KEY | pk_categorie_clienti_listini | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_categ_cli_listini_no_overlap | `CREATE INDEX ex_categ_cli_listini_no_overlap ON anagrafiche.categorie_clienti_listini USING gist (categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id, COALESCE(classe_utenza_id, '-1'::integer), validita) WHERE (attivo IS TRUE)` |
| ix_categ_cli_listini_attivo | `CREATE INDEX ix_categ_cli_listini_attivo ON anagrafiche.categorie_clienti_listini USING btree (attivo)` |
| ix_categ_cli_listini_validita_gist | `CREATE INDEX ix_categ_cli_listini_validita_gist ON anagrafiche.categorie_clienti_listini USING gist (validita)` |
| pk_categorie_clienti_listini | `CREATE UNIQUE INDEX pk_categorie_clienti_listini ON anagrafiche.categorie_clienti_listini USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_categorie_clienti_listini_a10_categorie_clienti_requ_3a447d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'categorie_clienti', 'attivo', 'categoria_cliente_id', 'id')` |
| trg_categorie_clienti_listini_a10_categorie_clienti_requ_3a447d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'categorie_clienti', 'attivo', 'categoria_cliente_id', 'id')` |
| trg_categorie_clienti_listini_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_categorie_clienti_listini_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_categorie_clienti_listini_a10_guard_listino_ins | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_categorie_clienti_listini_guard_listino()` |
| trg_categorie_clienti_listini_a10_guard_listino_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_categorie_clienti_listini_guard_listino()` |
| trg_categorie_clienti_listini_a10_guard_utility_tipo_ruo_46ad65 | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'emittente_soggetto_ruolo_id')` |
| trg_categorie_clienti_listini_a10_guard_utility_tipo_ruo_46ad65 | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'emittente_soggetto_ruolo_id')` |
| trg_categorie_clienti_listini_a10_listini_require_attivo_8048dc | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_categorie_clienti_listini_a10_listini_require_attivo_8048dc | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_categorie_clienti_listini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_categorie_clienti_listini_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_categorie_clienti_listini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_categorie_clienti_listini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
