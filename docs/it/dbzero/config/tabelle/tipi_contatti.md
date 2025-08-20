{% include-markdown "it/dbzero/config/manual/tipi_contatti.md" %}
# 📚 Tabella `tipi_contatti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.tipi_contatti_id_seq'::regclass) |
| descrizione | text | NO |  |
| codice_interno | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |
| codice | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_contatti_descr_non_vuota |  |
| PRIMARY KEY | pk_tipi_contatti | id |
| UNIQUE | uq_tipi_contatti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_contatti | `CREATE UNIQUE INDEX pk_tipi_contatti ON config.tipi_contatti USING btree (id)` |
| uq_tipi_contatti_codice_interno | `CREATE UNIQUE INDEX uq_tipi_contatti_codice_interno ON config.tipi_contatti USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_contatti_upd_lock_codice_interno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_contatti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
