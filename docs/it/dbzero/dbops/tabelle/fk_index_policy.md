# Tabella `fk_index_policy`

## Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_name | text | NO |  |
| constraint_name | text | NO |  |
| consentito | boolean | NO | true |
| note | text | YES |  |

## Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | fk_index_policy_pkey | schema_name, table_name, constraint_name |

## Indici
| Nome | Definizione |
|------|-------------|
| fk_index_policy_pkey | `CREATE UNIQUE INDEX fk_index_policy_pkey ON dbops.fk_index_policy USING btree (schema_name, table_name, constraint_name)` |