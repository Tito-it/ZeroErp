{% include-markdown "it/dbzero/vendite/manual/preventivi.md" %}
# 📚 Tabella `preventivi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero | character varying | NO |  |
| rev | integer | NO | 0 |
| is_revision_attiva | boolean | NO | false |
| billing_account_id | bigint | YES |  |
| istanza_utility_id | bigint | YES |  |
| utility_id | integer | NO |  |
| validita_dal | date | YES |  |
| validita_al | date | YES |  |
| totale_imponibile | numeric | YES | 0 |
| totale_iva | numeric | YES | 0 |
| totale_documento | numeric | YES | 0 |
| valuta_id | integer | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| competenza_mese | date | YES |  |
| fatturazione_immediata | boolean | YES | false |
| stato_doc_preventivo_id | bigint | NO |  |
| data | date | NO | CURRENT_DATE |
| termine_pagamento_id | bigint | YES |  |
| uid | uuid | NO | uuidv7() |
| storicizza | boolean | YES | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_preventivi_competenza_mese_primo |  |
| CHECK | chk_preventivi_validita |  |
| FOREIGN KEY | fk_preventivi_billing_account | billing_account_id |
| FOREIGN KEY | fk_preventivi_istanza | istanza_utility_id |
| FOREIGN KEY | fk_preventivi_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_preventivi_utility | utility_id |
| FOREIGN KEY | fk_preventivi_valuta | valuta_id |
| FOREIGN KEY | fk_v_preventivi_stato_ddt | stato_doc_preventivo_id |
| PRIMARY KEY | pk_preventivi | id |
| UNIQUE | uq_preventivi_numero_rev | numero, rev |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_preventivi | `CREATE UNIQUE INDEX pk_preventivi ON vendite.preventivi USING btree (id)` |
| uq_preventivi_numero_rev | `CREATE UNIQUE INDEX uq_preventivi_numero_rev ON vendite.preventivi USING btree (numero, rev)` |
| uq_preventivi_uid | `CREATE UNIQUE INDEX uq_preventivi_uid ON vendite.preventivi USING btree (uid)` |
| ux_preventivi_numero_attiva | `CREATE UNIQUE INDEX ux_preventivi_numero_attiva ON vendite.preventivi USING btree (numero) WHERE (is_revision_attiva = true)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_gen_codice()` |
| trg_preventivi_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_gen_codice()` |
| trg_preventivi_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')` |
| trg_preventivi_a10_stati_doc_preventivi_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_doc_preventivo_id')` |
| trg_preventivi_a10_stati_doc_preventivi_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_preventivi', 'attivo', 'stato_doc_preventivo_id')` |
| trg_preventivi_a10_termini_pagamento_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id')` |
| trg_preventivi_a10_termini_pagamento_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id')` |
| trg_preventivi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_preventivi_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_normalize()` |
| trg_preventivi_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_normalize()` |
| trg_preventivi_z90_sync_canali_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |
| trg_preventivi_z90_sync_canali_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |

---
{% include-markdown "signature-core.md" %}
