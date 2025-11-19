{% include-markdown "it/dbzero/config/manual/stradario.md" %}
# 📚 Tabella `stradario`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| comune_id | integer | NO |  |
| stradario_generale_id | integer | NO |  |
| geoloc | USER-DEFINED | YES |  |
| extra_info | jsonb | YES |  |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | character varying | YES | CURRENT_USER |
| data_update | timestamp with time zone | YES | now() |
| user_update | character varying | YES | CURRENT_USER |
| codice_postale_id | integer | NO |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stradario_codice_postale_id | codice_postale_id |
| FOREIGN KEY | fk_stradario_comune_id | comune_id |
| FOREIGN KEY | fk_stradario_stradario_generale_id | stradario_generale_id |
| PRIMARY KEY | pk_stradario | id |
| UNIQUE | uq_stradario_comune_stradario_gen_cp | stradario_generale_id, comune_id, codice_postale_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stradario_codice_postale_id | `CREATE INDEX ix_stradario_codice_postale_id ON config.stradario USING btree (codice_postale_id)` |
| ix_stradario_comune | `CREATE INDEX ix_stradario_comune ON config.stradario USING btree (comune_id)` |
| ix_stradario_geoloc | `CREATE INDEX ix_stradario_geoloc ON config.stradario USING btree (geoloc)` |
| ix_stradario_stradario_generale_id | `CREATE INDEX ix_stradario_stradario_generale_id ON config.stradario USING btree (stradario_generale_id)` |
| pk_stradario | `CREATE UNIQUE INDEX pk_stradario ON config.stradario USING btree (id)` |
| uq_stradario_comune_stradario_gen_cp | `CREATE UNIQUE INDEX uq_stradario_comune_stradario_gen_cp ON config.stradario USING btree (comune_id, stradario_generale_id, codice_postale_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stradario_ins_upd_tx_id_managed | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stradario_ins_upd_tx_id_managed | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stradario_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stradario_z90_upd_dlt_storico_generic | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('stradario_id')` |
| trg_stradario_z90_upd_dlt_storico_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('stradario_id')` |

---
{% include-markdown "signature-core.md" %}
