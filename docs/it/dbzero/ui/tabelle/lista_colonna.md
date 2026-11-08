{% include-markdown "it/dbzero/ui/manual/lista_colonna.md" %}
# 📚 Tabella `lista_colonna`

> 📝 **Descrizione**
>
> Catalogo colonne disponibili per ciascuna lista. Definisce tutto cio che la lista puo mostrare.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| lista_id | integer | NO |  |
| codice | character varying(80) | NO |  |
| etichetta | character varying(120) | NO |  |
| etichetta_estesa | character varying(200) | YES |  |
| campo_sorgente | character varying(120) | YES |  |
| tipo_colonna | ui.tipo_colonna | NO | 'informazione'::ui.tipo_colonna |
| tipo_dato | ui.tipo_dato | NO |  |
| formato | character varying(40) | YES |  |
| larghezza_default | integer | YES |  |
| ordine_default | integer | NO |  |
| allineamento | ui.allineamento_colonna | NO | 'left'::ui.allineamento_colonna |
| gruppo | character varying(60) | YES |  |
| gruppo_ordine | integer | YES |  |
| filtrabile | boolean | NO | true |
| ordinabile | boolean | NO | true |
| esportabile | boolean | NO | true |
| ricercabile_full | boolean | NO | false |
| sensibile | boolean | NO | false |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO |  |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |
| etichetta_i18n_key | character varying(120) | YES |  |
| priorita | smallint | NO | 50 |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ui_lista_colonna_azione_non_esportabile |  |
| CHECK | chk_ui_lista_colonna_priorita_non_negativa |  |
| FOREIGN KEY | fk_lista_colonna_lista_definizione | lista_id |
| PRIMARY KEY | lista_colonna_pkey | id |
| UNIQUE | uq_ui_lista_colonna_lista_codice | lista_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_lista_colonna_lista_id | `CREATE INDEX ix_ui_lista_colonna_lista_id ON ui.lista_colonna USING btree (lista_id)` |
| lista_colonna_pkey | `CREATE UNIQUE INDEX lista_colonna_pkey ON ui.lista_colonna USING btree (id)` |
| uq_ui_lista_colonna_lista_codice | `CREATE UNIQUE INDEX uq_ui_lista_colonna_lista_codice ON ui.lista_colonna USING btree (lista_id, codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_lista_colonna_a10_lista_definizione_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('ui', 'lista_definizione', 'attivo', 'lista_id', 'id')` |
| trg_lista_colonna_a10_lista_definizione_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('ui', 'lista_definizione', 'attivo', 'lista_id', 'id')` |
| trg_lista_colonna_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_lista_colonna_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ui_lista_colonna_a10_valida_campo_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()` |
| trg_ui_lista_colonna_a10_valida_campo_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()` |

---
{% include-markdown "signature-core.md" %}
