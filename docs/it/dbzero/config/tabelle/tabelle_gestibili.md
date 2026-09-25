{% include-markdown "it/dbzero/config/manual/tabelle_gestibili.md" %}
# 📚 Tabella `tabelle_gestibili`

> 📝 **Descrizione**
>
> La lista delle tabelle GESTIBILI in modo generico: quelle che il lookup generico serve alle tendine (lookup) e quelle che il pannello di configurazione scrive col verbo config.fn_pannello_scrivi (pannello). Fino al 2026-09-25 era la costante REL_CONSENTITE del backend. Ogni riga nomina l'OGGETTO a cui la tabella appartiene (app_label, model_name, convenzione (schema, nome tabella) come in area_model_overrides): il verbo chiede il livello su quell'oggetto, e l'area la ricava script.fn_area_di_oggetto — qui non c'e' una colonna area. ⛔ All'app solo SELECT: la lista e' una porta, perche' il verbo scrive come proprietario su ogni tabella che vi compare. Una riga nasce nel CSV del seed, non dall'applicazione. Brief: brief-db-pannello-config-verbo-generico, sezione 3.1.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | text | NO |  |
| schema_tabella | text | NO |  |
| nome_tabella | text | NO |  |
| app_label | text | NO |  |
| model_name | text | NO |  |
| lookup | boolean | NO | false |
| pannello | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tabelle_gestibili_codice_interno_qualificato |  |
| CHECK | chk_tabelle_gestibili_nomi_forma |  |
| CHECK | chk_tabelle_gestibili_oggetto_forma |  |
| PRIMARY KEY | pk_tabelle_gestibili | id |
| UNIQUE | uq_tabelle_gestibili_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tabelle_gestibili | `CREATE UNIQUE INDEX pk_tabelle_gestibili ON config.tabelle_gestibili USING btree (id)` |
| uq_tabelle_gestibili_codice_interno | `CREATE UNIQUE INDEX uq_tabelle_gestibili_codice_interno ON config.tabelle_gestibili USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
