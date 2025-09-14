# 📚 Tabella `modalita_addebito_trasporto`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
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
| trg_block_deact_modalita_addebito_trasporto_ordini | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ordini', 'modalita_addebito_trasporto_id')` |
| trg_mod_add_trasporto_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |

---
{% include-markdown "signature-core.md" %}
