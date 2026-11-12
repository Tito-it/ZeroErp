{% include-markdown "it/dbzero/config/manual/note_stili.md" %}
# 📚 Tabella `note_stili`

> 📝 **Descrizione**
>
> Dominio degli stili per le note. Normalizza il campo "stile" (es. NORMALE, GRASSETTO, AVVISO, PICCOLO).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(16) | NO |  |
| codice_interno | character varying(16) | NO |  |
| descrizione | character varying(120) | NO |  |
| attivo | boolean | NO | true |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | YES | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_cfg_note_stili_codice_interno_len |  |
| CHECK | chk_cfg_note_stili_codice_len |  |
| CHECK | chk_note_stili_note_non_vuota |  |
| PRIMARY KEY | pk_config_note_stili | id |
| UNIQUE | uq_cfg_note_stili_codice | codice |
| UNIQUE | uq_cfg_note_stili_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_note_stili_attivo | `CREATE INDEX ix_cfg_note_stili_attivo ON config.note_stili USING btree (attivo)` |
| pk_config_note_stili | `CREATE UNIQUE INDEX pk_config_note_stili ON config.note_stili USING btree (id)` |
| uq_cfg_note_stili_codice | `CREATE UNIQUE INDEX uq_cfg_note_stili_codice ON config.note_stili USING btree (codice)` |
| uq_cfg_note_stili_codice_interno | `CREATE UNIQUE INDEX uq_cfg_note_stili_codice_interno ON config.note_stili USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_stili_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_note_stili_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_stili_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_note_stili_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('note_stili_id')` |
| trg_note_stili_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('note_stili_id')` |

---
{% include-markdown "signature-core.md" %}
