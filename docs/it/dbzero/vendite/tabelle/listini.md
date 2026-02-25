{% include-markdown "it/dbzero/vendite/manual/listini.md" %}
# 📚 Tabella `listini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| dominio | character varying | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_dominio |  |
| PRIMARY KEY | pk_listini | id |
| UNIQUE | uq_listini_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini | `CREATE UNIQUE INDEX pk_listini ON vendite.listini USING btree (id)` |
| uq_listini_codice | `CREATE UNIQUE INDEX uq_listini_codice ON vendite.listini USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_a10_listini_associazioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_associazioni', 'listino_id', 'id')` |
| trg_listini_a10_listini_versioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_versioni', 'listino_id', 'id')` |
| trg_listini_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
