{% include-markdown "it/dbzero/config/manual/qualifiche.md" %}
# 📚 Tabella `qualifiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_qualifiche | id |
| UNIQUE | uq_qualifiche_codice | codice |
| UNIQUE | uq_qualifiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_qualifiche | `CREATE UNIQUE INDEX pk_qualifiche ON config.qualifiche USING btree (id)` |
| uq_qualifiche_codice | `CREATE UNIQUE INDEX uq_qualifiche_codice ON config.qualifiche USING btree (codice)` |
| uq_qualifiche_codice_interno | `CREATE UNIQUE INDEX uq_qualifiche_codice_interno ON config.qualifiche USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_qualifiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
