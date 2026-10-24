{% include-markdown "it/dbzero/config/manual/tipi_indirizzi_allowed.md" %}
# 📚 Tabella `tipi_indirizzi_allowed`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| ambito | character varying(50) | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| obbligatorio | boolean | NO | false |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| slot_default | boolean | NO | false |
| ripiego_tipo_indirizzo_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_indirizzi_allowed_ripiego_diverso |  |
| CHECK | chk_tipi_indirizzi_allowed_ripiego_solo_slot |  |
| FOREIGN KEY | fk_config_tipi_indirizzi | tipo_indirizzo_id |
| FOREIGN KEY | fk_tipi_indirizzi_allowed_ripiego | ripiego_tipo_indirizzo_id |
| FOREIGN KEY | fk_tipi_indirizzi_allowed_sorgenti | ambito |
| PRIMARY KEY | pk_tipi_indirizzi_allowed | ambito, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_indirizzi_allowed | `CREATE UNIQUE INDEX pk_tipi_indirizzi_allowed ON config.tipi_indirizzi_allowed USING btree (ambito, tipo_indirizzo_id)` |
| uq_tipi_indirizzi_allowed_slot_default | `CREATE UNIQUE INDEX uq_tipi_indirizzi_allowed_slot_default ON config.tipi_indirizzi_allowed USING btree (ambito) WHERE slot_default` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_indirizzi_allowed_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_indirizzi_allowed_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
