{% include-markdown "it/dbzero/config/manual/modi_approvvigionamento.md" %}
# 📚 Tabella `modi_approvvigionamento`

> 📝 **Descrizione**
>
> Modo di approvvigionamento di un articolo: DA DOVE arriva la merce promessa (ACQUISTO: la compro; PRODUZIONE: la faccio; STOCK: c'e' a magazzino; NON_APPLICABILE: prestazione, non c'e' merce). Dimensione ORTOGONALE a config.nature_vendita, che dice invece DOVE VA la riga venduta (ordine, commessa, contratto): un assemblato puo' essere comprato finito, un articolo semplice prodotto. Letto da catalogo.articoli.modo_approvvigionamento_id, con default ACQUISTO (decisione di Tid, 2026-09-02). E' la colonna che rende ponibile la domanda «questa riga richiede produzione?» e il perno di qualunque proposta d'acquisto. Vocabolario modificabile dall'operatore (codice, descrizione); codice_interno e' la chiave su cui il codice confronta, immutabile via lock automatico. Brief: brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezione 3.2.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_modi_approvvigionamento_codice_interno_non_vuoto |  |
| PRIMARY KEY | pk_modi_approvvigionamento | id |
| UNIQUE | uq_modi_approvvigionamento_codice | codice |
| UNIQUE | uq_modi_approvvigionamento_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_modi_approvvigionamento | `CREATE UNIQUE INDEX pk_modi_approvvigionamento ON config.modi_approvvigionamento USING btree (id)` |
| uq_modi_approvvigionamento_codice | `CREATE UNIQUE INDEX uq_modi_approvvigionamento_codice ON config.modi_approvvigionamento USING btree (codice)` |
| uq_modi_approvvigionamento_codice_interno | `CREATE UNIQUE INDEX uq_modi_approvvigionamento_codice_interno ON config.modi_approvvigionamento USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_modi_approvvigionamento_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'modo_approvvigionamento_id', 'id', 'attivo')` |
| trg_modi_approvvigionamento_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_modi_approvvigionamento_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_modi_approvvigionamento_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_modi_approvvigionamento_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_modi_approvvigionamento_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_modi_approvvigionamento_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_modi_approvvigionamento_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
