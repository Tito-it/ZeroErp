{% include-markdown "it/dbzero/documenti/manual/render_engine_documento.md" %}
# 📚 Tabella `render_engine_documento`

> 📝 **Descrizione**
>
> I motori che rendono una versione di modello in PDF. Un motore e' codice: la riga nasce con il changeSet che accompagna il codice che lo sa usare. L'applicazione li legge soltanto.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(80) | NO |  |
| codice_interno | character varying(80) | NO |  |
| descrizione | text | NO |  |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| etichetta_key | character varying(120) | NO |  |
| ordine | smallint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_render_engine_documento_codice_interno_non_vuoto |  |
| CHECK | chk_render_engine_documento_codice_non_vuoto |  |
| CHECK | chk_render_engine_documento_descrizione_non_vuota |  |
| PRIMARY KEY | render_engine_documento_pkey | id |
| UNIQUE | uq_render_engine_documento_codice | codice |
| UNIQUE | uq_render_engine_documento_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| render_engine_documento_pkey | `CREATE UNIQUE INDEX render_engine_documento_pkey ON documenti.render_engine_documento USING btree (id)` |
| uq_render_engine_documento_codice | `CREATE UNIQUE INDEX uq_render_engine_documento_codice ON documenti.render_engine_documento USING btree (codice)` |
| uq_render_engine_documento_codice_interno | `CREATE UNIQUE INDEX uq_render_engine_documento_codice_interno ON documenti.render_engine_documento USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_render_engine_documento_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_render_engine_documento_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_render_engine_documento_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_render_engine_documento_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_render_engine_documento_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_render_engine_documento_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_render_engine_documento_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
