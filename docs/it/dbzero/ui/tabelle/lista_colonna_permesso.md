{% include-markdown "it/dbzero/ui/manual/lista_colonna_permesso.md" %}

# 📚 Tabella `lista_colonna_permesso`

## 🗂️ Campi principali

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | identity |
| colonna_id | integer | NO | |
| profilo_accesso_id | integer | NO | |
| livello_accesso | config.livello_accesso | NO | |
| data_insert | timestamp | NO | now() |
| user_insert | character varying(80) | NO | |
| data_update | timestamp | YES | |
| user_update | character varying(80) | YES | |

## 🔒 Vincoli

| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk (id) | id |
| UNIQUE | uq_ui_lista_colonna_permesso_col_profilo | colonna_id, profilo_accesso_id |
| FOREIGN KEY | fk_lista_colonna_permesso_lista_colonna | colonna_id → ui.lista_colonna(id) ON DELETE CASCADE |
| FOREIGN KEY | fk_lista_colonna_permesso_profili_accesso | profilo_accesso_id → config.profili_accesso(id) |

## 📑 Indici

| Nome | Definizione |
|------|-------------|
| uq_ui_lista_colonna_permesso_col_profilo | `CREATE UNIQUE INDEX ON ui.lista_colonna_permesso USING btree (colonna_id, profilo_accesso_id)` |
| ix_ui_lista_colonna_permesso_profilo_accesso_id | `CREATE INDEX ON ui.lista_colonna_permesso USING btree (profilo_accesso_id)` |

---
{% include-markdown "signature-core.md" %}
