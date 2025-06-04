{% include-markdown "it/dbzero/config/manual/tipi_ruoli.md" %}
# Tabella `tipi_ruoli`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.tipi_ruoli_id_seq'::regclass) |
| cod_ruolo | character varying | NO |  |
| descrizione | character varying | NO |  |
| cd_int_ruolo | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_ruoli | id |
| UNIQUE | uq_tipi_ruoli_cd_int_ruolo | cd_int_ruolo |
| UNIQUE | uq_tipi_ruoli_cod_ruolo | cod_ruolo |

## Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_ruoli | `CREATE UNIQUE INDEX pk_tipi_ruoli ON config.tipi_ruoli USING btree (id)` |
| uq_tipi_ruoli_cd_int_ruolo | `CREATE UNIQUE INDEX uq_tipi_ruoli_cd_int_ruolo ON config.tipi_ruoli USING btree (cd_int_ruolo)` |
| uq_tipi_ruoli_cod_ruolo | `CREATE UNIQUE INDEX uq_tipi_ruoli_cod_ruolo ON config.tipi_ruoli USING btree (cod_ruolo)` |

## Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_ruoli_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cd_int_ruolo', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_ruoli_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |