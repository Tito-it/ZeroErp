{% include-markdown "it/dbzero/config/manual/lingue.md" %}
# 📚 Tabella `lingue`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_iso | character varying | NO |  |
| descrizione | text | NO |  |
| descrizione_locale | text | NO |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_cfg_lingue_codice_iso_len |  |
| PRIMARY KEY | pk_config_lingue | id |
| UNIQUE | uq_cfg_lingue_codice_iso | codice_iso |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_lingue_attivo | `CREATE INDEX ix_cfg_lingue_attivo ON config.lingue USING btree (attivo)` |
| pk_config_lingue | `CREATE UNIQUE INDEX pk_config_lingue ON config.lingue USING btree (id)` |
| uq_cfg_lingue_codice_iso | `CREATE UNIQUE INDEX uq_cfg_lingue_codice_iso ON config.lingue USING btree (codice_iso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_lingue_a10_note_articoli_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli', 'id_lingua', 'id')` |
| trg_lingue_a10_note_articoli_componenti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'note_articoli_componenti', 'id_lingua', 'id')` |
| trg_lingue_a10_note_attivita_fatturabili_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_attivita_fatturabili', 'id_lingua', 'id')` |
| trg_lingue_a10_note_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note', 'id_lingua', 'id')` |
| trg_lingue_a10_note_contratto_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_contratto', 'id_lingua', 'id')` |
| trg_lingue_a10_note_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_ddt', 'id_lingua', 'id')` |
| trg_lingue_a10_note_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_fatture', 'id_lingua', 'id')` |
| trg_lingue_a10_note_ordini_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_ordini', 'id_lingua', 'id')` |
| trg_lingue_a10_note_preventivo_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'note_preventivo', 'id_lingua', 'id')` |
| trg_lingue_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
