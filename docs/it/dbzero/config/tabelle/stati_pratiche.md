# 📚 Tabella `stati_pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| codice_interno | character varying | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_pratiche | id |
| UNIQUE | uq_stati_pratiche_codice | codice |
| UNIQUE | uq_stati_pratiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_pratiche | `CREATE UNIQUE INDEX pk_stati_pratiche ON config.stati_pratiche USING btree (id)` |
| uq_stati_pratiche_codice | `CREATE UNIQUE INDEX uq_stati_pratiche_codice ON config.stati_pratiche USING btree (codice)` |
| uq_stati_pratiche_codice_interno | `CREATE UNIQUE INDEX uq_stati_pratiche_codice_interno ON config.stati_pratiche USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_pratiche_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_stati_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
