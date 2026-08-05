# 📚 Tabella `messaggi_errore_codici_legacy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | text | NO |  |
| data_registrazione | date | NO | CURRENT_DATE |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_messaggi_errore_codici_legacy_non_conforme |  |
| PRIMARY KEY | pk_messaggi_errore_codici_legacy | id |
| UNIQUE | uq_messaggi_errore_codici_legacy_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_messaggi_errore_codici_legacy | `CREATE UNIQUE INDEX pk_messaggi_errore_codici_legacy ON dbops.messaggi_errore_codici_legacy USING btree (id)` |
| uq_messaggi_errore_codici_legacy_codice | `CREATE UNIQUE INDEX uq_messaggi_errore_codici_legacy_codice ON dbops.messaggi_errore_codici_legacy USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
