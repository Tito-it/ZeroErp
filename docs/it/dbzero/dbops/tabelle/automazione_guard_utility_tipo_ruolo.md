{% include-markdown "it/dbzero/dbops/manual/automazione_guard_utility_tipo_ruolo.md" %}
# 📚 Tabella `automazione_guard_utility_tipo_ruolo`

> 📝 **Descrizione**
>
> Configurazione automazione trigger guard utility-&gt;tipo_ruolo su tabelle con contesto ruolo.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| utility_column | text | NO | 'utility_id'::text |
| soggetto_ruolo_column | text | NO |  |
| enabled | boolean | NO | true |
| exec_mode | text | NO | 'AUTO'::text |
| trigger_name | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automazione_guard_utility_tipo_ruolo_exec_mode |  |
| PRIMARY KEY | pk_automazione_guard_utility_tipo_ruolo | id |
| UNIQUE | uq_automazione_guard_utility_tipo_ruolo_table | schema_name, table_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_guard_utility_tipo_ruolo | `CREATE UNIQUE INDEX pk_automazione_guard_utility_tipo_ruolo ON dbops.automazione_guard_utility_tipo_ruolo USING btree (id)` |
| uq_automazione_guard_utility_tipo_ruolo_table | `CREATE UNIQUE INDEX uq_automazione_guard_utility_tipo_ruolo_table ON dbops.automazione_guard_utility_tipo_ruolo USING btree (schema_name, table_name)` |

---
{% include-markdown "signature-core.md" %}
