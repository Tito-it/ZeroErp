{% include-markdown "it/dbzero/vendite/manual/fatture_indirizzi.md" %}
# 📚 Tabella `fatture_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| tipo_indirizzo_id | bigint | NO |  |
| snapshot | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_indir_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_indir_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_fatture_indirizzi | id |
| UNIQUE | uq_fatture_indirizzi_uno_per_tipo_ | fattura_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_indir_fattura | `CREATE INDEX ix_fatture_indir_fattura ON vendite.fatture_indirizzi USING btree (fattura_id)` |
| pk_fatture_indirizzi | `CREATE UNIQUE INDEX pk_fatture_indirizzi ON vendite.fatture_indirizzi USING btree (id)` |
| uq_fatture_indirizzi_uno_per_tipo_ | `CREATE UNIQUE INDEX uq_fatture_indirizzi_uno_per_tipo_ ON vendite.fatture_indirizzi USING btree (fattura_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_fatture_indirizzi_only_allowed_tipi()` |
| trg_fatture_indirizzi_a10_ins_upd_only_allowed_tipi | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_fatture_indirizzi_only_allowed_tipi()` |

---
{% include-markdown "signature-core.md" %}
