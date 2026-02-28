{% include-markdown "it/dbzero/config/manual/profili_reparto_azioni.md" %}
# 📚 Tabella `profili_reparto_azioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| unita_organizzativa_id | integer | NO |  |
| azione_id | integer | NO |  |
| abilitata | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_profili_reparto_azioni_azione | azione_id |
| FOREIGN KEY | fk_profili_reparto_azioni_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_profili_reparto_azioni | id |
| UNIQUE | uq_profili_reparto_azioni_uo_azione | unita_organizzativa_id, azione_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_profili_reparto_azioni_azione_id | `CREATE INDEX ix_profili_reparto_azioni_azione_id ON config.profili_reparto_azioni USING btree (azione_id)` |
| ix_profili_reparto_azioni_uo_id | `CREATE INDEX ix_profili_reparto_azioni_uo_id ON config.profili_reparto_azioni USING btree (unita_organizzativa_id)` |
| pk_profili_reparto_azioni | `CREATE UNIQUE INDEX pk_profili_reparto_azioni ON config.profili_reparto_azioni USING btree (id)` |
| uq_profili_reparto_azioni_uo_azione | `CREATE UNIQUE INDEX uq_profili_reparto_azioni_uo_azione ON config.profili_reparto_azioni USING btree (unita_organizzativa_id, azione_id)` |

---
{% include-markdown "signature-core.md" %}
