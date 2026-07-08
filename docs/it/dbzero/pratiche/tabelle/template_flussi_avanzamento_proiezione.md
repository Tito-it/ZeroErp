{% include-markdown "it/dbzero/pratiche/manual/template_flussi_avanzamento_proiezione.md" %}
# 📚 Tabella `template_flussi_avanzamento_proiezione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| esito_richiesto | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tfap_esito_verdetto |  |
| FOREIGN KEY | fk_tfap_esito | esito_richiesto |
| FOREIGN KEY | fk_tfap_template_flusso | template_flusso_id |
| PRIMARY KEY | pk_template_flussi_avanzamento_proiezione | id |
| UNIQUE | uq_tfap_flusso_esito | template_flusso_id, esito_richiesto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_template_flussi_avanzamento_proiezione | `CREATE UNIQUE INDEX pk_template_flussi_avanzamento_proiezione ON pratiche.template_flussi_avanzamento_proiezione USING btree (id)` |
| uq_tfap_flusso_esito | `CREATE UNIQUE INDEX uq_tfap_flusso_esito ON pratiche.template_flussi_avanzamento_proiezione USING btree (template_flusso_id, esito_richiesto) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_flussi_avanzamento_proiezione_a10_template__99560a | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_avanzamento_proiezione_a10_template__99560a | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_avanzamento_proiezione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_template_flussi_avanzamento_proiezione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tfap_a10_guard_compatibilita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_tfap_guard_compatibilita()` |
| trg_tfap_a10_guard_compatibilita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_tfap_guard_compatibilita()` |

---
{% include-markdown "signature-core.md" %}
