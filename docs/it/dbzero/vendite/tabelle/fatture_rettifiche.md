{% include-markdown "it/dbzero/vendite/manual/fatture_rettifiche.md" %}
# 📚 Tabella `fatture_rettifiche`

> 📝 **Descrizione**
>
> Link fra documenti rettificanti e documenti rettificati (supporto N:N).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| rettificata_id | bigint | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_ret_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_ret_rettificata | rettificata_id |
| PRIMARY KEY | pk_fatture_rettifiche | id |
| UNIQUE | uq_fatture_rettifiche_pair | fattura_id, rettificata_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_fatture_rettifiche_rettificata_id | `CREATE INDEX ix_vendite_fatture_rettifiche_rettificata_id ON vendite.fatture_rettifiche USING btree (rettificata_id)` |
| pk_fatture_rettifiche | `CREATE UNIQUE INDEX pk_fatture_rettifiche ON vendite.fatture_rettifiche USING btree (id)` |
| uq_fatture_rettifiche_pair | `CREATE UNIQUE INDEX uq_fatture_rettifiche_pair ON vendite.fatture_rettifiche USING btree (fattura_id, rettificata_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_rettifiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_rettifiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
