{% include-markdown "it/dbzero/dbops/manual/coda_lavori.md" %}
# 📚 Tabella `coda_lavori`

> 📝 **Descrizione**
>
> Coda dei lavori asincroni sul database, senza broker: una riga e' un lavoro (job_type e payload). Si accoda solo da dbops.fn_accoda_lavoro, che controlla tipo, classe e scope ed e' idempotente sui lavori vivi; il drenatore del backend prende, recupera e chiude i lavori. Un lavoro OPERATORE appartiene a un'azienda (emittente_fiscale_id) e gira con l'identita' catturata nello scope; un lavoro SISTEMA non ha azienda ne' scope. Chi vede quali righe lo dice la policy rls_coda_lavori_ef_perimetro.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| job_type | text | NO |  |
| payload | jsonb | NO | '{}'::jsonb |
| run_as | text | NO |  |
| scope | jsonb | YES |  |
| origine | text | NO | 'API'::text |
| priorita | smallint | NO | 100 |
| stato | text | NO | 'PENDING'::text |
| tentativi | integer | NO | 0 |
| max_tentativi | integer | NO | 5 |
| ultimo_errore | jsonb | YES |  |
| run_after | timestamp with time zone | YES |  |
| claimed_at | timestamp with time zone | YES |  |
| started_at | timestamp with time zone | YES |  |
| ended_at | timestamp with time zone | YES |  |
| job_run_id | bigint | YES |  |
| idempotency_key | text | YES |  |
| result | jsonb | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| archiviato | boolean | NO | false |
| archiviato_il | timestamp with time zone | YES |  |
| archiviato_da | text | YES |  |
| emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_coda_lavori_archiviato_coerente |  |
| CHECK | chk_coda_lavori_archiviato_non_vivo |  |
| CHECK | chk_coda_lavori_emittente_dallo_scope |  |
| CHECK | chk_coda_lavori_max_tentativi |  |
| CHECK | chk_coda_lavori_origine |  |
| CHECK | chk_coda_lavori_run_as |  |
| CHECK | chk_coda_lavori_run_as_emittente |  |
| CHECK | chk_coda_lavori_run_as_scope |  |
| CHECK | chk_coda_lavori_stato |  |
| CHECK | chk_coda_lavori_tentativi |  |
| FOREIGN KEY | fk_coda_lavori_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_coda_lavori_tipo | job_type |
| PRIMARY KEY | pk_coda_lavori | id |
| UNIQUE | uq_coda_lavori_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_coda_lavori_da_lavorare | `CREATE INDEX ix_coda_lavori_da_lavorare ON dbops.coda_lavori USING btree (priorita, id) WHERE (stato = ANY (ARRAY['PENDING'::text, 'IN_CORSO'::text]))` |
| ix_coda_lavori_stato | `CREATE INDEX ix_coda_lavori_stato ON dbops.coda_lavori USING btree (stato)` |
| pk_coda_lavori | `CREATE UNIQUE INDEX pk_coda_lavori ON dbops.coda_lavori USING btree (id)` |
| uq_coda_lavori_uid | `CREATE UNIQUE INDEX uq_coda_lavori_uid ON dbops.coda_lavori USING btree (uid)` |
| uq_coda_lavori_vivo_idem | `CREATE UNIQUE INDEX uq_coda_lavori_vivo_idem ON dbops.coda_lavori USING btree (job_type, idempotency_key) WHERE ((idempotency_key IS NOT NULL) AND (stato = ANY (ARRAY['PENDING'::text, 'IN_CORSO'::text])))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_coda_lavori_a10_archiviazione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_coda_archiviazione()` |
| trg_coda_lavori_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_coda_lavori_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_coda_lavori_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_coda_lavori_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
