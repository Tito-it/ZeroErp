{% include-markdown "it/dbzero/dbops/manual/stati_check_dichiarazioni.md" %}
# 📚 Tabella `stati_check_dichiarazioni`

> 📝 **Descrizione**
>
> Registro del presidio C1 (uno stato previsto dal modello e mai scritto): i valori ammessi dal CHECK di una colonna di stato che il criterio di dbops.vw_stati_check_scrittori non trova scritti da nessuna funzione ne' dal default, e che restano cosi' per una DICHIARAZIONE. Il canale dice CHI verifica la riga: APPLICAZIONE = lo scrive un repository Python, lo verifica il test del backend; ESENTE = esente dal criterio per la ragione scritta, lo verifica il pgTAP nel verso DEBITO_ESTINTO. ⚠️ ESENTE non vuol dire «non scritto»: vuol dire che il criterio testuale non lo vede (es. una copia colonna→colonna). E' un registro e DEVE calare: una riga rientrata va tolta. Brief: brief-db-presidio-stati-mai-scritti §2.4 e §3-bis.4.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| colonna | text | NO |  |
| valore | text | NO |  |
| canale | text | NO |  |
| ragione | text | NO |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_stati_check_dichiarazioni_canale |  |
| CHECK | chk_stati_check_dichiarazioni_identificatori |  |
| CHECK | chk_stati_check_dichiarazioni_ragione |  |
| PRIMARY KEY | pk_stati_check_dichiarazioni | id |
| UNIQUE | uq_stati_check_dichiarazioni_valore | schema_tabella, nome_tabella, colonna, valore |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_check_dichiarazioni | `CREATE UNIQUE INDEX pk_stati_check_dichiarazioni ON dbops.stati_check_dichiarazioni USING btree (id)` |
| uq_stati_check_dichiarazioni_valore | `CREATE UNIQUE INDEX uq_stati_check_dichiarazioni_valore ON dbops.stati_check_dichiarazioni USING btree (schema_tabella, nome_tabella, colonna, valore)` |

---
{% include-markdown "signature-core.md" %}
