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
| codice | character varying | NO |  |
| etichetta | character varying | NO |  |
| etichetta_estesa | character varying | YES |  |
| campo_sorgente | character varying | YES |  |
| tipo_colonna | USER-DEFINED | NO | 'informazione'::ui.tipo_colonna |
| tipo_dato | USER-DEFINED | NO |  |
| formato | character varying | YES |  |
| larghezza_default | integer | YES |  |
| ordine_default | integer | NO |  |
| allineamento | USER-DEFINED | NO | 'left'::ui.allineamento_colonna |
| gruppo | character varying | YES |  |
| gruppo_ordine | integer | YES |  |
| filtrabile | boolean | NO | true |
| ordinabile | boolean | NO | true |
| esportabile | boolean | NO | true |
| ricercabile_full | boolean | NO | false |
| sensibile | boolean | NO | false |
| attivo | boolean | NO | true |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO |  |
| data_update | timestamp without time zone | YES |  |
| user_update | character varying | YES |  |
| etichetta_i18n_key | character varying | YES |  |
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
| trg_ui_lista_colonna_a10_valida_campo_sorgente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()` |
| trg_ui_lista_colonna_a10_valida_campo_sorgente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()` |

---
{% include-markdown "signature-core.md" %}
