{% include-markdown "it/dbzero/dbops/manual/marcatori_automazione_debito.md" %}
# 📚 Tabella `marcatori_automazione_debito`

> 📝 **Descrizione**
>
> Registro del debito di dbops.vw_marcatori_automazione_senza_esecutore: le tabelle con un marcatore di automazione (tx_id, storicizza, cleanup_at) che nessuno esegue, lasciate tali per una decisione. Una riga zittisce il presidio su quella tabella e quel marcatore soltanto. Dichiarare un debito non lo assolve: il registro deve calare, e una riga che non trova piu' il suo caso esce dal presidio come DEBITO_ESTINTO. Seminato dal CSV di 80_data (mirror: una riga tolta si cancella anche con un changeSet).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| marcatore | text | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| ragione | text | NO |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_marcatori_automazione_debito_marcatore |  |
| CHECK | chk_marcatori_automazione_debito_ragione |  |
| PRIMARY KEY | pk_marcatori_automazione_debito | id |
| UNIQUE | uq_marcatori_automazione_debito_target | marcatore, schema_tabella, nome_tabella |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_marcatori_automazione_debito | `CREATE UNIQUE INDEX pk_marcatori_automazione_debito ON dbops.marcatori_automazione_debito USING btree (id)` |
| uq_marcatori_automazione_debito_target | `CREATE UNIQUE INDEX uq_marcatori_automazione_debito_target ON dbops.marcatori_automazione_debito USING btree (marcatore, schema_tabella, nome_tabella)` |

---
{% include-markdown "signature-core.md" %}
