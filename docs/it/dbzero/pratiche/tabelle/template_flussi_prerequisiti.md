{% include-markdown "it/dbzero/pratiche/manual/template_flussi_prerequisiti.md" %}
# 📚 Tabella `template_flussi_prerequisiti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| prerequisito_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| esito_richiesto | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_template_flussi_prereq_esito |  |
| CHECK | chk_template_flussi_prereq_no_self |  |
| FOREIGN KEY | fk_template_flussi_prereq_flusso | template_flusso_id |
| FOREIGN KEY | fk_template_flussi_prereq_prerequisito | prerequisito_id |
| PRIMARY KEY | pk_pratiche_template_flussi_prerequisiti | id |
| UNIQUE | uq_pratiche_template_flussi_prereq_flusso_prereq | template_flusso_id, prerequisito_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_template_flussi_prerequisiti | `CREATE UNIQUE INDEX pk_pratiche_template_flussi_prerequisiti ON pratiche.template_flussi_prerequisiti USING btree (id)` |
| uq_pratiche_template_flussi_prereq_flusso_prereq | `CREATE UNIQUE INDEX uq_pratiche_template_flussi_prereq_flusso_prereq ON pratiche.template_flussi_prerequisiti USING btree (template_flusso_id, prerequisito_id)` |

---
{% include-markdown "signature-core.md" %}
