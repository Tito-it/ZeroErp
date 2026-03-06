{% include-markdown "it/dbzero/pratiche/manual/formule_tempo.md" %}
# 📚 Tabella `formule_tempo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| tipo_prestazione_id | integer | NO |  |
| template_flusso_da_id | integer | NO |  |
| template_flusso_a_id | integer | NO |  |
| giorni_esecuzione | integer | NO |  |
| giorni_warning | integer | NO |  |
| giorni_critico | integer | NO |  |
| attivo | boolean | NO | true |
| descrizione | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_formule_tempo_da_diverso_a |  |
| CHECK | chk_formule_tempo_giorni_critico |  |
| CHECK | chk_formule_tempo_giorni_esecuzione |  |
| CHECK | chk_formule_tempo_giorni_warning |  |
| CHECK | chk_formule_tempo_warning_gt_critico |  |
| CHECK | chk_formule_tempo_warning_lt_esecuzione |  |
| FOREIGN KEY | fk_formule_tempo_template_a | template_flusso_a_id |
| FOREIGN KEY | fk_formule_tempo_template_da | template_flusso_da_id |
| FOREIGN KEY | fk_formule_tempo_tipo_prestazione | tipo_prestazione_id |
| PRIMARY KEY | pk_pratiche_formule_tempo | id |
| UNIQUE | uq_formule_tempo_tipo_da_a | tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_formule_tempo | `CREATE UNIQUE INDEX pk_pratiche_formule_tempo ON pratiche.formule_tempo USING btree (id)` |
| uq_formule_tempo_tipo_da_a | `CREATE UNIQUE INDEX uq_formule_tempo_tipo_da_a ON pratiche.formule_tempo USING btree (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id)` |

---
{% include-markdown "signature-core.md" %}
