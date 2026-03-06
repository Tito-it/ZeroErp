{% include-markdown "it/dbzero/pratiche/manual/regole_generazione.md" %}
# 📚 Tabella `regole_generazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| template_flusso_origine_id | integer | NO |  |
| tipo_prestazione_dest_id | integer | NO |  |
| template_flusso_dest_id | integer | YES |  |
| esito_richiesto | character varying | YES |  |
| auto | boolean | NO | false |
| attivo | boolean | NO | true |
| descrizione | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_regole_gen_esito |  |
| FOREIGN KEY | fk_regole_gen_template_dest | template_flusso_dest_id |
| FOREIGN KEY | fk_regole_gen_template_origine | template_flusso_origine_id |
| FOREIGN KEY | fk_regole_gen_tipo_dest | tipo_prestazione_dest_id |
| PRIMARY KEY | pk_pratiche_regole_generazione | id |
| UNIQUE | uq_pratiche_regole_gen_origine_dest_esito | template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_regole_generazione | `CREATE UNIQUE INDEX pk_pratiche_regole_generazione ON pratiche.regole_generazione USING btree (id)` |
| uq_pratiche_regole_gen_origine_dest_esito | `CREATE UNIQUE INDEX uq_pratiche_regole_gen_origine_dest_esito ON pratiche.regole_generazione USING btree (template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto)` |
| uq_pratiche_regole_gen_origine_dest_null_esito | `CREATE UNIQUE INDEX uq_pratiche_regole_gen_origine_dest_null_esito ON pratiche.regole_generazione USING btree (template_flusso_origine_id, tipo_prestazione_dest_id) WHERE (esito_richiesto IS NULL)` |

---
{% include-markdown "signature-core.md" %}
