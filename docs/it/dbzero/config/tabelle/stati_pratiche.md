# 📚 Tabella `stati_pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('stati_pratiche_id_seq'::regclass) |
| cod_stato | character varying | NO |  |
| descrizione | character varying | NO |  |
| cd_int_stato | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_pratiche | id |
| UNIQUE | uq_stati_pratiche_cd_int_stato | cd_int_stato |
| UNIQUE | uq_stati_pratiche_cod_stato | cod_stato |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_pratiche | `CREATE UNIQUE INDEX pk_stati_pratiche ON config.stati_pratiche USING btree (id)` |
| uq_stati_pratiche_cd_int_stato | `CREATE UNIQUE INDEX uq_stati_pratiche_cd_int_stato ON config.stati_pratiche USING btree (cd_int_stato)` |
| uq_stati_pratiche_cod_stato | `CREATE UNIQUE INDEX uq_stati_pratiche_cod_stato ON config.stati_pratiche USING btree (cod_stato)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_pratiche_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cod_int_stato', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_stati_pratiche_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
