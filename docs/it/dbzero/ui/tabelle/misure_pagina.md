{% include-markdown "it/dbzero/ui/manual/misure_pagina.md" %}
# 📚 Tabella `misure_pagina`

> 📝 **Descrizione**
>
> Il catalogo delle misure «righe per pagina» ammesse e dei loro default, uno per uso (ui.uso_misura_pagina). Le citano ui.lista_preset.pagina_dimensione (FK e guard) e le preferenze di lista (guard di forma); il resolver delle liste non risponde mai una misura che non sta qui. L'applicazione lo legge con ui.fn_get_misure_pagina e non lo scrive: le righe le porta il CSV del seed.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| misura | integer | NO |  |
| uso_default | ui.uso_misura_pagina | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_misure_pagina_misura |  |
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
| trg_misure_pagina_a10_guard_default_per_uso_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION ui.trgfn_misure_pagina_guard_default_per_uso()` |
| trg_misure_pagina_a10_guard_default_per_uso_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION ui.trgfn_misure_pagina_guard_default_per_uso()` |
| trg_misure_pagina_a10_guard_default_per_uso_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION ui.trgfn_misure_pagina_guard_default_per_uso()` |
| trg_misure_pagina_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('misura', 'E_UI_MISURA_PAGINA_IMMUTABILE')` |
| trg_misure_pagina_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_misure_pagina_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_misure_pagina_z10_ritira_dalle_preferenze_dlt | AFTER | DELETE | `EXECUTE FUNCTION ui.trgfn_misure_pagina_ritira_dalle_preferenze()` |

---
{% include-markdown "signature-core.md" %}
