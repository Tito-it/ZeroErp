{% include-markdown "it/dbzero/vendite/manual/fatture_scadenze.md" %}
# 📚 Tabella `fatture_scadenze`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| numero_rata | smallint | NO |  |
| data_scadenza | date | NO |  |
| importo | numeric | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_scadenze_importo_pos |  |
| FOREIGN KEY | fk_fatture_scadenze_fattura | fattura_id |
| PRIMARY KEY | pk_fatture_scadenze | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_scadenze_data | `CREATE INDEX ix_fatture_scadenze_data ON vendite.fatture_scadenze USING btree (data_scadenza)` |
| pk_fatture_scadenze | `CREATE UNIQUE INDEX pk_fatture_scadenze ON vendite.fatture_scadenze USING btree (id)` |
| uq_fatture_scadenze_nr | `CREATE UNIQUE INDEX uq_fatture_scadenze_nr ON vendite.fatture_scadenze USING btree (fattura_id, numero_rata)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_scadenze_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_scadenze_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_scadenze_id')` |
| trg_fatture_scadenze_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('fatture_scadenze_id')` |

---
{% include-markdown "signature-core.md" %}
