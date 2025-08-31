{% include-markdown "it/dbzero/storico/manual/soggetti.md" %}
# 📚 Tabella `soggetti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| soggetto_id | uuid | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_soggetti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_soggetti_soggetto_id | `CREATE INDEX ix_soggetti_soggetto_id ON storico.soggetti USING btree (soggetto_id)` |
| ix_storico_soggetti_soggetto_valid_from_desc | `CREATE INDEX ix_storico_soggetti_soggetto_valid_from_desc ON storico.soggetti USING btree (soggetto_id, valid_from DESC)` |
| pk_storico_soggetti | `CREATE UNIQUE INDEX pk_storico_soggetti ON storico.soggetti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
