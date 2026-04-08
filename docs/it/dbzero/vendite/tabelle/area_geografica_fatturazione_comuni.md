{% include-markdown "it/dbzero/vendite/manual/area_geografica_fatturazione_comuni.md" %}
# 📚 Tabella `area_geografica_fatturazione_comuni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| area_geografica_id | bigint | NO |  |
| comune_id | integer | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_area_geografica_fatturazione_comuni_area | area_geografica_id |
| FOREIGN KEY | fk_area_geografica_fatturazione_comuni_comune | comune_id |
| PRIMARY KEY | pk_area_geografica_fatturazione_comuni | id |
| UNIQUE | uq_area_geografica_fatturazione_comuni | area_geografica_id, comune_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_area_geografica_fatturazione_comuni | `CREATE UNIQUE INDEX pk_area_geografica_fatturazione_comuni ON vendite.area_geografica_fatturazione_comuni USING btree (id)` |
| uq_area_geografica_fatturazione_comuni | `CREATE UNIQUE INDEX uq_area_geografica_fatturazione_comuni ON vendite.area_geografica_fatturazione_comuni USING btree (area_geografica_id, comune_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_area_geografica_fatturazione_comuni_a10_area_geograf_f88212 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_area_geografica_fatturazione_comuni_a10_area_geograf_f88212 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'area_geografica_fatturazione', 'attivo', 'area_geografica_id', 'id')` |
| trg_area_geografica_fatturazione_comuni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_area_geografica_fatturazione_comuni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
