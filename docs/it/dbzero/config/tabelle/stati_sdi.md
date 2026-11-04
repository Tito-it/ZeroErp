{% include-markdown "it/dbzero/config/manual/stati_sdi.md" %}
# 📚 Tabella `stati_sdi`

> 📝 **Descrizione**
>
> Stati esito SDI (canale di invio fatture).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| codice_interno | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_sdi | id |
| UNIQUE | uq_stati_sdi_codice | codice |
| UNIQUE | uq_stati_sdi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_sdi_attivo | `CREATE INDEX ix_stati_sdi_attivo ON config.stati_sdi USING btree (attivo)` |
| pk_stati_sdi | `CREATE UNIQUE INDEX pk_stati_sdi ON config.stati_sdi USING btree (id)` |
| uq_stati_sdi_codice | `CREATE UNIQUE INDEX uq_stati_sdi_codice ON config.stati_sdi USING btree (codice)` |
| uq_stati_sdi_codice_interno | `CREATE UNIQUE INDEX uq_stati_sdi_codice_interno ON config.stati_sdi USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_sdi_a10_fatturazione_lotti_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatturazione_lotti_fatture', 'stato_sdi_id', 'id', 'attivo')` |
| trg_stati_sdi_a10_fatture_sdi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_sdi', 'stato_sdi_id', 'id', 'attivo')` |
| trg_stati_sdi_a10_fatture_sdi_eventi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_sdi_eventi', 'stato_sdi_id', 'id', 'attivo')` |
| trg_stati_sdi_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_sdi_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_sdi_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
