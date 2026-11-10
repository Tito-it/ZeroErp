{% include-markdown "it/dbzero/dbops/manual/automation_scope.md" %}
# 📚 Tabella `automation_scope`

> 📝 **Descrizione**
>
> L'ambito delle automazioni: quali schemi e quali tabelle i runner (ATTIVO, LOCK_COLUMNS, DATE_VALIDITA, audit, storicizzazione, CLEANUP_AT, DELETE_BLOCK, overlap, CODICE_MAIUSCOLO) e la politica degli indici delle FK governano. Una riga = uno schema e un filtro di tabella (table_like: *all o un pattern LIKE). Gli schemi li risolve dbops.fn_resolve_scope, il filtro per tabella dbops.fn_table_in_scope, la politica degli indici dbops.fn_indici_schema_nell_ambito (per schema). Un registro vuoto vuol dire tutti gli schemi utente tranne storico; uno schema senza righe e' fuori. Nessun runner legge la tabella da se'.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_like | text | NO | '*all'::text |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automation_scope | schema_name, table_like |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_scope | `CREATE UNIQUE INDEX pk_automation_scope ON dbops.automation_scope USING btree (schema_name, table_like)` |

---
{% include-markdown "signature-core.md" %}
