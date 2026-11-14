{% include-markdown "it/dbzero/config/manual/stati_doc_listino_versioni.md" %}
# 📚 Tabella `stati_doc_listino_versioni`

> 📝 **Descrizione**
>
> Vocabolario degli stati di una versione di listino (vendite.listini_versioni.stato_doc_listino_versione_id): BOZZA (in preparazione: righe e date si cambiano), ATTIVA (i prezzi sono in uso), CHIUSA (la finestra di validita' e' passata: storia dei prezzi). I passaggi in config.transizioni_stati_listino_versioni. ⚠️ Gli id del seed sono scritti anche nel predicato di ex_listini_versioni_no_overlap e in chk_listini_versioni_chiusa_con_fine (un vincolo non legge un'altra tabella): si cambiano insieme, li confronta il pgTAP vendite/test-listino-versione-al-modello-v1. Seed dal CSV 80_data/sql/config/stati_doc_listino_versioni.csv. Brief: brief-modello-documento-vendita §16 (L-1, Tid 2026-10-28).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| descrizione | character varying(120) | NO |  |
| ordine | smallint | NO |  |
| iniziale | boolean | NO | false |
| terminale | boolean | NO | false |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_doc_listino_versioni_iniziale_attivo |  |
| PRIMARY KEY | pk_stati_doc_listino_versioni | id |
| UNIQUE | uq_stati_doc_listino_versioni_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_doc_listino_versioni | `CREATE UNIQUE INDEX pk_stati_doc_listino_versioni ON config.stati_doc_listino_versioni USING btree (id)` |
| uq_stati_doc_listino_versioni_codice_interno | `CREATE UNIQUE INDEX uq_stati_doc_listino_versioni_codice_interno ON config.stati_doc_listino_versioni USING btree (codice_interno)` |
| ux_stati_doc_listino_versioni_iniziale | `CREATE UNIQUE INDEX ux_stati_doc_listino_versioni_iniziale ON config.stati_doc_listino_versioni USING btree (iniziale) WHERE iniziale` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_listino_versioni_a10_listini_versioni_bloc_f846eb | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'listini_versioni', 'stato_doc_listino_versione_id', 'id', 'attivo')` |
| trg_stati_doc_listino_versioni_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_doc_listino_versioni_a10_terminale_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale('vendite.listini_versioni')` |
| trg_stati_doc_listino_versioni_a10_terminale_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale('vendite.listini_versioni')` |
| trg_stati_doc_listino_versioni_a10_transizioni_stati_lis_71bb5b | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_listino_versioni', 'stato_da_id', 'id', 'attivo')` |
| trg_stati_doc_listino_versioni_a10_transizioni_stati_lis_87ef0d | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_listino_versioni', 'stato_a_id', 'id', 'attivo')` |
| trg_stati_doc_listino_versioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_listino_versioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
