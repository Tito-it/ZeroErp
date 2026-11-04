# 📚 Tabella `orientamenti_pagina`

> 📝 **Descrizione**
>
> Orientamenti di pagina del PDF (PORTRAIT, LANDSCAPE): i valori ammessi di documenti.template_documenti_versioni.page_orientation, legata per FK a codice_interno. Si legge, non si configura: niente attivo. Brief: brief-db-vocabolari-versione-template.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(40) | NO |  |
| codice | character varying(40) | NO |  |
| descrizione | character varying(255) | YES |  |
| etichetta_key | character varying(120) | NO |  |
| ordine | smallint | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_orientamenti_pagina_codice_interno_non_vuoto |  |
| PRIMARY KEY | pk_orientamenti_pagina | id |
| UNIQUE | uq_orientamenti_pagina_codice | codice |
| UNIQUE | uq_orientamenti_pagina_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_orientamenti_pagina | `CREATE UNIQUE INDEX pk_orientamenti_pagina ON documenti.orientamenti_pagina USING btree (id)` |
| uq_orientamenti_pagina_codice | `CREATE UNIQUE INDEX uq_orientamenti_pagina_codice ON documenti.orientamenti_pagina USING btree (codice)` |
| uq_orientamenti_pagina_codice_interno | `CREATE UNIQUE INDEX uq_orientamenti_pagina_codice_interno ON documenti.orientamenti_pagina USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_orientamenti_pagina_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_orientamenti_pagina_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_orientamenti_pagina_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_orientamenti_pagina_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_orientamenti_pagina_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_orientamenti_pagina_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_orientamenti_pagina_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
