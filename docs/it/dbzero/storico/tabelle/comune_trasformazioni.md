# 📚 Tabella `comune_trasformazioni`

> 📝 **Descrizione**
>
> Trasformazioni tra comuni: accorpamenti e scissioni

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| id_comune_orig | integer | NO |  |
| id_comune_nuovo | integer | NO |  |
| tipo_evento | character | NO |  |
| data_evento | date | NO |  |
| note | text | YES |  |
| data_insert | timestamp without time zone | YES | now() |
| user_insert | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_comune_trasformazioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_comune_trasformazioni_nuovo | `CREATE INDEX ix_comune_trasformazioni_nuovo ON storico.comune_trasformazioni USING btree (id_comune_nuovo)` |
| ix_comune_trasformazioni_orig | `CREATE INDEX ix_comune_trasformazioni_orig ON storico.comune_trasformazioni USING btree (id_comune_orig)` |
| pk_comune_trasformazioni | `CREATE UNIQUE INDEX pk_comune_trasformazioni ON storico.comune_trasformazioni USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
