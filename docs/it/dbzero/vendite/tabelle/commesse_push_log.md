{% include-markdown "it/dbzero/vendite/manual/commesse_push_log.md" %}
# 📚 Tabella `commesse_push_log`

> 📝 **Descrizione**
>
> Registro dei giri dell'orchestratore push commesse. ⭐ Dal 2026-08-22 la riga nasce in TESTA al giro (vendite.fn_start_commessa_push_run, stato IN_ESECUZIONE) e si chiude alla fine (vendite.fn_close_commessa_push_run): prima veniva creata a fine corsa, ed e' il motivo per cui l'evento d'avvio citava entity_id = 0 — un id che non esisteva ancora. Ne discendono tre cose: l'evento d'avvio ha un'entita' vera, il correlation_id del giro ha dove stare prima che il giro produca qualcosa, e un giro INTERROTTO lascia una traccia (la riga rimasta IN_ESECUZIONE). ⚠️ Non e' piu' append-only: la chiusura e' un UPDATE della stessa riga, e non c'e' nessun veto che lo impedisca. ⚠️ E lo stato inter-run ora ESISTE: chi conta i giri deve decidere cosa farne, perche' IN_ESECUZIONE non e' un esito.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| run_at | timestamp with time zone | NO | now() |
| dry_run | boolean | NO | false |
| source_types | ARRAY | YES |  |
| risultato | jsonb | NO | '{}'::jsonb |
| stato | character varying | NO |  |
| durata_ms | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| correlation_id | uuid | YES |  |
| tx_id | uuid | YES |  |
| cleanup_at | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_commesse_push_log_durata_ms |  |
| CHECK | chk_commesse_push_log_stato |  |
| PRIMARY KEY | pk_commesse_push_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_push_log_correlation | `CREATE INDEX ix_commesse_push_log_correlation ON vendite.commesse_push_log USING btree (correlation_id) WHERE (correlation_id IS NOT NULL)` |
| ix_commesse_push_log_run_at | `CREATE INDEX ix_commesse_push_log_run_at ON vendite.commesse_push_log USING btree (run_at)` |
| pk_commesse_push_log | `CREATE UNIQUE INDEX pk_commesse_push_log ON vendite.commesse_push_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_commesse_push_log_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_push_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_commesse_push_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_push_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_commesse_push_log_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
