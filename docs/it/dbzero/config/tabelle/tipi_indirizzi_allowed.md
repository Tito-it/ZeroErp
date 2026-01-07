{% include-markdown "it/dbzero/config/manual/tipi_indirizzi_allowed.md" %}
# 📚 Tabella `tipi_indirizzi_allowed`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| ambito | text | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| obbligatorio | boolean | NO | false |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_indirizzi_ambito |  |
| FOREIGN KEY | fk_config_tipi_indirizzi | tipo_indirizzo_id |
| PRIMARY KEY | pk_tipi_indirizzi_allowed | ambito, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_indirizzi_allowed_ambito_attivi | `CREATE INDEX ix_tipi_indirizzi_allowed_ambito_attivi ON config.tipi_indirizzi_allowed USING btree (ambito)` |
| pk_tipi_indirizzi_allowed | `CREATE UNIQUE INDEX pk_tipi_indirizzi_allowed ON config.tipi_indirizzi_allowed USING btree (ambito, tipo_indirizzo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_indirizzi_allowed_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
