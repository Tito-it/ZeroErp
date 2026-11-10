{% include-markdown "it/dbzero/dbops/manual/codici_errore_senza_policy.md" %}
# 📚 Tabella `codici_errore_senza_policy`

> 📝 **Descrizione**
>
> Registro del debito del terzo lato: i codici errore che una funzione viva puo' nominare e che non hanno una voce nella mappa generata delle politiche d'errore del backend (backend/apps/core/services/error_policies_generated.py). Effetto del difetto: l'operatore legge comunque la frase giusta (viene dal catalogo), ma il tipo di risposta HTTP resta appiattito su 400 anche quando la verita' e' 404 o 403. Si chiude a lotti per dominio, partendo dai da_trigger. Esiste per tenere acceso il cancello mentre il debito si salda: e' un debito, deve calare, e il cancello pretende che una voce che ha ottenuto la sua politica venga tolta. La misura e' dbops.vw_codici_errore_da_dichiarare.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | text | NO |  |
| da_trigger | boolean | NO |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_codici_errore_senza_policy_conforme |  |
| PRIMARY KEY | pk_codici_errore_senza_policy | id |
| UNIQUE | uq_codici_errore_senza_policy_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_codici_errore_senza_policy | `CREATE UNIQUE INDEX pk_codici_errore_senza_policy ON dbops.codici_errore_senza_policy USING btree (id)` |
| uq_codici_errore_senza_policy_codice | `CREATE UNIQUE INDEX uq_codici_errore_senza_policy_codice ON dbops.codici_errore_senza_policy USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
