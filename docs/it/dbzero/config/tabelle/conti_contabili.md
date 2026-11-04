{% include-markdown "it/dbzero/config/manual/conti_contabili.md" %}
# 📚 Tabella `conti_contabili`

> 📝 **Descrizione**
>
> Tabella dei conti contabili per IVA e scritture, con distinzione Acquisto/Vendita

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(20) | NO |  |
| descrizione | character varying(100) | NO |  |
| tipo_conto | character(1) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

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
| trg_conti_contabili_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_conti_contabili_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_conti_contabili_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_conti_contabili_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
