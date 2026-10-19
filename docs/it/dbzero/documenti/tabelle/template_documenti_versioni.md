{% include-markdown "it/dbzero/documenti/manual/template_documenti_versioni.md" %}
# 📚 Tabella `template_documenti_versioni`

> 📝 **Descrizione**
>
> Versioni renderizzabili del template documentale, con validita temporale e stato di pubblicazione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_documento_id | bigint | NO |  |
| versione | integer | NO |  |
| stato | character varying(30) | NO | 'BOZZA'::character varying |
| titolo | text | NO |  |
| formato_template | character varying(30) | NO | 'HTML'::character varying |
| html_template | text | NO |  |
| css_template | text | YES |  |
| markdown_template | text | YES |  |
| render_engine_id | bigint | NO |  |
| page_format | character varying(30) | NO | 'A4'::character varying |
| page_orientation | character varying(20) | NO | 'PORTRAIT'::character varying |
| margin_top_mm | numeric(8,2) | NO | 10 |
| margin_right_mm | numeric(8,2) | NO | 10 |
| margin_bottom_mm | numeric(8,2) | NO | 10 |
| margin_left_mm | numeric(8,2) | NO | 10 |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| context_schema | jsonb | NO | '{}'::jsonb |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |
| versione_contesto | integer | NO |  |
| derivata_da_versione_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_documenti_versioni_context_schema_obj |  |
| CHECK | chk_template_documenti_versioni_html_template_non_vuoto |  |
| CHECK | chk_template_documenti_versioni_margin_bottom_mm_finito |  |
| CHECK | chk_template_documenti_versioni_margin_left_mm_finito |  |
| CHECK | chk_template_documenti_versioni_margin_right_mm_finito |  |
| CHECK | chk_template_documenti_versioni_margin_top_mm_finito |  |
| CHECK | chk_template_documenti_versioni_margini_non_neg |  |
| CHECK | chk_template_documenti_versioni_stato |  |
| CHECK | chk_template_documenti_versioni_titolo_non_vuoto |  |
| CHECK | chk_template_documenti_versioni_valido_dal_pubblicata |  |
| CHECK | chk_template_documenti_versioni_versione_contesto_pos |  |
| CHECK | chk_template_documenti_versioni_versione_pos |  |
| FOREIGN KEY | fk_template_documenti_versioni_derivata_da | derivata_da_versione_id |
| FOREIGN KEY | fk_template_documenti_versioni_formati_pagina | page_format |
| FOREIGN KEY | fk_template_documenti_versioni_formati_template | formato_template |
| FOREIGN KEY | fk_template_documenti_versioni_orientamenti_pagina | page_orientation |
| FOREIGN KEY | template_documenti_versioni_render_engine_id_fkey | render_engine_id |
| FOREIGN KEY | template_documenti_versioni_template_documento_id_fkey | template_documento_id |
| PRIMARY KEY | template_documenti_versioni_pkey | id |
| UNIQUE | uq_template_documenti_versioni_template_versione | template_documento_id, versione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_template_documenti_versioni_no_overlap_pubblicata | `CREATE INDEX ex_template_documenti_versioni_no_overlap_pubblicata ON documenti.template_documenti_versioni USING gist (template_documento_id, validita) WHERE ((attivo IS TRUE) AND ((stato)::text = 'PUBBLICATA'::text))` |
| ix_template_documenti_versioni_template_stato_attivo | `CREATE INDEX ix_template_documenti_versioni_template_stato_attivo ON documenti.template_documenti_versioni USING btree (template_documento_id, stato, attivo)` |
| ix_template_documenti_versioni_template_valido_dal | `CREATE INDEX ix_template_documenti_versioni_template_valido_dal ON documenti.template_documenti_versioni USING btree (template_documento_id, valido_dal, valido_al)` |
| template_documenti_versioni_pkey | `CREATE UNIQUE INDEX template_documenti_versioni_pkey ON documenti.template_documenti_versioni USING btree (id)` |
| uq_template_documenti_versioni_template_versione | `CREATE UNIQUE INDEX uq_template_documenti_versioni_template_versione ON documenti.template_documenti_versioni USING btree (template_documento_id, versione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_documenti_versioni_a05_guard_standard_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()` |
| trg_template_documenti_versioni_a05_guard_standard_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()` |
| trg_template_documenti_versioni_a05_guard_standard_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_template_standard_guard_sola_lettura()` |
| trg_template_documenti_versioni_a10_block_delete_protected_dlt | BEFORE | DELETE | `EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_block_delete()` |
| trg_template_documenti_versioni_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_template_documenti_versioni_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_template_documenti_versioni_a10_documenti_generati_b_8557e2 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'documenti_generati', 'template_versione_id', 'id', 'attivo')` |
| trg_template_documenti_versioni_a10_guard_derivata_da_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_guard_derivata_da()` |
| trg_template_documenti_versioni_a10_guard_derivata_da_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_guard_derivata_da()` |
| trg_template_documenti_versioni_a10_protect_pubblicata_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata()` |
| trg_template_documenti_versioni_a10_render_engine_docume_fac063 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'render_engine_documento', 'attivo', 'render_engine_id', 'id')` |
| trg_template_documenti_versioni_a10_render_engine_docume_fac063 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'render_engine_documento', 'attivo', 'render_engine_id', 'id')` |
| trg_template_documenti_versioni_a10_template_documenti_r_6d5768 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti', 'attivo', 'template_documento_id', 'id')` |
| trg_template_documenti_versioni_a10_template_documenti_r_6d5768 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti', 'attivo', 'template_documento_id', 'id')` |
| trg_template_documenti_versioni_a10_template_documenti_v_6e0d39 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('documenti', 'template_documenti_versioni', 'derivata_da_versione_id', 'id', 'attivo')` |
| trg_template_documenti_versioni_a10_template_documenti_v_718a3d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti_versioni', 'attivo', 'derivata_da_versione_id', 'id')` |
| trg_template_documenti_versioni_a10_template_documenti_v_718a3d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('documenti', 'template_documenti_versioni', 'attivo', 'derivata_da_versione_id', 'id')` |
| trg_template_documenti_versioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_documenti_versioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_documenti_versioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_documenti_versioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_documenti_versioni_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_documenti_versioni_id')` |
| trg_template_documenti_versioni_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('template_documenti_versioni_id')` |

---
{% include-markdown "signature-core.md" %}
