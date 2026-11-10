{% include-markdown "it/dbzero/vendite/manual/area_geografica_fatturazione.md" %}
# 📚 Tabella `area_geografica_fatturazione`

> 📝 **Descrizione**
>
> Area geografica per raggruppamenti fatturazione (comuni).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | text | NO |  |
| descrizione | text | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_area_geografica_fatturazione | id |
| UNIQUE | uq_area_geografica_fatturazione_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_area_geografica_fatturazione | `CREATE UNIQUE INDEX pk_area_geografica_fatturazione ON vendite.area_geografica_fatturazione USING btree (id)` |
| uq_area_geografica_fatturazione_codice | `CREATE UNIQUE INDEX uq_area_geografica_fatturazione_codice ON vendite.area_geografica_fatturazione USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_area_geografica_fatturazione_a10_area_geografica_fat_ac8b7b | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'area_geografica_fatturazione_comuni', 'area_geografica_id', 'id', 'attivo')` |
| trg_area_geografica_fatturazione_a10_attivita_fatturabil_736ee0 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'attivita_fatturabili', 'area_geografica_id', 'id', 'attivo')` |
| trg_area_geografica_fatturazione_a10_commesse_attivita_b_717fad | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'area_geografica_id', 'id', 'attivo')` |
| trg_area_geografica_fatturazione_a10_fatturazione_lotti_ea0fab | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti', 'area_geografica_id', 'id', 'attivo')` |
| trg_area_geografica_fatturazione_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_area_geografica_fatturazione_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_area_geografica_fatturazione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_area_geografica_fatturazione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
