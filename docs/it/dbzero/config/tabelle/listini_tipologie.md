{% include-markdown "it/dbzero/config/manual/listini_tipologie.md" %}
# 📚 Tabella `listini_tipologie`

> 📝 **Descrizione**
>
> Tipologie voce di listino. Flag booleani esclusivi per pipeline fatturazione (e_consumo, e_quota_fissa, ecc.).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| e_consumo | boolean | NO | false |
| e_quota_fissa | boolean | NO | false |
| e_imposta | boolean | NO | false |
| e_onere | boolean | NO | false |
| e_prodotto | boolean | NO | false |
| e_servizio | boolean | NO | false |
| ordinamento | smallint | NO | 100 |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_tipologie_flag_esclusivi |  |
| PRIMARY KEY | pk_listini_tipologie | id |
| UNIQUE | uq_listini_tipologie_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini_tipologie | `CREATE UNIQUE INDEX pk_listini_tipologie ON config.listini_tipologie USING btree (id)` |
| uq_listini_tipologie_codice | `CREATE UNIQUE INDEX uq_listini_tipologie_codice ON config.listini_tipologie USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_tipologie_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'listino_tipologia_id', 'id', 'attivo')` |
| trg_listini_tipologie_a10_listini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini', 'tipologia_id', 'id', 'attivo')` |
| trg_listini_tipologie_a10_listini_tipologie_erogazioni_b_8a5a43 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'listini_tipologie_erogazioni', 'tipologia_id', 'id', 'attivo')` |
| trg_listini_tipologie_a10_listini_tipologie_utilities_bl_13ca28 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'listini_tipologie_utilities', 'tipologia_id', 'id', 'attivo')` |
| trg_listini_tipologie_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_listini_tipologie_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_listini_tipologie_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_tipologie_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_tipologie_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('listini_tipologie_id')` |
| trg_listini_tipologie_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('listini_tipologie_id')` |

---
{% include-markdown "signature-core.md" %}
