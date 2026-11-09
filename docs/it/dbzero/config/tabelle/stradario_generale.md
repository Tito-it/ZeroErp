{% include-markdown "it/dbzero/config/manual/stradario_generale.md" %}
# 📚 Tabella `stradario_generale`

> 📝 **Descrizione**
>
> Stradario generale: vie, strade, piazze con riferimento alla toponomastica.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| toponomastica_id | integer | NO |  |
| descrizione | character varying(100) | NO |  |
| descrizione_breve | character varying(50) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| indirizzo_normalizzato | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_stradario_generale_toponomastica_id | toponomastica_id |
| PRIMARY KEY | pk_stradario_generale | id |
| UNIQUE | uq_toponomastica_descr | toponomastica_id, descrizione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stradario_generale_norm_trgm | `CREATE INDEX ix_stradario_generale_norm_trgm ON config.stradario_generale USING gin (indirizzo_normalizzato gin_trgm_ops)` |
| pk_stradario_generale | `CREATE UNIQUE INDEX pk_stradario_generale ON config.stradario_generale USING btree (id)` |
| uq_toponomastica_descr | `CREATE UNIQUE INDEX uq_toponomastica_descr ON config.stradario_generale USING btree (toponomastica_id, descrizione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stradario_generale_a10_toponomastica_require_attivo_cb898e | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'toponomastica', 'attivo', 'toponomastica_id', 'id')` |
| trg_stradario_generale_a10_toponomastica_require_attivo_cb898e | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'toponomastica', 'attivo', 'toponomastica_id', 'id')` |
| trg_stradario_generale_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stradario_generale_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stradario_generale_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stradario_generale_normalize()` |
| trg_stradario_generale_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_stradario_generale_normalize()` |
| trg_stradario_generale_protect_update_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stradario_generale_protect_update()` |

---
{% include-markdown "signature-core.md" %}
