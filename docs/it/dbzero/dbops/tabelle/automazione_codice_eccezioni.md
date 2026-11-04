{% include-markdown "it/dbzero/dbops/manual/automazione_codice_eccezioni.md" %}
# 📚 Tabella `automazione_codice_eccezioni`

> 📝 **Descrizione**
>
> Le colonne codice che l'automazione CODICE_MAIUSCOLO NON normalizza. La regola e' per esclusione (decisione Tid 2026-11-04): ogni colonna codice di una tabella dell'ambito si salva in upper(btrim(...)) (script.trgfn_codice_maiuscolo), e una tabella nuova nasce presidiata. Qui stanno le colonne codice che non sono un codice dell'operatore: una chiave tecnica letta dal codice per nome, o un codice esterno dove il maiuscolo conta. Il MOTIVO e' obbligatorio. Una riga toglie il trigger al giro successivo (dbops.fn_run_automations_codice_maiuscolo, azione TOGLIE). codice_interno non e' nel perimetro: lo scrive la migrazione. Seed da 80_data (CSV dbops/automazione_codice_eccezioni.csv).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| column_name | text | NO | 'codice'::text |
| motivo | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automazione_codice_eccezioni_colonna |  |
| CHECK | chk_automazione_codice_eccezioni_motivo |  |
| PRIMARY KEY | pk_automazione_codice_eccezioni | id |
| UNIQUE | uq_automazione_codice_eccezioni_colonna | schema_name, table_name, column_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_codice_eccezioni | `CREATE UNIQUE INDEX pk_automazione_codice_eccezioni ON dbops.automazione_codice_eccezioni USING btree (id)` |
| uq_automazione_codice_eccezioni_colonna | `CREATE UNIQUE INDEX uq_automazione_codice_eccezioni_colonna ON dbops.automazione_codice_eccezioni USING btree (schema_name, table_name, column_name)` |

---
{% include-markdown "signature-core.md" %}
