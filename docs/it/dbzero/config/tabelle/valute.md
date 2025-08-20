{% include-markdown "it/dbzero/config/manual/valute.md" %}
# 📚 Tabella `valute`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.valute_id_seq'::regclass) |
| codice | character | NO |  |
| iso_code | character | NO |  |
| iso_num_code | smallint | YES |  |
| descrizione | character varying | NO |  |
| simbolo | character varying | NO |  |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_valute | id |
| UNIQUE | uq_iso_code | iso_code |
| UNIQUE | uq_valute_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_valute_desc_valuta | `CREATE INDEX ix_config_valute_desc_valuta ON config.valute USING btree (descrizione)` |
| pk_valute | `CREATE UNIQUE INDEX pk_valute ON config.valute USING btree (id)` |
| uq_iso_code | `CREATE UNIQUE INDEX uq_iso_code ON config.valute USING btree (iso_code)` |
| uq_valute_codice | `CREATE UNIQUE INDEX uq_valute_codice ON config.valute USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_valute_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
