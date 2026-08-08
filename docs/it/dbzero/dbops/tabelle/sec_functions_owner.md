{% include-markdown "it/dbzero/dbops/manual/sec_functions_owner.md" %}
# 📚 Tabella `sec_functions_owner`

> 📝 **Descrizione**
>
> Mappa funzioni sensibili e owner richiesto per hardening permessi.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| schema_name | text | NO |  |
| function_name | text | NO |  |
| arg_types | text | NO |  |
| required_owner | text | NO |  |
| note | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_sec_func_owner | id |
| UNIQUE | uq_sec_functions_owner_signature | schema_name, function_name, arg_types |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_sec_func_owner | `CREATE UNIQUE INDEX pk_sec_func_owner ON dbops.sec_functions_owner USING btree (id)` |
| uq_sec_functions_owner_signature | `CREATE UNIQUE INDEX uq_sec_functions_owner_signature ON dbops.sec_functions_owner USING btree (schema_name, function_name, arg_types)` |

---
{% include-markdown "signature-core.md" %}
