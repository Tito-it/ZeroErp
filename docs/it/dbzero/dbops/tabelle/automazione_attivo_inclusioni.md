{% include-markdown "it/dbzero/dbops/manual/automazione_attivo_inclusioni.md" %}
# 📚 Tabella `automazione_attivo_inclusioni`

> 📝 **Descrizione**
>
> Le FK senza il suffisso _id che l'automazione ATTIVO lega comunque. dbops.fn_run_automations_attivo salta ogni FK la cui colonna non finisce in _id; per una riga qui genera invece la coppia intera, il block sul padre (dbops.trgfn_prevent_deactivate_if_children) e il require sulla figlia (dbops.trgfn_child_requires_active_parent), con la colonna del padre referenziata dalla FK anche quando e' una UNIQUE non primaria. Una FK per riga (schema e tabella della FIGLIA, colonna FK; uq_automazione_attivo_inclusioni_fk), col motivo obbligatorio e non vuoto (chk_automazione_attivo_inclusioni_motivo). Una colonna che finisce in _id qui non entra (chk_automazione_attivo_inclusioni_senza_id): la lega gia' l'automazione. Un'eccezione di dbops.automazione_attivo_eccezioni prevale: la domanda «questa FK si lega?» la risponde dbops.fn_attivo_fk_esclusa. Togliere una riga ritira i trigger al giro successivo (dbops.fn_ritira_attivo_eccezioni). Seed da 80_data (CSV dbops/automazione_attivo_inclusioni.csv).

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
| CHECK | chk_automazione_attivo_inclusioni_motivo |  |
| CHECK | chk_automazione_attivo_inclusioni_senza_id |  |
| PRIMARY KEY | pk_automazione_attivo_inclusioni | id |
| UNIQUE | uq_automazione_attivo_inclusioni_fk | schema_figlia, tabella_figlia, colonna_fk |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_attivo_inclusioni | `CREATE UNIQUE INDEX pk_automazione_attivo_inclusioni ON dbops.automazione_attivo_inclusioni USING btree (id)` |
| uq_automazione_attivo_inclusioni_fk | `CREATE UNIQUE INDEX uq_automazione_attivo_inclusioni_fk ON dbops.automazione_attivo_inclusioni USING btree (schema_figlia, tabella_figlia, colonna_fk)` |

---
{% include-markdown "signature-core.md" %}
