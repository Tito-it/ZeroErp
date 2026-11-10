{% include-markdown "it/dbzero/dbops/manual/rls_perimetro_debito.md" %}
# 📚 Tabella `rls_perimetro_debito`

> 📝 **Descrizione**
>
> Registro del debito del perimetro RLS: le tabelle che il criterio di dbops.vw_rls_perimetro_scoperto trova scoperte e che restano tali per una decisione. Una riga zittisce il presidio su quella tabella e su quel criterio soltanto. Dichiarare un debito non lo assolve: dice perche' e' qui, non che va bene che ci sia. E' un registro e deve calare: il presidio pretende che una riga rientrata venga tolta (stato DEBITO_ESTINTO).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| criterio | text | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| ragione | text | NO |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_rls_perimetro_debito_criterio |  |
| CHECK | chk_rls_perimetro_debito_ragione |  |
| PRIMARY KEY | pk_rls_perimetro_debito | id |
| UNIQUE | uq_rls_perimetro_debito_target | criterio, schema_tabella, nome_tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_rls_perimetro_debito | `CREATE UNIQUE INDEX pk_rls_perimetro_debito ON dbops.rls_perimetro_debito USING btree (id)` |
| uq_rls_perimetro_debito_target | `CREATE UNIQUE INDEX uq_rls_perimetro_debito_target ON dbops.rls_perimetro_debito USING btree (criterio, schema_tabella, nome_tabella)` |

---
{% include-markdown "signature-core.md" %}
