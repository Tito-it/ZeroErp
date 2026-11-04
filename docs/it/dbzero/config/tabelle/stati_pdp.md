{% include-markdown "it/dbzero/config/manual/stati_pdp.md" %}
# 📚 Tabella `stati_pdp`

> 📝 **Descrizione**
>
> Stati tecnici dei punti di prelievo (PDP): disponibile, attivo, disattivo tecnico, dismesso.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(16) | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| ordine | integer | NO | 10 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_pdp | id |
| UNIQUE | uq_stati_pdp_codice | codice |
| UNIQUE | uq_stati_pdp_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_pdp_attivo_ordine | `CREATE INDEX ix_stati_pdp_attivo_ordine ON config.stati_pdp USING btree (attivo, ordine)` |
| pk_stati_pdp | `CREATE UNIQUE INDEX pk_stati_pdp ON config.stati_pdp USING btree (id)` |
| uq_stati_pdp_codice | `CREATE UNIQUE INDEX uq_stati_pdp_codice ON config.stati_pdp USING btree (codice)` |
| uq_stati_pdp_codice_interno | `CREATE UNIQUE INDEX uq_stati_pdp_codice_interno ON config.stati_pdp USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_pdp_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_pdp_a10_pdp_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'pdp', 'stato_pdp_id', 'id', 'attivo')` |
| trg_stati_pdp_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_pdp_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_pdp_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_pdp_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_pdp_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stati_pdp_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stati_pdp_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('stati_pdp_id')` |
| trg_stati_pdp_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('stati_pdp_id')` |

---
{% include-markdown "signature-core.md" %}
