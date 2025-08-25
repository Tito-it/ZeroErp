# 📚 Tabella `sto_demo_storico`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.sto_demo_storico_id_seq'::regclass) |
| sto_demo_id | bigint | NO |  |
| op | text | YES |  |
| ts | timestamp without time zone | YES | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | sto_demo_storico_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| sto_demo_storico_pkey | `CREATE UNIQUE INDEX sto_demo_storico_pkey ON storico.sto_demo_storico USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
