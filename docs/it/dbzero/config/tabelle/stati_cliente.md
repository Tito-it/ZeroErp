# 📚 Tabella `stati_cliente`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('stati_cliente_id_seq'::regclass) |
| cod_int_stato_cliente | character | NO |  |
| desc_stato_cliente | character varying | NO | ''::character varying |
| desc_breve_stato | character | NO |  |
| check_lettura | character | NO | 'S'::bpchar |
| abilita_fattura | character | NO | 'S'::bpchar |
| stato_cliente | character | NO | 'IS'::bpchar |
| stato_cliente_ia | character | NO | 'I'::bpchar |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_cli_abilita_fattura |  |
| CHECK | chk_stati_cli_check_lettura |  |
| CHECK | chk_stati_cli_stato_cliente |  |
| CHECK | chk_stati_cli_stato_cliente_pc |  |
| PRIMARY KEY | pk_stati_cliente | id |
| UNIQUE | uq_stati_cli_cod_unq | cod_int_stato_cliente |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_stati_cli_desc | `CREATE INDEX ix_config_stati_cli_desc ON config.stati_cliente USING btree (desc_stato_cliente)` |
| pk_stati_cliente | `CREATE UNIQUE INDEX pk_stati_cliente ON config.stati_cliente USING btree (id)` |
| uq_stati_cli_cod_unq | `CREATE UNIQUE INDEX uq_stati_cli_cod_unq ON config.stati_cliente USING btree (cod_int_stato_cliente)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_cliente_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cod_int_stato_cliente', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_stati_cliente_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |