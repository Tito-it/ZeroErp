{% include-markdown "it/dbzero/ui/manual/lista_colonna_permesso.md" %}
# 📚 Tabella `lista_colonna_permesso`

> 📝 **Descrizione**
>
> Permessi a livello colonna per profilo_accesso. deny-list per non sensibili, allow-list per sensibili.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| colonna_id | integer | NO |  |
| profilo_accesso_id | integer | NO |  |
| livello_accesso | config.livello_accesso | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO |  |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |

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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_lista_colonna_permesso_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_lista_colonna_permesso_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
