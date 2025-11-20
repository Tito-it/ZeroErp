{% include-markdown "it/dbzero/config/manual/iva_natura.md" %}
# 📚 Tabella `iva_natura`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character | NO |  |
| descrizione | character varying | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| user_insert | character varying | YES |  |
| user_update | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_iva_natura | id |
| UNIQUE | uq_iva_natura_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_iva_natura | `CREATE UNIQUE INDEX pk_iva_natura ON config.iva_natura USING btree (id)` |
| uq_iva_natura_codice | `CREATE UNIQUE INDEX uq_iva_natura_codice ON config.iva_natura USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_natura_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
