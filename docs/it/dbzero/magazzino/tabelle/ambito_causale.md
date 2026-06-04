# 📚 Tabella `ambito_causale`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | YES |  |
| user_update | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_mag_ambito_causale | id |
| UNIQUE | uq_mag_ambito_causale_codice | codice |
| UNIQUE | uq_mag_ambito_causale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_mag_ambito_causale | `CREATE UNIQUE INDEX pk_mag_ambito_causale ON magazzino.ambito_causale USING btree (id)` |
| uq_mag_ambito_causale_codice | `CREATE UNIQUE INDEX uq_mag_ambito_causale_codice ON magazzino.ambito_causale USING btree (codice)` |
| uq_mag_ambito_causale_codice_interno | `CREATE UNIQUE INDEX uq_mag_ambito_causale_codice_interno ON magazzino.ambito_causale USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ambito_causale_a10_causali_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'causali', 'ambito_causale_id', 'id', 'attivo')` |
| trg_ambito_causale_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_ambito_causale_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ambito_causale_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ambito_causale_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ambito_causale_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ambito_causale_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('ambito_causale_id')` |
| trg_ambito_causale_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('ambito_causale_id')` |

---
{% include-markdown "signature-core.md" %}
