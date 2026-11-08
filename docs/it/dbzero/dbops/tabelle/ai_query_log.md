{% include-markdown "it/dbzero/dbops/manual/ai_query_log.md" %}
# 📚 Tabella `ai_query_log`

> 📝 **Descrizione**
>
> Registro delle interazioni con l'assistente AI: il testo inviato dall'utente, gli strumenti invocati, la risposta, token, durata e provider. Il backend la scrive solo in INSERT. Scade: cleanup_at nasce con la riga (data_insert + il termine della regola CLEANUP_AT della tabella in dbops.automation_rules_tbl, 90 giorni) e il purge delle automazioni cancella le righe scadute; la tabella e' nell'ambito di dbops.automation_scope.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| request_id | uuid | NO |  |
| user_id | integer | NO |  |
| input_text | text | NO |  |
| tools_called | jsonb | YES |  |
| response_text | text | YES |  |
| provider | character varying(50) | NO |  |
| model | character varying(100) | NO |  |
| tokens_input | integer | YES |  |
| tokens_output | integer | YES |  |
| duration_ms | integer | YES |  |
| error_code | character varying(100) | YES |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_ai_query_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ai_query_log_cleanup_at | `CREATE INDEX ix_ai_query_log_cleanup_at ON dbops.ai_query_log USING btree (cleanup_at)` |
| ix_ai_query_log_data_insert | `CREATE INDEX ix_ai_query_log_data_insert ON dbops.ai_query_log USING btree (data_insert DESC)` |
| ix_ai_query_log_request_id | `CREATE INDEX ix_ai_query_log_request_id ON dbops.ai_query_log USING btree (request_id)` |
| ix_ai_query_log_user_id | `CREATE INDEX ix_ai_query_log_user_id ON dbops.ai_query_log USING btree (user_id)` |
| pk_ai_query_log | `CREATE UNIQUE INDEX pk_ai_query_log ON dbops.ai_query_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ai_query_log_m50_cleanup_at_ins | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_cleanup_at_alla_nascita()` |

---
{% include-markdown "signature-core.md" %}
