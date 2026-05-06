{% include-markdown "it/dbzero/ui/manual/lista_colonna.md" %}

# 📚 Tabella `lista_colonna`

## 🗂️ Campi principali

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | identity |
| lista_id | integer | NO | |
| codice | character varying(80) | NO | |
| etichetta | character varying(120) | NO | |
| etichetta_estesa | character varying(200) | YES | |
| campo_sorgente | character varying(120) | YES | |
| tipo_colonna | ui.tipo_colonna | NO | 'informazione' |
| tipo_dato | ui.tipo_dato | NO | |
| formato | character varying(40) | YES | |
| larghezza_default | integer | YES | |
| ordine_default | integer | NO | |
| allineamento | ui.allineamento_colonna | NO | 'left' |
| gruppo | character varying(60) | YES | |
| gruppo_ordine | integer | YES | |
| filtrabile | boolean | NO | true |
| ordinabile | boolean | NO | true |
| esportabile | boolean | NO | true |
| ricercabile_full | boolean | NO | false |
| sensibile | boolean | NO | false |
| attivo | boolean | NO | true |
| data_insert | timestamp | NO | now() |
| user_insert | character varying(80) | NO | |
| data_update | timestamp | YES | |
| user_update | character varying(80) | YES | |

## 🔒 Vincoli

| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk (id) | id |
| UNIQUE | uq_ui_lista_colonna_lista_codice | lista_id, codice |
| CHECK | chk_ui_lista_colonna_azione_non_esportabile | `tipo_colonna <> 'azione' OR esportabile = FALSE` |
| FOREIGN KEY | fk_lista_colonna_lista_definizione | lista_id → ui.lista_definizione(id) |

## 📑 Indici

| Nome | Definizione |
|------|-------------|
| uq_ui_lista_colonna_lista_codice | `CREATE UNIQUE INDEX ON ui.lista_colonna USING btree (lista_id, codice)` |
| ix_ui_lista_colonna_lista_id | `CREATE INDEX ON ui.lista_colonna USING btree (lista_id)` |

## 🚨 Trigger

| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_lista_colonna_a10_valida_campo_sorgente_ins_upd | BEFORE | INSERT, UPDATE OF campo_sorgente, tipo_colonna, lista_id | `EXECUTE FUNCTION ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente()` |

---
{% include-markdown "signature-core.md" %}
