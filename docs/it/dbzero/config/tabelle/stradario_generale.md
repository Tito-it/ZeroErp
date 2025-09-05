{% include-markdown "it/dbzero/config/manual/stradario_generale.md" %}
# 📚 Tabella `stradario_generale`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| toponomastica_id | integer | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
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
| ix_stradario_generale_toponomastica_id | `CREATE INDEX ix_stradario_generale_toponomastica_id ON config.stradario_generale USING btree (toponomastica_id)` |
| pk_stradario_generale | `CREATE UNIQUE INDEX pk_stradario_generale ON config.stradario_generale USING btree (id)` |
| uq_toponomastica_descr | `CREATE UNIQUE INDEX uq_toponomastica_descr ON config.stradario_generale USING btree (toponomastica_id, descrizione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stradario_generale_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_stradario_generale_norm()` |
| trg_stradario_generale_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stradario_generale_norm()` |
| trg_stradario_generale_upd_non_permesso | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_stradario_generale_upd_non_permesso()` |
| trg_upd_stradario_generale_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
