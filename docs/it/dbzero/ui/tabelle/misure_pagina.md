{% include-markdown "it/dbzero/ui/manual/misure_pagina.md" %}
# 📚 Tabella `misure_pagina`

> 📝 **Descrizione**
>
> Catalogo delle misure «righe per pagina» ammesse, e dei loro due default: la sede UNICA per DB, backend e frontend (decisioni di Tid del 2026-09-29). Le citano ui.lista_preset.pagina_dimensione (FK) e le preferenze utente (guard); il resolver delle liste non risponde mai una misura che non sta qui. L'applicazione la legge con ui.fn_get_misure_pagina(). Posseduta dal CSV (80_data/sql/ui/misure_pagina.csv): all'app solo SELECT. Brief: brief-db-misure-pagina-catalogo.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| misura | integer | NO |  |
| uso_default | character varying(20) | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_misure_pagina_misura |  |
| CHECK | chk_misure_pagina_uso_default |  |
| PRIMARY KEY | pk_misure_pagina | id |
| UNIQUE | uq_misure_pagina_misura | misura |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_misure_pagina | `CREATE UNIQUE INDEX pk_misure_pagina ON ui.misure_pagina USING btree (id)` |
| uq_misure_pagina_misura | `CREATE UNIQUE INDEX uq_misure_pagina_misura ON ui.misure_pagina USING btree (misura)` |
| uq_misure_pagina_uso_default | `CREATE UNIQUE INDEX uq_misure_pagina_uso_default ON ui.misure_pagina USING btree (uso_default) WHERE (uso_default IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_misure_pagina_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_misure_pagina_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
