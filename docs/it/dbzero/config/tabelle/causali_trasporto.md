{% include-markdown "it/dbzero/config/manual/causali_trasporto.md" %}
# 📚 Tabella `causali_trasporto`

> 📝 **Descrizione**
>
> Elenco causali di trasporto (DDT).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(16) | NO |  |
| descrizione | character varying(120) | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| fatturabile | boolean | NO | false |
| causale_magazzino | character varying(50) | YES |  |
| richiede_cliente | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_causali_trasporto_causale_magazzino | causale_magazzino |
| PRIMARY KEY | pk_causali_trasporto | id |
| UNIQUE | causali_trasporto_codice_key | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| causali_trasporto_codice_key | `CREATE UNIQUE INDEX causali_trasporto_codice_key ON config.causali_trasporto USING btree (codice)` |
| ix_causali_trasporto_attivo | `CREATE INDEX ix_causali_trasporto_attivo ON config.causali_trasporto USING btree (attivo)` |
| pk_causali_trasporto | `CREATE UNIQUE INDEX pk_causali_trasporto ON config.causali_trasporto USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_causali_trasporto_a10_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt', 'causale_trasporto_id', 'id', 'attivo')` |
| trg_causali_trasporto_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini', 'causale_trasporto_id', 'id', 'attivo')` |
| trg_causali_trasporto_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_causali_trasporto_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_causali_trasporto_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_causali_trasporto_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
