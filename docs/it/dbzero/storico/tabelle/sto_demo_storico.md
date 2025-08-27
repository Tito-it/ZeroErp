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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sto_demo_storico_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('sto_demo_storico_id')` |
| trg_sto_demo_storico_upd_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('sto_demo_storico_id')` |

---
{% include-markdown "signature-core.md" %}
