# 📚 Tabella `classi_errore`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| classe | text | NO |  |
| descrizione | text | NO |  |
| obsoleto_dal | date | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_classi_errore_classe_non_vuota |  |
| PRIMARY KEY | pk_classi_errore | classe |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_classi_errore | `CREATE UNIQUE INDEX pk_classi_errore ON config.classi_errore USING btree (classe)` |

---
{% include-markdown "signature-core.md" %}
