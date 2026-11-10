{% include-markdown "it/dbzero/dbops/manual/messaggi_errore_codici_legacy.md" %}
# 📚 Tabella `messaggi_errore_codici_legacy`

> 📝 **Descrizione**
>
> Registro del debito ereditato sulla convenzione dei codici errore (E_{MODULO}_{TIPO}, W_ per i warning: docs/it/dev/api.md). Ci va un codice che arriva da fuori gia' fuori convenzione e che non conviene rinominare; il CHECK chk_messaggi_errore_codici_legacy_non_conforme impedisce di registrarci un codice conforme. Un registro vuoto e' un registro in pari, non inutile: il controllo (B) di scripts/sql/guardrail_codice_errore_strutturato.sql lo legge, ed e' pronto per la prossima eredita' di codici. Non e' un elenco di eccezioni: una famiglia nuova con una semantica sua si risolve allargando la convenzione, non registrandola qui; per questo non c'e' una colonna motivo, e l'orologio del debito e' data_registrazione. Da non confondere con dbops.codici_errore_senza_policy, il registro del terzo lato.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | text | NO |  |
| data_registrazione | date | NO | script.fn_data_operativa() |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_messaggi_errore_codici_legacy_non_conforme |  |
| PRIMARY KEY | pk_messaggi_errore_codici_legacy | id |
| UNIQUE | uq_messaggi_errore_codici_legacy_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_messaggi_errore_codici_legacy | `CREATE UNIQUE INDEX pk_messaggi_errore_codici_legacy ON dbops.messaggi_errore_codici_legacy USING btree (id)` |
| uq_messaggi_errore_codici_legacy_codice | `CREATE UNIQUE INDEX uq_messaggi_errore_codici_legacy_codice ON dbops.messaggi_errore_codici_legacy USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
