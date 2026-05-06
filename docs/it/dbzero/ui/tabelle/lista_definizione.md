{% include-markdown "it/dbzero/ui/manual/lista_definizione.md" %}

# 📚 Tabella `lista_definizione`

## 🗂️ Campi principali

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | identity |
| codice | character varying(80) | NO | |
| descrizione | character varying(200) | NO | |
| schema_dati | character varying(40) | NO | |
| vista_sql | character varying(120) | YES | |
| note | text | YES | |
| attivo | boolean | NO | true |
| data_insert | timestamp | NO | now() |
| user_insert | character varying(80) | NO | |
| data_update | timestamp | YES | |
| user_update | character varying(80) | YES | |

## 🔒 Vincoli

| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk (id) | id |
| UNIQUE | uq_ui_lista_definizione_codice | codice |

## 📑 Indici

| Nome | Definizione |
|------|-------------|
| uq_ui_lista_definizione_codice | `CREATE UNIQUE INDEX ON ui.lista_definizione USING btree (codice)` |

## 🚨 Trigger

| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_lista_definizione_a10_valida_vista_sql_ins_upd | BEFORE | INSERT, UPDATE OF vista_sql, attivo | `EXECUTE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()` |

---
{% include-markdown "signature-core.md" %}
