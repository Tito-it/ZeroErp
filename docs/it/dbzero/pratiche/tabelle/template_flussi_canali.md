{% include-markdown "it/dbzero/pratiche/manual/template_flussi_canali.md" %}
# 📚 Tabella `template_flussi_canali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| canale_id | integer | NO |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_template_flussi_canali_canale | canale_id |
| FOREIGN KEY | fk_template_flussi_canali_flusso | template_flusso_id |
| PRIMARY KEY | pk_pratiche_template_flussi_canali | id |
| UNIQUE | uq_pratiche_template_flussi_canali_flusso_canale | template_flusso_id, canale_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_template_flussi_canali | `CREATE UNIQUE INDEX pk_pratiche_template_flussi_canali ON pratiche.template_flussi_canali USING btree (id)` |
| uq_pratiche_template_flussi_canali_flusso_canale | `CREATE UNIQUE INDEX uq_pratiche_template_flussi_canali_flusso_canale ON pratiche.template_flussi_canali USING btree (template_flusso_id, canale_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_flussi_canali_a10_canali_pratiche_require_a_b1f4df | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'canali_pratiche', 'attivo', 'canale_id', 'id')` |
| trg_template_flussi_canali_a10_canali_pratiche_require_a_b1f4df | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'canali_pratiche', 'attivo', 'canale_id', 'id')` |
| trg_template_flussi_canali_a10_template_flussi_require_a_6a3242 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_canali_a10_template_flussi_require_a_6a3242 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_canali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_flussi_canali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
