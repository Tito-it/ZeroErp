{% include-markdown "it/dbzero/config/manual/stati_doc_fiscale_transizioni.md" %}
# 📚 Tabella `stati_doc_fiscale_transizioni`

> 📝 **Descrizione**
>
> Transizioni ammesse tra stati documento (lotto/fattura).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_from_id | bigint | NO |  |
| stato_to_id | bigint | NO |  |
| ammesso | boolean | NO | true |
| solo_lotto | boolean | NO | false |
| solo_fattura | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| azione_processo_codename | character varying(100) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_stati_doc_fiscale_transizioni_meta_manuale_dichiarato |  |
| CHECK | ck_stati_doc_fiscale_transizioni_tipo_lotto_solo_processo |  |
| FOREIGN KEY | fk_stati_doc_fiscale_transizioni_azioni_processo | azione_processo_codename |
| FOREIGN KEY | fk_stati_doc_fiscale_transizioni_from | stato_from_id |
| FOREIGN KEY | fk_stati_doc_fiscale_transizioni_to | stato_to_id |
| PRIMARY KEY | pk_stati_doc_fiscale_transizioni | id |
| UNIQUE | uq_stati_doc_fiscale_transizioni | stato_from_id, stato_to_id, solo_lotto, solo_fattura |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_doc_fiscale_transizioni | `CREATE UNIQUE INDEX pk_stati_doc_fiscale_transizioni ON config.stati_doc_fiscale_transizioni USING btree (id)` |
| uq_stati_doc_fiscale_transizioni | `CREATE UNIQUE INDEX uq_stati_doc_fiscale_transizioni ON config.stati_doc_fiscale_transizioni USING btree (stato_from_id, stato_to_id, solo_lotto, solo_fattura)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_doc_fiscale_transizioni_a10_stati_doc_fiscale_8ec9d2 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_from_id', 'id')` |
| trg_stati_doc_fiscale_transizioni_a10_stati_doc_fiscale_8ec9d2 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_from_id', 'id')` |
| trg_stati_doc_fiscale_transizioni_a10_stati_doc_fiscale_ec940d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_to_id', 'id')` |
| trg_stati_doc_fiscale_transizioni_a10_stati_doc_fiscale_ec940d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_fiscale', 'attivo', 'stato_to_id', 'id')` |
| trg_stati_doc_fiscale_transizioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_doc_fiscale_transizioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
