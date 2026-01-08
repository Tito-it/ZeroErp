{% include-markdown "it/dbzero/config/manual/comuni.md" %}
# 📚 Tabella `comuni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| descrizione | character varying | NO | ''::character varying |
| provincia_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_provincia | provincia_id |
| PRIMARY KEY | pk_comuni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_descrizione_comune | `CREATE INDEX ix_descrizione_comune ON config.comuni USING btree (descrizione)` |
| ix_provincia_id | `CREATE INDEX ix_provincia_id ON config.comuni USING btree (provincia_id)` |
| pk_comuni | `CREATE UNIQUE INDEX pk_comuni ON config.comuni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_comuni_a10_protect_update_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_comuni_protect_update()` |
| trg_comuni_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_comuni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_comuni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_z90_storico_generic_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('comune_id')` |
| trg_comuni_z90_storico_generic_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('comune_id')` |
| trg_comuni_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('comuni_id')` |
| trg_comuni_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('comuni_id')` |

---
{% include-markdown "signature-core.md" %}
