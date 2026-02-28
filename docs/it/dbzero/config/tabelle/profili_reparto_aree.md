{% include-markdown "it/dbzero/config/manual/profili_reparto_aree.md" %}
# 📚 Tabella `profili_reparto_aree`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| unita_organizzativa_id | integer | NO |  |
| area_id | integer | NO |  |
| livello | USER-DEFINED | NO | 'BLOCCATO'::config.livello_accesso |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_profili_reparto_aree_area | area_id |
| FOREIGN KEY | fk_profili_reparto_aree_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_profili_reparto_aree | id |
| UNIQUE | uq_profili_reparto_aree_uo_area | unita_organizzativa_id, area_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_profili_reparto_aree_area_id | `CREATE INDEX ix_profili_reparto_aree_area_id ON config.profili_reparto_aree USING btree (area_id)` |
| ix_profili_reparto_aree_uo_id | `CREATE INDEX ix_profili_reparto_aree_uo_id ON config.profili_reparto_aree USING btree (unita_organizzativa_id)` |
| pk_profili_reparto_aree | `CREATE UNIQUE INDEX pk_profili_reparto_aree ON config.profili_reparto_aree USING btree (id)` |
| uq_profili_reparto_aree_uo_area | `CREATE UNIQUE INDEX uq_profili_reparto_aree_uo_area ON config.profili_reparto_aree USING btree (unita_organizzativa_id, area_id)` |

---
{% include-markdown "signature-core.md" %}
