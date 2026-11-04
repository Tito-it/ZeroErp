{% include-markdown "it/dbzero/config/manual/stati_cliente.md" %}
# 📚 Tabella `stati_cliente`

> 📝 **Descrizione**
>
> Stati cliente (AT=Attivo, IS=Istanza, CH=Chiuso, SM=Sosp.Morosita, AN=Annullato, CE=Cess.Amministrativa, LE=Legale)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | character varying(80) | NO | ''::character varying |
| descrizione_breve | character varying(20) | NO |  |
| check_lettura | character(1) | NO | 'S'::bpchar |
| abilita_fattura | character(1) | NO | 'S'::bpchar |
| codice | character varying(50) | NO | 'IS'::bpchar |
| stato_cliente_ia | character(1) | NO | 'I'::bpchar |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_cliente_descrizione_breve_non_vuota |  |
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
| trg_stati_cliente_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_cliente_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_cliente_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_cliente_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_cliente_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
