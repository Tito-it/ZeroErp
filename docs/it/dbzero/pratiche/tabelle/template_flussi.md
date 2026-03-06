{% include-markdown "it/dbzero/pratiche/manual/template_flussi.md" %}
# 📚 Tabella `template_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| tipo_prestazione_id | integer | NO |  |
| handler_id | integer | YES |  |
| codice | character varying | NO |  |
| descrizione | text | NO |  |
| sequenza | integer | NO | 0 |
| obbligatorio | boolean | NO | false |
| direzione | character varying | NO | 'INTERNA'::character varying |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| handler_params | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_flussi_direzione |  |
| FOREIGN KEY | fk_template_flussi_handler | handler_id |
| FOREIGN KEY | fk_template_flussi_tipo_prestazione | tipo_prestazione_id |
| PRIMARY KEY | pk_pratiche_template_flussi | id |
| UNIQUE | uq_pratiche_template_flussi_tipo_codice | tipo_prestazione_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_template_flussi | `CREATE UNIQUE INDEX pk_pratiche_template_flussi ON pratiche.template_flussi USING btree (id)` |
| uq_pratiche_template_flussi_tipo_codice | `CREATE UNIQUE INDEX uq_pratiche_template_flussi_tipo_codice ON pratiche.template_flussi USING btree (tipo_prestazione_id, codice)` |

---
{% include-markdown "signature-core.md" %}
