# 📚 Tabella `modalita_pagamento`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character | NO |  |
| descrizione | character varying | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | 'CURRENT_USER'::character varying |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | 'CURRENT_USER'::character varying |

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
| trg_upd_modalita_pagamento_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
