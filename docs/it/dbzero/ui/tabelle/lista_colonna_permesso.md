{% include-markdown "it/dbzero/ui/manual/lista_colonna_permesso.md" %}
# 📚 Tabella `lista_colonna_permesso`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| colonna_id | integer | NO |  |
| profilo_accesso_id | integer | NO |  |
| livello_accesso | USER-DEFINED | NO |  |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO |  |
| data_update | timestamp without time zone | YES |  |
| user_update | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_lista_colonna_permesso_lista_colonna | colonna_id |
| FOREIGN KEY | fk_lista_colonna_permesso_profili_accesso | profilo_accesso_id |
| PRIMARY KEY | lista_colonna_permesso_pkey | id |
| UNIQUE | uq_ui_lista_colonna_permesso_col_profilo | colonna_id, profilo_accesso_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_lista_colonna_permesso_profilo_accesso_id | `CREATE INDEX ix_ui_lista_colonna_permesso_profilo_accesso_id ON ui.lista_colonna_permesso USING btree (profilo_accesso_id)` |
| lista_colonna_permesso_pkey | `CREATE UNIQUE INDEX lista_colonna_permesso_pkey ON ui.lista_colonna_permesso USING btree (id)` |
| uq_ui_lista_colonna_permesso_col_profilo | `CREATE UNIQUE INDEX uq_ui_lista_colonna_permesso_col_profilo ON ui.lista_colonna_permesso USING btree (colonna_id, profilo_accesso_id)` |

---
{% include-markdown "signature-core.md" %}
