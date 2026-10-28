{% include-markdown "it/dbzero/config/manual/transizioni_stati_listino_versioni.md" %}
# 📚 Tabella `transizioni_stati_listino_versioni`

> 📝 **Descrizione**
>
> Matrice dei passaggi di stato di una versione di listino: una riga attiva = un passaggio ammesso. La giudica il guard vendite.trgfn_listini_versioni_guard_transizione_stato a ogni UPDATE che cambia lo stato; la legge il verbo comune (script.fn_doc_passaggio). BOZZA -&gt; ATTIVA e' manuale, con l'azione attiva_listino (L-3), e lo scrive vendite.fn_attiva_versione_listino; ATTIVA -&gt; CHIUSA e' di processo (meta.manuale = false): lo scrive solo vendite.fn_chiudi_versioni_listino_scadute, a finestra scaduta (L-2). Seed dal CSV 80_data/sql/config/transizioni_stati_listino_versioni.csv. Brief: brief-modello-documento-vendita §16 (L-2, L-3, Tid 2026-10-28).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | bigint | NO |  |
| stato_a_id | bigint | NO |  |
| azione_processo_codename | character varying(100) | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_transizioni_stati_listino_versioni_non_riflessa |  |
| CHECK | ck_transizioni_stati_listino_versioni_meta_manuale_dichiarato |  |
| FOREIGN KEY | fk_transizioni_stati_listino_versioni_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_listino_versioni_azioni_processo | azione_processo_codename |
| FOREIGN KEY | fk_transizioni_stati_listino_versioni_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_listino_versioni | id |
| UNIQUE | uq_transizioni_stati_listino_versioni | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_listino_versioni | `CREATE UNIQUE INDEX pk_transizioni_stati_listino_versioni ON config.transizioni_stati_listino_versioni USING btree (id)` |
| uq_transizioni_stati_listino_versioni | `CREATE UNIQUE INDEX uq_transizioni_stati_listino_versioni ON config.transizioni_stati_listino_versioni USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_listino_versioni_a10_stati_doc_lis_2a7aad | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_listino_versioni', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_listino_versioni_a10_stati_doc_lis_2a7aad | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_listino_versioni', 'attivo', 'stato_da_id', 'id')` |
| trg_transizioni_stati_listino_versioni_a10_stati_doc_lis_cdf482 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_listino_versioni', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_listino_versioni_a10_stati_doc_lis_cdf482 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_listino_versioni', 'attivo', 'stato_a_id', 'id')` |
| trg_transizioni_stati_listino_versioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_listino_versioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
