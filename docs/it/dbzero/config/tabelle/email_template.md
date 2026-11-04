{% include-markdown "it/dbzero/config/manual/email_template.md" %}
# 📚 Tabella `email_template`

> 📝 **Descrizione**
>
> Template email parametrizzabili con variabili {{...}}. Override per reparto, tipo prestazione e lingua.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(100) | NO |  |
| unita_organizzativa_id | integer | YES |  |
| tipo_prestazione_id | integer | YES |  |
| lingua | character varying(5) | NO | 'it'::character varying |
| oggetto | text | NO |  |
| corpo_html | text | NO |  |
| corpo_testo | text | YES |  |
| variabili_disponibili | jsonb | NO | '[]'::jsonb |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | email_template_tipo_prestazione_id_fkey | tipo_prestazione_id |
| FOREIGN KEY | email_template_unita_organizzativa_id_fkey | unita_organizzativa_id |
| PRIMARY KEY | email_template_pkey | id |
| UNIQUE | uq_email_template_codice_uo_tp_lingua | codice, unita_organizzativa_id, tipo_prestazione_id, lingua |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| email_template_pkey | `CREATE UNIQUE INDEX email_template_pkey ON config.email_template USING btree (id)` |
| uq_email_template_codice_uo_tp_lingua | `CREATE UNIQUE INDEX uq_email_template_codice_uo_tp_lingua ON config.email_template USING btree (codice, unita_organizzativa_id, tipo_prestazione_id, lingua) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_email_template_a10_email_log_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_log', 'email_template_id', 'id', 'attivo')` |
| trg_email_template_a10_email_outbox_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_outbox', 'email_template_id', 'id', 'attivo')` |
| trg_email_template_a10_tipi_prestazione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_email_template_a10_tipi_prestazione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_id', 'id')` |
| trg_email_template_a10_unita_organizzative_require_attiv_522c7e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_email_template_a10_unita_organizzative_require_attiv_522c7e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_email_template_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_email_template_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_email_template_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_email_template_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
