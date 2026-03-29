{% include-markdown "it/dbzero/pratiche/manual/competenze_flussi.md" %}
# 📚 Tabella `competenze_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_id | integer | NO |  |
| unita_organizzativa_id | integer | NO |  |
| risorsa_umana_id | bigint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_competenze_flussi_risorse_umane | risorsa_umana_id |
| FOREIGN KEY | fk_competenze_flussi_template_flussi | template_flusso_id |
| FOREIGN KEY | fk_competenze_flussi_unita_organizzative | unita_organizzativa_id |
| PRIMARY KEY | pk_competenze_flussi | id |
| UNIQUE | uq_competenze_flussi | template_flusso_id, unita_organizzativa_id, risorsa_umana_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_competenze_flussi | `CREATE UNIQUE INDEX pk_competenze_flussi ON pratiche.competenze_flussi USING btree (id)` |
| uq_competenze_flussi | `CREATE UNIQUE INDEX uq_competenze_flussi ON pratiche.competenze_flussi USING btree (template_flusso_id, unita_organizzativa_id, risorsa_umana_id)` |

---
{% include-markdown "signature-core.md" %}
