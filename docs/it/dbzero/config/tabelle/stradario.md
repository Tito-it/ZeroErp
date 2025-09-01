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
| data_insert | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |
| data_update | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| user_update | character varying | YES | CURRENT_USER |
| codice_postale_id | integer | NO |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_geoloc_srid |  |
| FOREIGN KEY | fk_stradario_codice_postale_id | codice_postale_id |
| FOREIGN KEY | fk_stradario_comune_id | comune_id |
| FOREIGN KEY | fk_stradario_stradario_generale_id | stradario_generale_id |
| PRIMARY KEY | pk_stradario | id |
| UNIQUE | uq_stradario_comune_stradario_gen_cp | codice_postale_id, stradario_generale_id, comune_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stradario_codice_postale_id | `CREATE INDEX ix_stradario_codice_postale_id ON config.stradario USING btree (codice_postale_id)` |
| ix_stradario_comune_id | `CREATE INDEX ix_stradario_comune_id ON config.stradario USING btree (comune_id)` |
| ix_stradario_geoloc | `CREATE INDEX ix_stradario_geoloc ON config.stradario USING gist (geoloc)` |
| ix_stradario_stradario_generale_id | `CREATE INDEX ix_stradario_stradario_generale_id ON config.stradario USING btree (stradario_generale_id)` |
| pk_stradario | `CREATE UNIQUE INDEX pk_stradario ON config.stradario USING btree (id)` |
| uq_stradario_comune_stradario_gen_cp | `CREATE UNIQUE INDEX uq_stradario_comune_stradario_gen_cp ON config.stradario USING btree (comune_id, stradario_generale_id, codice_postale_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stradario_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stradario_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_stradario_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_stradario_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('stradario_id')` |
| trg_z90_stradario_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('stradario_id')` |
| trgx_z90_stradario_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('stradario_id')` |
| trgx_z90_stradario_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('stradario_id')` |

---
{% include-markdown "signature-core.md" %}
