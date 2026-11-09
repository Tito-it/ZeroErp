{% include-markdown "it/dbzero/vendite/manual/stati_commessa.md" %}
# 📚 Tabella `stati_commessa`

> 📝 **Descrizione**
>
> Lookup stati commessa: governa ciclo di vita, emissione AF e modificabilita` attivita`.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | character varying(200) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| codice_interno | character varying(50) | NO |  |
| chiude_commessa | boolean | NO | false |
| emittibile | boolean | NO | false |
| modificabile | boolean | NO | true |
| fase | character varying(20) | NO |  |
| is_abortito | boolean | NO | false |
| iniziale | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_commessa_abortito_attivo |  |
| CHECK | chk_stati_commessa_fase |  |
| CHECK | chk_stati_commessa_iniziale_attivo |  |
| PRIMARY KEY | pk_stati_commessa | id |
| UNIQUE | uq_stati_commessa_codice | codice |
| UNIQUE | uq_stati_commessa_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_commessa_attivo | `CREATE INDEX ix_stati_commessa_attivo ON vendite.stati_commessa USING btree (attivo)` |
| pk_stati_commessa | `CREATE UNIQUE INDEX pk_stati_commessa ON vendite.stati_commessa USING btree (id)` |
| uq_stati_commessa_abortito | `CREATE UNIQUE INDEX uq_stati_commessa_abortito ON vendite.stati_commessa USING btree (is_abortito) WHERE is_abortito` |
| uq_stati_commessa_codice | `CREATE UNIQUE INDEX uq_stati_commessa_codice ON vendite.stati_commessa USING btree (codice)` |
| uq_stati_commessa_codice_interno | `CREATE UNIQUE INDEX uq_stati_commessa_codice_interno ON vendite.stati_commessa USING btree (codice_interno)` |
| uq_stati_commessa_iniziale | `CREATE UNIQUE INDEX uq_stati_commessa_iniziale ON vendite.stati_commessa USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_commessa_a10_commesse_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse', 'stato_commessa_id', 'id', 'attivo')` |
| trg_stati_commessa_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_commessa_a10_transizioni_stati_commessa_block_a15bfb | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'transizioni_stati_commessa', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_commessa_a10_transizioni_stati_commessa_block_f860d1 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'transizioni_stati_commessa', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_commessa_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_commessa_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
