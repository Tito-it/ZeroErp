{% include-markdown "it/dbzero/dbops/manual/audit_sources.md" %}
# 📚 Tabella `audit_sources`

> 📝 **Descrizione**
>
> Catalogo delle sorgenti dell'audit: ogni riga descrive una tabella storico.* navigabile dal drawer di amministrazione (codice, tabella e colonna di chiave della shadow, chiave della label, area funzionale). La legge script.vw_audit_sources, solo le righe attive. Seminata dal CSV di 80_data. Fuori dall'ambito delle automazioni: non porta colonne di tracciamento (tx_id, storicizza, data_update, user_update) che nessuno scriverebbe; lo presidia dbops.vw_marcatori_automazione_senza_esecutore.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| code | text | NO |  |
| storico_table | text | NO |  |
| storico_pk_col | text | NO |  |
| label_key | text | NO |  |
| area_funzionale | text | NO |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_audit_sources | id |
| UNIQUE | uq_audit_sources_code | code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_audit_sources | `CREATE UNIQUE INDEX pk_audit_sources ON dbops.audit_sources USING btree (id)` |
| uq_audit_sources_code | `CREATE UNIQUE INDEX uq_audit_sources_code ON dbops.audit_sources USING btree (code)` |

---
{% include-markdown "signature-core.md" %}
