{% include-markdown "it/dbzero/ui/manual/lista_preset.md" %}

# 📚 Tabella `lista_preset`

## 🗂️ Campi principali

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | identity |
| lista_id | integer | NO | |
| codice | character varying(80) | NO | |
| descrizione | character varying(200) | NO | |
| ambito | ui.ambito_preset | NO | |
| profilo_accesso_id | integer | YES | |
| emittente_fiscale_id | integer | YES | |
| is_default | boolean | NO | false |
| pagina_dimensione | integer | YES | 25 |
| ordinamento_default | jsonb | YES | |
| filtri_default | jsonb | YES | |
| attivo | boolean | NO | true |
| data_insert | timestamp | NO | now() |
| user_insert | character varying(80) | NO | |
| data_update | timestamp | YES | |
| user_update | character varying(80) | YES | |

## 🔒 Vincoli

| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk (id) | id |
| UNIQUE | uq_ui_lista_preset_lista_codice | lista_id, codice |
| CHECK | chk_ui_lista_preset_ambito_refs | coerenza ambito / profilo_accesso_id / emittente_fiscale_id |
| FOREIGN KEY | fk_lista_preset_lista_definizione | lista_id → ui.lista_definizione(id) |
| FOREIGN KEY | fk_lista_preset_profili_accesso | profilo_accesso_id → config.profili_accesso(id) |
| FOREIGN KEY | fk_lista_preset_emittenti_fiscali | emittente_fiscale_id → anagrafiche.emittenti_fiscali(id) |

## 📑 Indici

| Nome | Definizione |
|------|-------------|
| uq_ui_lista_preset_lista_codice | `CREATE UNIQUE INDEX ON ui.lista_preset USING btree (lista_id, codice)` |
| uq_ui_lista_preset_default | `CREATE UNIQUE INDEX ON ui.lista_preset (lista_id, ambito, COALESCE(profilo_accesso_id,0), COALESCE(emittente_fiscale_id,0)) WHERE is_default = TRUE` |
| ix_ui_lista_preset_lista_id | `CREATE INDEX ON ui.lista_preset USING btree (lista_id)` |
| ix_ui_lista_preset_profilo_accesso_id | `CREATE INDEX ON ui.lista_preset (profilo_accesso_id) WHERE profilo_accesso_id IS NOT NULL` |
| ix_ui_lista_preset_emittente_fiscale_id | `CREATE INDEX ON ui.lista_preset (emittente_fiscale_id) WHERE emittente_fiscale_id IS NOT NULL` |

---
{% include-markdown "signature-core.md" %}
