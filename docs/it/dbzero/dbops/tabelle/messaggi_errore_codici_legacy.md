{% include-markdown "it/dbzero/dbops/manual/messaggi_errore_codici_legacy.md" %}
# 📚 Tabella `messaggi_errore_codici_legacy`

> 📝 **Descrizione**
>
> Registro del DEBITO EREDITATO sulla convenzione dei codici errore (E_{MODULO}_{TIPO}, W_ per i warning — docs/it/dev/api.md). Ci va un codice che arriva da fuori gia' fuori convenzione e che non conviene rinominare; il CHECK chk_..._non_conforme impedisce di registrarci un codice conforme. ⭐ A ZERO RIGHE dal 2026-08-07: le 57 voci del 2026-08-05 sono state tutte smaltite, l'ultima col rename MESSAGGIO_NON_DEFINITO -&gt; E_MESSAGGIO_NON_DEFINITO. ⛔ NON DROPPARE (decisione Tid 2026-08-08): a zero righe il drop sarebbe neutro nel comportamento, ma costerebbe mettere mano al controllo (B) di scripts/sql/guardrail_codice_errore_strutturato.sql — l'unica cosa che tiene la convenzione — in un presidio verde, e toglierebbe il meccanismo pronto per la prossima eredita' di codici. Un registro vuoto non e' un registro inutile: e' un registro in pari. ⚠️ NON e' una whitelist di eccezioni: una FAMIGLIA nuova con una semantica sua (com'e' stato per i W_, changeSet 20260805-28) si risolve ALLARGANDO la convenzione, non registrandola qui — per questo non c'e' una colonna «motivo», e l'orologio del debito e' data_registrazione. ⚠️ Da non confondere con dbops.codici_errore_senza_policy, che e' il registro del terzo lato (codici senza policy BE). Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md §5.5.

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
