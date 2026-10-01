{% include-markdown "it/dbzero/ui/manual/lista_definizione.md" %}
# 📚 Tabella `lista_definizione`

> 📝 **Descrizione**
>
> Catalogo delle liste configurabili. Una riga per lista personalizzabile.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| schema_dati | character varying | NO |  |
| vista_sql | character varying | YES |  |
| note | text | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO |  |
| data_update | timestamp with time zone | YES |  |
| user_update | character varying | YES |  |
| multi_emittente | boolean | NO | false |
| perimetro_emittente | boolean | NO | true |
| ricerca_min_caratteri | smallint | NO | 3 |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ui_lista_definizione_perimetro_coerente |  |
| CHECK | chk_ui_lista_definizione_ricerca_min_caratteri |  |
| PRIMARY KEY | lista_definizione_pkey | id |
| UNIQUE | uq_ui_lista_definizione_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| lista_definizione_pkey | `CREATE UNIQUE INDEX lista_definizione_pkey ON ui.lista_definizione USING btree (id)` |
| uq_ui_lista_definizione_codice | `CREATE UNIQUE INDEX uq_ui_lista_definizione_codice ON ui.lista_definizione USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_lista_definizione_guard_multi_emittente()` |
| trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_lista_definizione_guard_multi_emittente()` |
| trg_ui_lista_definizione_a10_valida_vista_sql_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()` |
| trg_ui_lista_definizione_a10_valida_vista_sql_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()` |

---
{% include-markdown "signature-core.md" %}
