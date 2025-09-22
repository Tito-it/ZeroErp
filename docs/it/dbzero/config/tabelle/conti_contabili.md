{% include-markdown "it/dbzero/config/manual/conti_contabili.md" %}
# 📚 Tabella `conti_contabili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| tipo_conto | character | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | 'CURRENT_USER'::text |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | 'CURRENT_USER'::text |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_conti_contabili | id |
| UNIQUE | uq_conti_contabili_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_conti_contabili_descrizione | `CREATE INDEX ix_conti_contabili_descrizione ON config.conti_contabili USING btree (descrizione)` |
| ix_conti_contabili_tipo_conto | `CREATE INDEX ix_conti_contabili_tipo_conto ON config.conti_contabili USING btree (tipo_conto)` |
| pk_conti_contabili | `CREATE UNIQUE INDEX pk_conti_contabili ON config.conti_contabili USING btree (id)` |
| uq_conti_contabili_codice | `CREATE UNIQUE INDEX uq_conti_contabili_codice ON config.conti_contabili USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_conti_contabili_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
