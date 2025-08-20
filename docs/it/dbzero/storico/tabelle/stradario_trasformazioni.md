# 📚 Tabella `stradario_trasformazioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('storico.stradario_trasformazioni_id_seq'::regclass) |
| via_id_orig | integer | NO |  |
| via_id_nuovo | integer | NO |  |
| tipo_evento | character | NO |  |
| data_evento | date | NO |  |
| note | text | YES |  |
| data_insert | timestamp without time zone | YES | CURRENT_TIMESTAMP |
| user_insert | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stradario_config | stradario_id, via_id_nuovo |
| FOREIGN KEY | fk_stradario_via_orig_config | via_id_orig |
| PRIMARY KEY | pk_stradario_trasformazioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stradario_trasformazioni_via_id_nuovo | `CREATE INDEX ix_stradario_trasformazioni_via_id_nuovo ON storico.stradario_trasformazioni USING btree (via_id_nuovo)` |
| ix_stradario_trasformazioni_via_id_orig | `CREATE INDEX ix_stradario_trasformazioni_via_id_orig ON storico.stradario_trasformazioni USING btree (via_id_orig)` |
| pk_stradario_trasformazioni | `CREATE UNIQUE INDEX pk_stradario_trasformazioni ON storico.stradario_trasformazioni USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
