# 📚 Tabella `preventivi_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| preventivo_id | bigint | NO |  |
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
| FOREIGN KEY | fk_preventivi_indir_preventivo | preventivo_id |
| FOREIGN KEY | fk_preventivi_indir_tipo | tipo_indirizzo_id |
| FOREIGN KEY | fk_preventivi_indirizzi_origine_indirizzo | origine_indirizzo_id |
| FOREIGN KEY | fk_preventivi_indirizzi_origine_sog_ruolo | origine_soggetto_ruolo_id |
| PRIMARY KEY | pk_preventivi_indirizzi | id |
| UNIQUE | uq_preventivi_indirizzi_uno_per_tipo_ | tipo_indirizzo_id, preventivo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_preventivi_indir_preventivo | `CREATE INDEX ix_preventivi_indir_preventivo ON vendite.preventivi_indirizzi USING btree (preventivo_id)` |
| ix_preventivi_indirizzi_origine_indirizzo | `CREATE INDEX ix_preventivi_indirizzi_origine_indirizzo ON vendite.preventivi_indirizzi USING btree (origine_indirizzo_id)` |
| ix_preventivi_indirizzi_origine_sog_ruolo | `CREATE INDEX ix_preventivi_indirizzi_origine_sog_ruolo ON vendite.preventivi_indirizzi USING btree (origine_soggetto_ruolo_id)` |
| pk_preventivi_indirizzi | `CREATE UNIQUE INDEX pk_preventivi_indirizzi ON vendite.preventivi_indirizzi USING btree (id)` |
| uq_preventivi_indirizzi_uno_per_tipo_ | `CREATE UNIQUE INDEX uq_preventivi_indirizzi_uno_per_tipo_ ON vendite.preventivi_indirizzi USING btree (preventivo_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('PREVENTIVI')` |
| trg_preventivi_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_indirizzi_only_allowed('PREVENTIVI')` |

---
{% include-markdown "signature-core.md" %}
