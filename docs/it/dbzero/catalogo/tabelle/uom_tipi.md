{% include-markdown "it/dbzero/catalogo/manual/uom_tipi.md" %}
# 📚 Tabella `uom_tipi`

> 📝 **Descrizione**
>
> Tipologie/dimensioni fisiche delle unita di misura.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(30) | NO |  |
| codice_interno | character varying(30) | NO |  |
| descrizione | character varying(120) | NO |  |
| attivo | boolean | NO | true |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_uom_tipi | id |
| UNIQUE | uq_uom_tipi_codice | codice |
| UNIQUE | uq_uom_tipi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_uom_tipi | `CREATE UNIQUE INDEX pk_uom_tipi ON catalogo.uom_tipi USING btree (id)` |
| uq_uom_tipi_codice | `CREATE UNIQUE INDEX uq_uom_tipi_codice ON catalogo.uom_tipi USING btree (codice)` |
| uq_uom_tipi_codice_interno | `CREATE UNIQUE INDEX uq_uom_tipi_codice_interno ON catalogo.uom_tipi USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_uom_tipi_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_uom_tipi_a10_unita_misura_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('catalogo', 'unita_misura', 'tipo_uom_id', 'id', 'attivo')` |
| trg_uom_tipi_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_uom_tipi_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_uom_tipi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_uom_tipi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
