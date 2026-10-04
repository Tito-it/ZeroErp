{% include-markdown "it/dbzero/storico/manual/stradario_trasformazioni.md" %}
# 📚 Tabella `stradario_trasformazioni`

> 📝 **Descrizione**
>
> Trasformazioni storiche delle vie (stradario)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| via_id_orig | integer | NO |  |
| via_id_nuovo | integer | NO |  |
| tipo_evento | character(1) | NO |  |
| data_evento | date | NO |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stradario_trasformazioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stradario_trasf_via_orig | `CREATE INDEX ix_stradario_trasf_via_orig ON storico.stradario_trasformazioni USING btree (via_id_orig)` |
| pk_stradario_trasformazioni | `CREATE UNIQUE INDEX pk_stradario_trasformazioni ON storico.stradario_trasformazioni USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
