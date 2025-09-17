{% include-markdown "it/dbzero/config/manual/stati_cliente.md" %}
# 📚 Tabella `stati_cliente`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | character | NO |  |
| descrizione | character varying | NO | ''::character varying |
| descrizione_breve | character | NO |  |
| check_lettura | character | NO | 'S'::bpchar |
| abilita_fattura | character | NO | 'S'::bpchar |
| codice | character | NO | 'IS'::bpchar |
| stato_cliente_ia | character | NO | 'I'::bpchar |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | 'CURRENT_USER'::text |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | 'CURRENT_USER'::text |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_cliente | id |
| UNIQUE | uq_stati_cli_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_stati_cli_desc | `CREATE INDEX ix_config_stati_cli_desc ON config.stati_cliente USING btree (descrizione)` |
| pk_stati_cliente | `CREATE UNIQUE INDEX pk_stati_cliente ON config.stati_cliente USING btree (id)` |
| uq_stati_cli_codice_interno | `CREATE UNIQUE INDEX uq_stati_cli_codice_interno ON config.stati_cliente USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_cliente_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_stati_cliente_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
