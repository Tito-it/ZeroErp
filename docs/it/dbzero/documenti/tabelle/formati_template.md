# 📚 Tabella `formati_template`

> 📝 **Descrizione**
>
> Formati della sorgente di una versione di template (HTML, HTML_MARKDOWN_BLOCKS): i valori ammessi di documenti.template_documenti_versioni.formato_template, legata per FK a codice_interno. Si legge (tendina del drawer della versione, lookup generico), non si configura: niente attivo, un valore nuovo nasce con il motore che lo sa trattare. Brief: brief-db-vocabolari-versione-template.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | YES |  |
| etichetta_key | character varying(120) | NO |  |
| ordine | smallint | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_formati_template_codice_interno_non_vuoto |  |
| PRIMARY KEY | pk_formati_template | id |
| UNIQUE | uq_formati_template_codice | codice |
| UNIQUE | uq_formati_template_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_formati_template | `CREATE UNIQUE INDEX pk_formati_template ON documenti.formati_template USING btree (id)` |
| uq_formati_template_codice | `CREATE UNIQUE INDEX uq_formati_template_codice ON documenti.formati_template USING btree (codice)` |
| uq_formati_template_codice_interno | `CREATE UNIQUE INDEX uq_formati_template_codice_interno ON documenti.formati_template USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_formati_template_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_formati_template_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_formati_template_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_formati_template_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_formati_template_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_formati_template_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_formati_template_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
