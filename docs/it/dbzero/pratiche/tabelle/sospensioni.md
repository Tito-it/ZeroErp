{% include-markdown "it/dbzero/pratiche/manual/sospensioni.md" %}
# 📚 Tabella `sospensioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| flusso_id | bigint | YES |  |
| data_inizio | timestamp with time zone | NO | now() |
| data_fine | timestamp with time zone | YES |  |
| data_riattivazione_prevista | date | YES |  |
| motivo | text | NO |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sospensioni_data_fine |  |
| FOREIGN KEY | fk_sospensioni_flusso | flusso_id |
| FOREIGN KEY | fk_sospensioni_pratica | pratica_id |
| PRIMARY KEY | pk_pratiche_sospensioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_sospensioni | `CREATE UNIQUE INDEX pk_pratiche_sospensioni ON pratiche.sospensioni USING btree (id)` |
| uq_sospensioni_attiva_flusso | `CREATE UNIQUE INDEX uq_sospensioni_attiva_flusso ON pratiche.sospensioni USING btree (pratica_id, flusso_id) WHERE ((data_fine IS NULL) AND (flusso_id IS NOT NULL))` |
| uq_sospensioni_attiva_pratica | `CREATE UNIQUE INDEX uq_sospensioni_attiva_pratica ON pratiche.sospensioni USING btree (pratica_id) WHERE ((data_fine IS NULL) AND (flusso_id IS NULL))` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sospensioni_a10_guard_coerenza_flusso_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()` |
| trg_sospensioni_a10_guard_coerenza_flusso_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()` |
| trg_sospensioni_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_sospensioni_giornale_ins()` |
| trg_sospensioni_z90_giornale_riattivazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_sospensioni_giornale_riattivazione()` |
| trg_sospensioni_z90_propaga_riattivazione_upd | AFTER | UPDATE | `EXECUTE FUNCTION pratiche.trgfn_sospensioni_riattiva()` |
| trg_sospensioni_z90_propaga_sospensione_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_sospensioni_propaga()` |

---
{% include-markdown "signature-core.md" %}
