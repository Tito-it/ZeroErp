{% include-markdown "it/dbzero/dbops/manual/automazione_attivo_eccezioni.md" %}
# 📚 Tabella `automazione_attivo_eccezioni`

> 📝 **Descrizione**
>
> Le FK che l'automazione ATTIVO NON lega: per una riga qui, dbops.fn_run_automations_attivo non genera ne' il block sul padre ne' il require sul figlio, e dbops.fn_ritira_attivo_eccezioni toglie quelli gia' generati. Una FK per riga (schema e tabella del FIGLIO, colonna FK), col MOTIVO obbligatorio: un'eccezione senza perche' e' un buco nel framework. Prima riga il 2026-09-25: config.profili_accesso_bindings.identita_digitale_id — porta e profili si sganciano (brief-db-blocco-login-per-credenziale §12.3). Seed da 80_data (CSV dbops/automazione_attivo_eccezioni.csv).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_figlia | text | NO |  |
| tabella_figlia | text | NO |  |
| colonna_fk | text | NO |  |
| motivo | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automazione_attivo_eccezioni_motivo |  |
| PRIMARY KEY | pk_automazione_attivo_eccezioni | id |
| UNIQUE | uq_automazione_attivo_eccezioni_fk | schema_figlia, tabella_figlia, colonna_fk |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_attivo_eccezioni | `CREATE UNIQUE INDEX pk_automazione_attivo_eccezioni ON dbops.automazione_attivo_eccezioni USING btree (id)` |
| uq_automazione_attivo_eccezioni_fk | `CREATE UNIQUE INDEX uq_automazione_attivo_eccezioni_fk ON dbops.automazione_attivo_eccezioni USING btree (schema_figlia, tabella_figlia, colonna_fk)` |

---
{% include-markdown "signature-core.md" %}
