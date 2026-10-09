{% include-markdown "it/dbzero/vendite/manual/fatture_arrotondamenti_scope.md" %}
# 📚 Tabella `fatture_arrotondamenti_scope`

> 📝 **Descrizione**
>
> Saldo arrotondamenti per scope di fatturazione (BA, utility, tipo doc, emittente, valuta).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| utility_id | integer | NO |  |
| tipo_doc_fiscale_id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| valuta_id | bigint | NO |  |
| saldo_arrotondamento | numeric | NO | 0 |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| termine_pagamento_id | bigint | YES |  |
| modalita_pagamento_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_arrotondamenti_scope_saldo_arrotondamento_finito |  |
| FOREIGN KEY | fk_arrotondamenti_scope_modalita_pagamento | modalita_pagamento_id |
| FOREIGN KEY | fk_arrotondamenti_scope_termine_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_ba | billing_account_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_tipo_doc | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_utility | utility_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_valuta | valuta_id |
| PRIMARY KEY | pk_fatture_arrotondamenti_scope | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatture_arrotondamenti_scope | `CREATE UNIQUE INDEX pk_fatture_arrotondamenti_scope ON vendite.fatture_arrotondamenti_scope USING btree (id)` |
| uq_fatture_arrotondamenti_scope_key | `CREATE UNIQUE INDEX uq_fatture_arrotondamenti_scope_key ON vendite.fatture_arrotondamenti_scope USING btree (billing_account_id, utility_id, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, valuta_id, termine_pagamento_id, modalita_pagamento_id) NULLS NOT DISTINCT` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_arrotondamenti_scope_a10_termini_pagamento_r_53f077 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fatture_arrotondamenti_scope_a10_termini_pagamento_r_53f077 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id', 'id')` |
| trg_fatture_arrotondamenti_scope_a10_tipi_doc_fiscale_re_9c1c2e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatture_arrotondamenti_scope_a10_tipi_doc_fiscale_re_9c1c2e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_fatture_arrotondamenti_scope_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_arrotondamenti_scope_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_fatture_arrotondamenti_scope_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_arrotondamenti_scope_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
