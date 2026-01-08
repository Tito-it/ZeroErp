{% include-markdown "it/dbzero/config/manual/titoli_cortesia.md" %}
# 📚 Tabella `titoli_cortesia`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| descrizione | text | NO |  |
| descrizione_breve | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_contatto_ruolo | id |
| UNIQUE | uq_contatto_ruolo_contatto_ruolo_descrizione | descrizione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_contatto_ruolo | `CREATE UNIQUE INDEX pk_contatto_ruolo ON config.titoli_cortesia USING btree (id)` |
| uq_contatto_ruolo_contatto_ruolo_descrizione | `CREATE UNIQUE INDEX uq_contatto_ruolo_contatto_ruolo_descrizione ON config.titoli_cortesia USING btree (descrizione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_titoli_cortesia_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
