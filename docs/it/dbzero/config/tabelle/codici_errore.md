# 📚 Tabella `codici_errore`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| classe | text | NO |  |
| obsoleto_dal | date | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_codici_errore_codice_non_vuoto |  |
| CHECK | chk_codici_errore_note_una_riga |  |
| FOREIGN KEY | fk_codici_errore_classi_errore | classe |
| PRIMARY KEY | pk_codici_errore | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_codici_errore | `CREATE UNIQUE INDEX pk_codici_errore ON config.codici_errore USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
