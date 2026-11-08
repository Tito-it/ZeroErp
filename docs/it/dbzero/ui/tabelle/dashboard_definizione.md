{% include-markdown "it/dbzero/ui/manual/dashboard_definizione.md" %}
# 📚 Tabella `dashboard_definizione`

> 📝 **Descrizione**
>
> Catalogo delle dashboard configurabili. Una riga per dashboard personalizzabile (prima: home). Senza vista_sql: nessuna vista sorgente unica.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(80) | NO |  |
| descrizione | character varying(200) | NO |  |
| note | text | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO |  |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | dashboard_definizione_pkey | id |
| UNIQUE | uq_ui_dashboard_definizione_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| dashboard_definizione_pkey | `CREATE UNIQUE INDEX dashboard_definizione_pkey ON ui.dashboard_definizione USING btree (id)` |
| uq_ui_dashboard_definizione_codice | `CREATE UNIQUE INDEX uq_ui_dashboard_definizione_codice ON ui.dashboard_definizione USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_dashboard_definizione_a10_dashboard_preset_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('ui', 'dashboard_preset', 'dashboard_id', 'id', 'attivo')` |
| trg_dashboard_definizione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_dashboard_definizione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
