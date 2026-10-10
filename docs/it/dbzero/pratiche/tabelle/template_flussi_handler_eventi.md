{% include-markdown "it/dbzero/pratiche/manual/template_flussi_handler_eventi.md" %}
# 📚 Tabella `template_flussi_handler_eventi`

> 📝 **Descrizione**
>
> Legame data-driven template di flusso -&gt; handler per evento (IN_CORSO/COMPLETATO) esito-aware. Esecutore = handler in HANDLER_MAP (riuso handler_flussi). Generalizza template_flussi.handler_id; predispone le azioni di completamento per preventivo/offerta/contratto/ordini/commesse a dati.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| evento | character varying(20) | NO |  |
| esito_richiesto | character varying(20) | YES |  |
| handler_id | integer | NO |  |
| handler_params | jsonb | NO | '{}'::jsonb |
| sequenza | integer | NO | 0 |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tfhe_evento |  |
| FOREIGN KEY | fk_tfhe_esito_richiesto | esito_richiesto |
| FOREIGN KEY | fk_tfhe_handler | handler_id |
| FOREIGN KEY | fk_tfhe_template_flusso | template_flusso_id |
| PRIMARY KEY | pk_pratiche_template_flussi_handler_eventi | id |
| UNIQUE | uq_tfhe | template_flusso_id, evento, esito_richiesto, handler_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_template_flussi_handler_eventi | `CREATE UNIQUE INDEX pk_pratiche_template_flussi_handler_eventi ON pratiche.template_flussi_handler_eventi USING btree (id)` |
| uq_tfhe | `CREATE UNIQUE INDEX uq_tfhe ON pratiche.template_flussi_handler_eventi USING btree (template_flusso_id, evento, esito_richiesto, handler_id) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_flussi_handler_eventi_a10_guard_immutabile_iud | BEFORE | DELETE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_template_flussi_handler_eventi_a10_guard_immutabile_iud | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_template_flussi_handler_eventi_a10_guard_immutabile_iud | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_template_flussi_figli_guard_immutabile('template_flusso_id')` |
| trg_template_flussi_handler_eventi_a10_handler_flussi_re_70890c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'handler_flussi', 'attivo', 'handler_id', 'id')` |
| trg_template_flussi_handler_eventi_a10_handler_flussi_re_70890c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'handler_flussi', 'attivo', 'handler_id', 'id')` |
| trg_template_flussi_handler_eventi_a10_template_flussi_r_8a06d6 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_template_flussi_handler_eventi_a10_template_flussi_r_8a06d6 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pratiche', 'template_flussi', 'attivo', 'template_flusso_id', 'id')` |
| trg_tfhe_a10_guard_no_proiezione_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_tfhe_guard_no_proiezione()` |
| trg_tfhe_a10_guard_no_proiezione_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_tfhe_guard_no_proiezione()` |

---
{% include-markdown "signature-core.md" %}
