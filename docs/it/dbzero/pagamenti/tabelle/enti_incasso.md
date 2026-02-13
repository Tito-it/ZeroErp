{% include-markdown "it/dbzero/pagamenti/manual/enti_incasso.md" %}
# 📚 Tabella `enti_incasso`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | text | NO |  |
| codice_interno | text | YES |  |
| descrizione | text | NO |  |
| tipo | text | NO |  |
| attivo | boolean | NO | true |
| centro_riscossione_id | bigint | YES |  |
| soggetto_ruolo_id | bigint | YES |  |
| bank_branch_id | bigint | YES |  |
| formato_flusso | text | YES |  |
| regole_match | jsonb | NO | '{}'::jsonb |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_enti_incasso_bank_branch_tipo |  |
| CHECK | chk_enti_incasso_tipo |  |
| FOREIGN KEY | fk_enti_incasso_bank_branch | bank_branch_id |
| FOREIGN KEY | fk_enti_incasso_centro_riscossione | centro_riscossione_id |
| FOREIGN KEY | fk_enti_incasso_soggetto_ruolo | soggetto_ruolo_id |
| PRIMARY KEY | pk_enti_incasso | id |
| UNIQUE | uq_enti_incasso_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_enti_incasso | `CREATE UNIQUE INDEX pk_enti_incasso ON pagamenti.enti_incasso USING btree (id)` |
| uq_enti_incasso_codice | `CREATE UNIQUE INDEX uq_enti_incasso_codice ON pagamenti.enti_incasso USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_enti_incasso_guard_psp_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_enti_incasso_guard_psp()` |
| trg_enti_incasso_guard_psp_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_enti_incasso_guard_psp()` |

---
{% include-markdown "signature-core.md" %}
