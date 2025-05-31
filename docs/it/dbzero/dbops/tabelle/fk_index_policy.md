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
| CHECK | 18506_18522_1_not_null |  |
| CHECK | 18506_18522_2_not_null |  |
| CHECK | 18506_18522_3_not_null |  |
| CHECK | 18506_18522_4_not_null |  |
| PRIMARY KEY | fk_index_policy_pkey | table_name, constraint_name, schema_name |

## Indici
| Nome | Definizione |
|------|-------------|
| fk_index_policy_pkey | `CREATE UNIQUE INDEX fk_index_policy_pkey ON dbops.fk_index_policy USING btree (schema_name, table_name, constraint_name)` |