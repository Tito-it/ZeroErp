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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ddt_indirizzo_ordine | ddt_id |
| FOREIGN KEY | fk_ddt_indirizzo_tipo | tipo_indirizzo_id |
| PRIMARY KEY | pk_ddt_indirizzi | id |
| UNIQUE | uq_ddt_indirizzi_uno_per_tipo | tipo_indirizzo_id, ddt_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ddt_indirizzo_ordine | `CREATE INDEX ix_ddt_indirizzo_ordine ON acquisti.ddt_indirizzi USING btree (ddt_id)` |
| pk_ddt_indirizzi | `CREATE UNIQUE INDEX pk_ddt_indirizzi ON acquisti.ddt_indirizzi USING btree (id)` |
| uq_ddt_indirizzi_uno_per_tipo | `CREATE UNIQUE INDEX uq_ddt_indirizzi_uno_per_tipo ON acquisti.ddt_indirizzi USING btree (ddt_id, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION acquisti.trgfn_ddt_indirizzi_only_allowed_tipi()` |
| trg_ddt_indirizzi_a10_only_allowed_tipi_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION acquisti.trgfn_ddt_indirizzi_only_allowed_tipi()` |

---
{% include-markdown "signature-core.md" %}
