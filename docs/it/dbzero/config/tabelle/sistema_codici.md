{% include-markdown "it/dbzero/config/manual/sistema_codici.md" %}
# 📚 Tabella `sistema_codici`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_tipo | text | NO |  |
| descrizione | text | YES |  |
| prefisso | text | NO |  |
| separatore | text | YES |  |
| lunghezza_numero | integer | NO | 6 |
| usa_sequenza | boolean | YES | true |
| nome_sequenza | text | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | text | YES | 'CURRENT_USER'::text |
| data_update | timestamp with time zone | YES | now() |
| user_update | text | YES | 'CURRENT_USER'::text |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_sistema_codici | id |
| UNIQUE | uq_sistema_codici_codice_tipo | codice_tipo |
| UNIQUE | uq_sistema_codici_prefisso | prefisso |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_sistema_codici | `CREATE UNIQUE INDEX pk_sistema_codici ON config.sistema_codici USING btree (id)` |
| uq_sistema_codici_codice_tipo | `CREATE UNIQUE INDEX uq_sistema_codici_codice_tipo ON config.sistema_codici USING btree (codice_tipo)` |
| uq_sistema_codici_prefisso | `CREATE UNIQUE INDEX uq_sistema_codici_prefisso ON config.sistema_codici USING btree (prefisso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sistema_codici_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_sistema_codici_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_sistema_codici_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
