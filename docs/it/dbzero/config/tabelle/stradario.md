{% include-markdown "it/dbzero/config/manual/stradario.md" %}
# 📚 Tabella `stradario`

> 📝 **Descrizione**
>
> Stradario con CAP obbligatorio esclusivamente sulle vie

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| comune_id | integer | NO |  |
| stradario_generale_id | integer | NO |  |
| geoloc | geometry(Point,4326) | YES |  |
| meta | jsonb | YES |  |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | text | YES | CURRENT_USER |
| data_update | timestamp with time zone | YES | now() |
| user_update | text | NO | CURRENT_USER |
| codice_postale_id | integer | NO |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |
| obsoleto_dal | date | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stradario_codice_postale_id | codice_postale_id |
| FOREIGN KEY | fk_stradario_comune_id | comune_id |
| FOREIGN KEY | fk_stradario_stradario_generale_id | stradario_generale_id |
| PRIMARY KEY | pk_stradario | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_stradario_codice_postale_id | `CREATE INDEX ix_config_stradario_codice_postale_id ON config.stradario USING btree (codice_postale_id)` |
| ix_config_stradario_comune_id | `CREATE INDEX ix_config_stradario_comune_id ON config.stradario USING btree (comune_id)` |
| ix_config_stradario_stradario_generale_id | `CREATE INDEX ix_config_stradario_stradario_generale_id ON config.stradario USING btree (stradario_generale_id)` |
| ix_stradario_geoloc | `CREATE INDEX ix_stradario_geoloc ON config.stradario USING btree (geoloc)` |
| pk_stradario | `CREATE UNIQUE INDEX pk_stradario ON config.stradario USING btree (id)` |
| uq_stradario_comune_stradario_gen_cp | `CREATE UNIQUE INDEX uq_stradario_comune_stradario_gen_cp ON config.stradario USING btree (comune_id, stradario_generale_id, codice_postale_id) WHERE (obsoleto_dal IS NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stradario_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stradario_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stradario_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stradario_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stradario_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('stradario_id')` |
| trg_stradario_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('stradario_id')` |

---
{% include-markdown "signature-core.md" %}
