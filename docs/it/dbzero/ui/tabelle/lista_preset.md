{% include-markdown "it/dbzero/ui/manual/lista_preset.md" %}
# 📚 Tabella `lista_preset`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| lista_id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| ambito | USER-DEFINED | NO |  |
| profilo_accesso_id | integer | YES |  |
| emittente_fiscale_id | bigint | YES |  |
| is_default | boolean | NO | false |
| pagina_dimensione | integer | YES | 25 |
| ordinamento_default | jsonb | YES |  |
| filtri_default | jsonb | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO |  |
| data_update | timestamp without time zone | YES |  |
| user_update | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ui_lista_preset_ambito_refs |  |
| FOREIGN KEY | fk_lista_preset_emittenti_fiscali | emittente_fiscale_id |
| FOREIGN KEY | fk_lista_preset_lista_definizione | lista_id |
| FOREIGN KEY | fk_lista_preset_profili_accesso | profilo_accesso_id |
| PRIMARY KEY | lista_preset_pkey | id |
| UNIQUE | uq_ui_lista_preset_lista_codice | lista_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_lista_preset_emittente_fiscale_id | `CREATE INDEX ix_ui_lista_preset_emittente_fiscale_id ON ui.lista_preset USING btree (emittente_fiscale_id) WHERE (emittente_fiscale_id IS NOT NULL)` |
| ix_ui_lista_preset_lista_id | `CREATE INDEX ix_ui_lista_preset_lista_id ON ui.lista_preset USING btree (lista_id)` |
| ix_ui_lista_preset_profilo_accesso_id | `CREATE INDEX ix_ui_lista_preset_profilo_accesso_id ON ui.lista_preset USING btree (profilo_accesso_id) WHERE (profilo_accesso_id IS NOT NULL)` |
| lista_preset_pkey | `CREATE UNIQUE INDEX lista_preset_pkey ON ui.lista_preset USING btree (id)` |
| uq_ui_lista_preset_default | `CREATE UNIQUE INDEX uq_ui_lista_preset_default ON ui.lista_preset USING btree (lista_id, ambito, COALESCE(profilo_accesso_id, 0), COALESCE(emittente_fiscale_id, (0)::bigint)) WHERE (is_default = true)` |
| uq_ui_lista_preset_lista_codice | `CREATE UNIQUE INDEX uq_ui_lista_preset_lista_codice ON ui.lista_preset USING btree (lista_id, codice)` |

---
{% include-markdown "signature-core.md" %}
