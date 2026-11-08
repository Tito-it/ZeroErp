{% include-markdown "it/dbzero/config/manual/stati_assets.md" %}
# 📚 Tabella `stati_assets`

> 📝 **Descrizione**
>
> Dominio stati dell'asset (codici stabili; descrizioni multilingua via meta)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(32) | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_assets | id |
| UNIQUE | uq_stati_assets_codice | codice |
| UNIQUE | uq_stati_assets_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_assets_attivo | `CREATE INDEX ix_stati_assets_attivo ON config.stati_assets USING btree (attivo)` |
| pk_stati_assets | `CREATE UNIQUE INDEX pk_stati_assets ON config.stati_assets USING btree (id)` |
| uq_stati_assets_codice | `CREATE UNIQUE INDEX uq_stati_assets_codice ON config.stati_assets USING btree (codice)` |
| uq_stati_assets_codice_interno | `CREATE UNIQUE INDEX uq_stati_assets_codice_interno ON config.stati_assets USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_assets_a10_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'assets', 'stato_id', 'id', 'attivo')` |
| trg_stati_assets_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_assets_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_assets_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_assets_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_assets_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
