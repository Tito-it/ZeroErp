{% include-markdown "it/dbzero/config/manual/causali_onere.md" %}
# 📚 Tabella `causali_onere`

> 📝 **Descrizione**
>
> Vocabolario causale della porta oneri (brief-db-immutabilita-quantita-e-porta-oneri §4c.3). Nomina il perche' dell'importo di una riga commesse_attivita tipo_movimento=ONERE (qta=1, valore). Mono-lingua: la descrizione e' il label (pattern tipi_reso, nessun IF hardcoded). rev 2026-07-21.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(64) | NO |  |
| codice | character varying(64) | NO |  |
| descrizione | character varying(160) | NO |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_causali_onere | id |
| UNIQUE | uq_causali_onere_codice | codice |
| UNIQUE | uq_causali_onere_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_causali_onere_attivo | `CREATE INDEX ix_causali_onere_attivo ON config.causali_onere USING btree (attivo)` |
| ix_causali_onere_ordine | `CREATE INDEX ix_causali_onere_ordine ON config.causali_onere USING btree (ordine)` |
| pk_causali_onere | `CREATE UNIQUE INDEX pk_causali_onere ON config.causali_onere USING btree (id)` |
| uq_causali_onere_codice | `CREATE UNIQUE INDEX uq_causali_onere_codice ON config.causali_onere USING btree (codice)` |
| uq_causali_onere_codice_interno | `CREATE UNIQUE INDEX uq_causali_onere_codice_interno ON config.causali_onere USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_causali_onere_a10_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'articoli', 'causale_onere_id', 'id', 'attivo')` |
| trg_causali_onere_a10_commesse_attivita_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'commesse_attivita', 'causale_onere_id', 'id', 'attivo')` |
| trg_causali_onere_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_causali_onere_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_causali_onere_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_causali_onere_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_causali_onere_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
