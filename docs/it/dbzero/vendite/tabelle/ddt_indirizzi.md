{% include-markdown "it/dbzero/vendite/manual/ddt_indirizzi.md" %}
# 📚 Tabella `ddt_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ddt_id | bigint | NO |  |
| tipo_indirizzo_id | bigint | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| origine_indirizzo_id | bigint | YES |  |
| origine_soggetto_ruolo_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ddt_indirizzi_ddt | ddt_id |
| FOREIGN KEY | fk_ddt_indirizzi_origine_indirizzo | origine_indirizzo_id |
| FOREIGN KEY | fk_ddt_indirizzi_origine_sog_ruolo | origine_soggetto_ruolo_id |
| FOREIGN KEY | fk_ddt_indirizzo_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_ddt_indirizzi | id |
| UNIQUE | uq_ddt_indirizzi_uno_per_tipo | tipo_indirizzo_id, ddt_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_indirizzi_ddt | `CREATE INDEX ix_ddt_indirizzi_ddt ON vendite.ddt_indirizzi USING btree (ddt_id)` |
| ix_ddt_indirizzi_origine_indirizzo | `CREATE INDEX ix_ddt_indirizzi_origine_indirizzo ON vendite.ddt_indirizzi USING btree (origine_indirizzo_id)` |
| ix_ddt_indirizzi_origine_sog_ruolo | `CREATE INDEX ix_ddt_indirizzi_origine_sog_ruolo ON vendite.ddt_indirizzi USING btree (origine_soggetto_ruolo_id)` |
| pk_ddt_indirizzi | `CREATE UNIQUE INDEX pk_ddt_indirizzi ON vendite.ddt_indirizzi USING btree (id)` |
| uq_ddt_indirizzi_uno_per_tipo | `CREATE UNIQUE INDEX uq_ddt_indirizzi_uno_per_tipo ON vendite.ddt_indirizzi USING btree (ddt_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('DDT')` |
| trg_ddt_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('DDT')` |

---
{% include-markdown "signature-core.md" %}
