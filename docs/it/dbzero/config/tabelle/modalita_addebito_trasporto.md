{% include-markdown "it/dbzero/config/manual/modalita_addebito_trasporto.md" %}
# 📚 Tabella `modalita_addebito_trasporto`

> 📝 **Descrizione**
>
> Dominio: modalità di addebito delle spese di trasporto (porto).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(32) | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_modalita_addebito_trasporto | id |
| UNIQUE | uq_modalita_addebito_trasporto_codice | codice |
| UNIQUE | uq_modalita_addebito_trasporto_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_modalita_addebito_trasporto | `CREATE UNIQUE INDEX pk_modalita_addebito_trasporto ON config.modalita_addebito_trasporto USING btree (id)` |
| uq_modalita_addebito_trasporto_codice | `CREATE UNIQUE INDEX uq_modalita_addebito_trasporto_codice ON config.modalita_addebito_trasporto USING btree (codice)` |
| uq_modalita_addebito_trasporto_codice_interno | `CREATE UNIQUE INDEX uq_modalita_addebito_trasporto_codice_interno ON config.modalita_addebito_trasporto USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_modalita_addebito_trasporto_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt', 'modalita_addebito_trasporto_id', 'id', 'attivo')` |
| trg_modalita_addebito_trasporto_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_modalita_addebito_trasporto_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini', 'modalita_addebito_trasporto_id', 'id', 'attivo')` |
| trg_modalita_addebito_trasporto_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_modalita_addebito_trasporto_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
