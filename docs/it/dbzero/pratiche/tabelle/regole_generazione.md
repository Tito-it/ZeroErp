{% include-markdown "it/dbzero/pratiche/manual/regole_generazione.md" %}
# 📚 Tabella `regole_generazione`

> 📝 **Descrizione**
>
> Regole di generazione cross-pratica.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_origine_id | integer | NO |  |
| tipo_prestazione_dest_id | integer | NO |  |
| template_flusso_dest_id | integer | YES |  |
| esito_richiesto | character varying(20) | YES |  |
| auto | boolean | NO | false |
| attivo | boolean | NO | true |
| descrizione | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_regole_gen_esito |  |
| FOREIGN KEY | fk_regole_gen_template_dest | template_flusso_dest_id |
| FOREIGN KEY | fk_regole_gen_template_origine | template_flusso_origine_id |
| FOREIGN KEY | fk_regole_gen_tipo_dest | tipo_prestazione_dest_id |
| PRIMARY KEY | pk_pratiche_regole_generazione | id |
| UNIQUE | uq_pratiche_regole_gen_origine_dest_esito | template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_regole_generazione | `CREATE UNIQUE INDEX pk_pratiche_regole_generazione ON pratiche.regole_generazione USING btree (id)` |
| uq_pratiche_regole_gen_origine_dest_esito | `CREATE UNIQUE INDEX uq_pratiche_regole_gen_origine_dest_esito ON pratiche.regole_generazione USING btree (template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto)` |
| uq_pratiche_regole_gen_origine_dest_null_esito | `CREATE UNIQUE INDEX uq_pratiche_regole_gen_origine_dest_null_esito ON pratiche.regole_generazione USING btree (template_flusso_origine_id, tipo_prestazione_dest_id) WHERE (esito_richiesto IS NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_regole_generazione_a10_guard_immutabile_iud | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_origine_id')` |
| trg_regole_generazione_a10_guard_immutabile_iud | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_origine_id')` |
| trg_regole_generazione_a10_guard_immutabile_iud | BEFORE | DELETE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_origine_id')` |
| trg_regole_generazione_a10_template_flussi_require_attiv_7d1c41 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_origine_id', 'id')` |
| trg_regole_generazione_a10_template_flussi_require_attiv_7d1c41 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_origine_id', 'id')` |
| trg_regole_generazione_a10_template_flussi_require_attiv_c11e19 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_dest_id', 'id')` |
| trg_regole_generazione_a10_template_flussi_require_attiv_c11e19 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_dest_id', 'id')` |
| trg_regole_generazione_a10_tipi_prestazione_require_atti_a43fb7 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_dest_id', 'id')` |
| trg_regole_generazione_a10_tipi_prestazione_require_atti_a43fb7 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'tipi_prestazione', 'attivo', 'tipo_prestazione_dest_id', 'id')` |
| trg_regole_generazione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_regole_generazione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_regole_generazione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_regole_generazione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_regole_generazione_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('regole_generazione_id')` |
| trg_regole_generazione_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('regole_generazione_id')` |

---
{% include-markdown "signature-core.md" %}
