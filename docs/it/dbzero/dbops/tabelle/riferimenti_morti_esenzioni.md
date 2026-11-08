{% include-markdown "it/dbzero/dbops/manual/riferimenti_morti_esenzioni.md" %}
# 📚 Tabella `riferimenti_morti_esenzioni`

> 📝 **Descrizione**
>
> Registro del debito sui riferimenti morti nelle funzioni plpgsql: voci REALE/ORFANA note e motivate. E' un debito, non un elenco di eccezioni: deve calare. Letto da db/pgtap/dbops/test-riferimenti-morti-v1.sql e da scripts/sql/guardrail_riferimenti_morti.sql.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_nome | text | NO |  |
| funzione | text | NO |  |
| esito_like | text | NO |  |
| motivo | text | NO |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_riferimenti_morti_esenzioni_motivo |  |
| CHECK | chk_riferimenti_morti_esenzioni_pattern |  |
| PRIMARY KEY | pk_riferimenti_morti_esenzioni | id |
| UNIQUE | uq_riferimenti_morti_esenzioni_voce | schema_nome, funzione, esito_like |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_riferimenti_morti_esenzioni | `CREATE UNIQUE INDEX pk_riferimenti_morti_esenzioni ON dbops.riferimenti_morti_esenzioni USING btree (id)` |
| uq_riferimenti_morti_esenzioni_voce | `CREATE UNIQUE INDEX uq_riferimenti_morti_esenzioni_voce ON dbops.riferimenti_morti_esenzioni USING btree (schema_nome, funzione, esito_like)` |

---
{% include-markdown "signature-core.md" %}
