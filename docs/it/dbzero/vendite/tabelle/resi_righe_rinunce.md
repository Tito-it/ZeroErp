{% include-markdown "it/dbzero/vendite/manual/resi_righe_rinunce.md" %}
# 📚 Tabella `resi_righe_rinunce`

> 📝 **Descrizione**
>
> Quota di una riga reso per ri-consegna dichiarata DEFINITIVA: la merce non tornera' al cliente (brief-db-chiusura-riconsegna-reso-definitivo S4.1). Gemella di resi_righe_riconsegne; rinunce parziali e ripetute, nessuna UNIQUE per costruzione (l'invariante quantita &gt;= Sigma riconsegnate + Sigma rinunciate lo tiene il guard). Non muove numeri: ne' il contatore merce ne' l'importo dell'accredito cambiano - cambia la NATURA della quota pendente, che chiude il residuo ordine e rende l'accredito DOVUTO. La merce resta materialmente al fornitore: senza modulo magazzino non c'e' nulla da movimentare (S5.4). rev 2026-07-26.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| resi_riga_id | bigint | NO |  |
| qta | numeric | NO |  |
| note | character varying(255) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_resi_righe_rinunce_qta_finito |  |
| CHECK | k_resi_rinunce_qta_pos |  |
| FOREIGN KEY | fk_resi_rinunce_resi_riga | resi_riga_id |
| PRIMARY KEY | pk_resi_rinunce | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_rinunce_resi_riga_id | `CREATE INDEX ix_resi_rinunce_resi_riga_id ON vendite.resi_righe_rinunce USING btree (resi_riga_id)` |
| pk_resi_rinunce | `CREATE UNIQUE INDEX pk_resi_rinunce ON vendite.resi_righe_rinunce USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_rinunce_a10_resi_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_rinunce_a10_resi_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_rinunce_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_rinunce_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_rinunce_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_rinunce_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_rinunce_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_rinunce_id')` |
| trg_resi_righe_rinunce_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_rinunce_id')` |
| trg_resi_rinunce_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_rinunce_guard()` |
| trg_resi_rinunce_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_rinunce_guard()` |

---
{% include-markdown "signature-core.md" %}
