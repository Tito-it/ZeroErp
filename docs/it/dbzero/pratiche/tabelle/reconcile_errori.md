{% include-markdown "it/dbzero/pratiche/manual/reconcile_errori.md" %}
# 📚 Tabella `reconcile_errori`

> 📝 **Descrizione**
>
> GUIDA D4/G5: log append-only dei fallimenti di pratiche.fn_reconcile_sorgente inghiottiti dal trigger best-effort G3b (documento sovrano -&gt; nessun rollback del cambio-stato) e degli skip deliberati (tie-break ambiguo). Rende diagnosticabile un avanzamento milestone mancato. Nessuna FK: log resiliente per definizione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| sorgente_tipo_id | bigint | YES |  |
| pratica_id | bigint | YES |  |
| flusso_id | bigint | YES |  |
| errcode | text | YES |  |
| messaggio | text | YES |  |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| sorgente_id | bigint | YES |  |
| sorgente_uid | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_reconcile_errori_sorgente_forma |  |
| PRIMARY KEY | pk_reconcile_errori | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_reconcile_errori_data_insert | `CREATE INDEX ix_reconcile_errori_data_insert ON pratiche.reconcile_errori USING btree (data_insert DESC)` |
| ix_reconcile_errori_sorgente | `CREATE INDEX ix_reconcile_errori_sorgente ON pratiche.reconcile_errori USING btree (sorgente_tipo_id, sorgente_id, sorgente_uid)` |
| pk_reconcile_errori | `CREATE UNIQUE INDEX pk_reconcile_errori ON pratiche.reconcile_errori USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_reconcile_errori_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_reconcile_errori_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
