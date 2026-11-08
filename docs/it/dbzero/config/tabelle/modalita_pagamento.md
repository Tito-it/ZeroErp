{% include-markdown "it/dbzero/config/manual/modalita_pagamento.md" %}
# 📚 Tabella `modalita_pagamento`

> 📝 **Descrizione**
>
> Catalogo delle modalità di pagamento (es. RID, BONIFICO, CONTANTI)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | character varying(80) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_modalita_pagamento | id |
| UNIQUE | uq_modalita_pagamento_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_modalita_pagamento | `CREATE UNIQUE INDEX pk_modalita_pagamento ON config.modalita_pagamento USING btree (id)` |
| uq_modalita_pagamento_codice | `CREATE UNIQUE INDEX uq_modalita_pagamento_codice ON config.modalita_pagamento USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_modalita_pagamento_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_modalita_pagamento_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_modalita_pagamento_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_modalita_pagamento_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
