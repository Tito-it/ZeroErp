{% include-markdown "it/dbzero/config/manual/iva_natura.md" %}
# 📚 Tabella `iva_natura`

> 📝 **Descrizione**
>
> Codici natura IVA per fatturazione elettronica

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | character varying(250) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| user_insert | text | YES |  |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| is_reverse_charge | boolean | NO |  |

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
| trg_iva_natura_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_iva_natura_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_iva_natura_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_natura_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_iva_natura_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('iva_natura_id')` |
| trg_iva_natura_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('iva_natura_id')` |

---
{% include-markdown "signature-core.md" %}
