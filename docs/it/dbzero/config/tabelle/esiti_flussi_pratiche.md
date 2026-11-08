{% include-markdown "it/dbzero/config/manual/esiti_flussi_pratiche.md" %}
# 📚 Tabella `esiti_flussi_pratiche`

> 📝 **Descrizione**
>
> Vocabolario data-driven degli esiti dei flussi (pratiche.flussi.esito). Referenziato via codice_interno da flussi.esito, template_flussi.esito_default e template_flussi_prerequisiti.esito_richiesto (FK, 20260701-02). Base strutturale di motore (POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE) seedata con lo schema; gli esiti di dominio (es. instradamento di un bivio) sono seedati dai domini in 80_data. Sostituisce l'enum cablato chk_flussi_esito.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| is_verdetto | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_esiti_flussi_pratiche | id |
| UNIQUE | uq_esiti_flussi_pratiche_codice | codice |
| UNIQUE | uq_esiti_flussi_pratiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_esiti_flussi_pratiche | `CREATE UNIQUE INDEX pk_esiti_flussi_pratiche ON config.esiti_flussi_pratiche USING btree (id)` |
| uq_esiti_flussi_pratiche_codice | `CREATE UNIQUE INDEX uq_esiti_flussi_pratiche_codice ON config.esiti_flussi_pratiche USING btree (codice)` |
| uq_esiti_flussi_pratiche_codice_interno | `CREATE UNIQUE INDEX uq_esiti_flussi_pratiche_codice_interno ON config.esiti_flussi_pratiche USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_esiti_flussi_pratiche_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_esiti_flussi_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_esiti_flussi_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_esiti_flussi_pratiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_esiti_flussi_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
