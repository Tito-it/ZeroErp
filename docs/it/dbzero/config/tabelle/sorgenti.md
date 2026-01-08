{% include-markdown "it/dbzero/config/manual/sorgenti.md" %}
# 📚 Tabella `sorgenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| categoria | character varying | YES |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| target_table | regclass | YES |  |
| key_selector | text | NO | 'id'::text |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sorgenti_codice_interno_non_vuoto |  |
| CHECK | chk_sorgenti_key_selector_values |  |
| PRIMARY KEY | sorgenti_pkey | id |
| UNIQUE | uq_sorgenti_codice | codice |
| UNIQUE | uq_sorgenti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| sorgenti_pkey | `CREATE UNIQUE INDEX sorgenti_pkey ON config.sorgenti USING btree (id)` |
| uq_sorgenti_codice | `CREATE UNIQUE INDEX uq_sorgenti_codice ON config.sorgenti USING btree (codice)` |
| uq_sorgenti_codice_interno | `CREATE UNIQUE INDEX uq_sorgenti_codice_interno ON config.sorgenti USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sorgenti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('categoria', 'CODICE_NON_MODIFICABILE')` |
| trg_sorgenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sorgenti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_sorgenti_normalize()` |
| trg_sorgenti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_sorgenti_normalize()` |

---
{% include-markdown "signature-core.md" %}
