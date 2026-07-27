{% include-markdown "it/dbzero/anagrafiche/manual/gestori_utilities.md" %}
# 📚 Tabella `gestori_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| gestore_id | bigint | NO |  |
| utility_id | integer | NO |  |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_gestori_anagrafiche | gestore_id |
| FOREIGN KEY | fk_utilities_config | utility_id |
| PRIMARY KEY | pk_gestori_utilities_ruoli | id |
| UNIQUE | uq_gestore_utility | gestore_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_gestori_utilities_utility_id | `CREATE INDEX ix_anagrafiche_gestori_utilities_utility_id ON anagrafiche.gestori_utilities USING btree (utility_id)` |
| pk_gestori_utilities_ruoli | `CREATE UNIQUE INDEX pk_gestori_utilities_ruoli ON anagrafiche.gestori_utilities USING btree (id)` |
| uq_gestore_utility | `CREATE UNIQUE INDEX uq_gestore_utility ON anagrafiche.gestori_utilities USING btree (gestore_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_gestori_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_gestori_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
