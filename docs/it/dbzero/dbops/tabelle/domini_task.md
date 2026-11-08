{% include-markdown "it/dbzero/dbops/manual/domini_task.md" %}
# 📚 Tabella `domini_task`

> 📝 **Descrizione**
>
> Catalogo domini task pipeline.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | text | NO |  |
| descrizione | text | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_domini_task | id |
| UNIQUE | uq_domini_task_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_domini_task | `CREATE UNIQUE INDEX pk_domini_task ON dbops.domini_task USING btree (id)` |
| uq_domini_task_codice | `CREATE UNIQUE INDEX uq_domini_task_codice ON dbops.domini_task USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_domini_task_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice', 'E_CODICE_NON_MODIFICABILE')` |

---
{% include-markdown "signature-core.md" %}
