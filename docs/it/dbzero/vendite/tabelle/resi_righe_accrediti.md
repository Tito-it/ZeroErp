{% include-markdown "it/dbzero/vendite/manual/resi_righe_accrediti.md" %}
# 📚 Tabella `resi_righe_accrediti`

> 📝 **Descrizione**
>
> Il TERZO LATO delle uscite di una riga di reso, accanto a vendite.resi_righe_riconsegne (la merce torna al cliente) e vendite.resi_righe_rinunce (non torna piu'): qui si registra che una quota e' stata ACCREDITATA, contro una precisa riga di fattura. ⭐ Non e' un'eccezione al modello, ne completa una simmetria che la doc delle due sorelle nominava gia'. Popolata SOLO da vendite.fn_accredita_riga_reso. Serve tre cose insieme: (1) il FATTO, con chi/quando/quanto/contro cosa — una storia che altrimenti non esisterebbe da nessuna parte, perche' la rettifica in commessa dice COSA e' stato fatto, non A FRONTE DI COSA; (2) il PRESIDIO contro il doppio accredito, che chiude la finestra fra il verbo e l'emissione: in quel lasso l'attivita' fatturabile non esiste ancora, il conto della merce non e' cambiato e la riga e' ANCORA IN CODA, quindi un secondo click sarebbe coerente col conto; (3) il `gia_accreditato` che la coda espone in riga, cosi' il frontend gate il bottone su un dato che ha gia' invece di chiamare una capability per riga. Due tetti, imposti dal guard e non da un vincolo di colonna (le somme non si esprimono con una UNIQUE): Sigma qta per riga di reso &lt;= accredito dovuto (la MERCE), Sigma qta per riga di fattura &lt;= qta della riga (il DOCUMENTO). Due misure in lingue diverse che devono concordare: quando divergono c'e' un difetto da guardare, non un numero di cui fidarsi. brief-design-note-credito-resi D-NC-10 (S12.6-ter). rev 2026-08-18.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| resi_riga_id | bigint | NO |  |
| fattura_riga_rettificata_id | bigint | NO |  |
| qta | numeric | NO |  |
| qta_partita | numeric | NO |  |
| gruppo | character varying(128) | NO |  |
| commessa_attivita_id | bigint | NO |  |
| note | character varying(255) | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | k_resi_accrediti_qta_partita_pos |  |
| CHECK | k_resi_accrediti_qta_pos |  |
| FOREIGN KEY | fk_resi_accrediti_commessa_attivita | commessa_attivita_id |
| FOREIGN KEY | fk_resi_accrediti_fattura_riga | fattura_riga_rettificata_id |
| FOREIGN KEY | fk_resi_accrediti_resi_riga | resi_riga_id |
| PRIMARY KEY | pk_resi_accrediti | id |
| UNIQUE | uq_resi_accrediti_pair | resi_riga_id, fattura_riga_rettificata_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_accrediti_commessa_attivita_id | `CREATE INDEX ix_resi_accrediti_commessa_attivita_id ON vendite.resi_righe_accrediti USING btree (commessa_attivita_id)` |
| ix_resi_accrediti_fattura_riga_rettificata_id | `CREATE INDEX ix_resi_accrediti_fattura_riga_rettificata_id ON vendite.resi_righe_accrediti USING btree (fattura_riga_rettificata_id)` |
| pk_resi_accrediti | `CREATE UNIQUE INDEX pk_resi_accrediti ON vendite.resi_righe_accrediti USING btree (id)` |
| uq_resi_accrediti_pair | `CREATE UNIQUE INDEX uq_resi_accrediti_pair ON vendite.resi_righe_accrediti USING btree (resi_riga_id, fattura_riga_rettificata_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_accrediti_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_resi_accrediti_guard()` |
| trg_resi_accrediti_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_resi_accrediti_guard()` |
| trg_resi_righe_accrediti_a10_resi_righe_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_accrediti_a10_resi_righe_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'resi_righe', 'attivo', 'resi_riga_id', 'id')` |
| trg_resi_righe_accrediti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_accrediti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resi_righe_accrediti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_accrediti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_accrediti_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_accrediti_id')` |
| trg_resi_righe_accrediti_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('resi_righe_accrediti_id')` |

---
{% include-markdown "signature-core.md" %}
