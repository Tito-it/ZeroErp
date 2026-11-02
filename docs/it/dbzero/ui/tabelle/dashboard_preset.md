{% include-markdown "it/dbzero/ui/manual/dashboard_preset.md" %}
# 📚 Tabella `dashboard_preset`

> 📝 **Descrizione**
>
> Preset di dashboard per ambito: sistema (globale), emittente_fiscale, ruolo (via profilo_accesso). Ricalca ui.lista_preset.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| dashboard_id | integer | NO |  |
| codice | character varying(80) | NO |  |
| descrizione | character varying(200) | NO |  |
| ambito | ui.ambito_preset | NO |  |
| profilo_accesso_id | integer | YES |  |
| emittente_fiscale_id | integer | YES |  |
| is_default | boolean | NO | false |
| dimensione_max | integer | YES | 8 |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO |  |
| data_update | timestamp with time zone | YES |  |
| user_update | character varying(80) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ui_dashboard_preset_ambito_refs |  |
| FOREIGN KEY | fk_ui_dashboard_preset_dashboard_definizione | dashboard_id |
| FOREIGN KEY | fk_ui_dashboard_preset_emittenti_fiscali | emittente_fiscale_id |
| FOREIGN KEY | fk_ui_dashboard_preset_profili_accesso | profilo_accesso_id |
| PRIMARY KEY | dashboard_preset_pkey | id |
| UNIQUE | uq_ui_dashboard_preset_dashboard_codice | dashboard_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| dashboard_preset_pkey | `CREATE UNIQUE INDEX dashboard_preset_pkey ON ui.dashboard_preset USING btree (id)` |
| ix_ui_dashboard_preset_dashboard_id | `CREATE INDEX ix_ui_dashboard_preset_dashboard_id ON ui.dashboard_preset USING btree (dashboard_id)` |
| ix_ui_dashboard_preset_emittente_fiscale_id | `CREATE INDEX ix_ui_dashboard_preset_emittente_fiscale_id ON ui.dashboard_preset USING btree (emittente_fiscale_id) WHERE (emittente_fiscale_id IS NOT NULL)` |
| ix_ui_dashboard_preset_profilo_accesso_id | `CREATE INDEX ix_ui_dashboard_preset_profilo_accesso_id ON ui.dashboard_preset USING btree (profilo_accesso_id) WHERE (profilo_accesso_id IS NOT NULL)` |
| uq_ui_dashboard_preset_dashboard_codice | `CREATE UNIQUE INDEX uq_ui_dashboard_preset_dashboard_codice ON ui.dashboard_preset USING btree (dashboard_id, codice)` |
| uq_ui_dashboard_preset_default | `CREATE UNIQUE INDEX uq_ui_dashboard_preset_default ON ui.dashboard_preset USING btree (dashboard_id, ambito, COALESCE(profilo_accesso_id, 0), COALESCE(emittente_fiscale_id, 0)) WHERE (is_default = true)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_dashboard_preset_a20_data_update_contenuto_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preset_data_update_contenuto()` |

---
{% include-markdown "signature-core.md" %}
