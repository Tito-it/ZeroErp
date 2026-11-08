{% include-markdown "it/dbzero/config/manual/aspetti_beni.md" %}
# 📚 Tabella `aspetti_beni`

> 📝 **Descrizione**
>
> Elenco aspetti beni (DDT).

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

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_aspetti_beni | id |
| UNIQUE | aspetti_beni_codice_key | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| aspetti_beni_codice_key | `CREATE UNIQUE INDEX aspetti_beni_codice_key ON config.aspetti_beni USING btree (codice)` |
| ix_aspetti_beni_attivo | `CREATE INDEX ix_aspetti_beni_attivo ON config.aspetti_beni USING btree (attivo)` |
| pk_aspetti_beni | `CREATE UNIQUE INDEX pk_aspetti_beni ON config.aspetti_beni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_aspetti_beni_a10_ddt_block_deact_upd_4c6149 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ddt', 'aspetto_bene_id', 'id', 'attivo')` |
| trg_aspetti_beni_a10_ddt_block_deact_upd_efb5dd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'ddt', 'aspetto_bene_id', 'id', 'attivo')` |
| trg_aspetti_beni_a10_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('acquisti', 'ordini', 'aspetto_bene_id', 'id', 'attivo')` |
| trg_aspetti_beni_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_aspetti_beni_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_aspetti_beni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_aspetti_beni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
