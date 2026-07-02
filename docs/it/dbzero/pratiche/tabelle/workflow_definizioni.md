# 📚 Tabella `workflow_definizioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| tipo_prestazione_id | integer | NO |  |
| emittente_fiscale_id | bigint | YES |  |
| versione | integer | NO | 1 |
| stato | character varying | NO | 'BOZZA'::character varying |
| preset_origine_id | integer | YES |  |
| versione_origine | integer | YES |  |
| descrizione | text | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_workflow_definizioni_stato |  |
| CHECK | chk_workflow_definizioni_versione |  |
| FOREIGN KEY | fk_workflow_definizioni_emittente | emittente_fiscale_id |
| FOREIGN KEY | fk_workflow_definizioni_preset_origine | preset_origine_id |
| FOREIGN KEY | fk_workflow_definizioni_tipo_prestazione | tipo_prestazione_id |
| PRIMARY KEY | pk_pratiche_workflow_definizioni | id |
| UNIQUE | uq_workflow_definizioni_id_tipo | id, tipo_prestazione_id |
| UNIQUE | uq_workflow_definizioni_scope_versione | tipo_prestazione_id, emittente_fiscale_id, versione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_workflow_definizioni | `CREATE UNIQUE INDEX pk_pratiche_workflow_definizioni ON pratiche.workflow_definizioni USING btree (id)` |
| uq_workflow_definizioni_id_tipo | `CREATE UNIQUE INDEX uq_workflow_definizioni_id_tipo ON pratiche.workflow_definizioni USING btree (id, tipo_prestazione_id)` |
| uq_workflow_definizioni_pubblicata | `CREATE UNIQUE INDEX uq_workflow_definizioni_pubblicata ON pratiche.workflow_definizioni USING btree (tipo_prestazione_id, emittente_fiscale_id) NULLS NOT DISTINCT WHERE ((stato)::text = 'PUBBLICATA'::text)` |
| uq_workflow_definizioni_scope_versione | `CREATE UNIQUE INDEX uq_workflow_definizioni_scope_versione ON pratiche.workflow_definizioni USING btree (tipo_prestazione_id, emittente_fiscale_id, versione) NULLS NOT DISTINCT` |

---
{% include-markdown "signature-core.md" %}
