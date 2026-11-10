{% include-markdown "it/dbzero/dbops/manual/fk_index_policy.md" %}
# 📚 Tabella `fk_index_policy`

> 📝 **Descrizione**
>
> Politica degli indici sulle foreign key: una riga per FK, con la decisione su un indice dedicato. La scoperta (dbops.fn_populate_fk_index_policy) registra le FK scoperte senza riga come DA_DECIDERE e toglie le DA_DECIDERE la cui FK non e' piu' scoperta; le decisioni CON_INDICE e SENZA_INDICE le scrive solo il seed, il CSV di 80_data. dbops.apply_fk_index_policy crea o toglie gli indici delle sole righe decise, negli schemi governati (dbops.fn_indici_schema_nell_ambito). Le FK da decidere le mostra il presidio dbops.vw_fk_da_decidere. Una FK gia' coperta da un indice del suo changeSet non ha bisogno di una riga: la politica governa gli indici che crea lei.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| schema_name | text | NO |  |
| table_name | text | NO |  |
| constraint_name | text | NO |  |
| dll_command | text | NO |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| decisione | text | NO | 'DA_DECIDERE'::text |
| motivo | text | YES |  |
| indice_nome | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fk_index_policy_decisione |  |
| CHECK | chk_fk_index_policy_dll_command_forma |  |
| CHECK | chk_fk_index_policy_motivo_non_vuoto |  |
| PRIMARY KEY | fk_index_policy_pkey | schema_name, table_name, constraint_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| fk_index_policy_pkey | `CREATE UNIQUE INDEX fk_index_policy_pkey ON dbops.fk_index_policy USING btree (schema_name, table_name, constraint_name)` |

---
{% include-markdown "signature-core.md" %}
