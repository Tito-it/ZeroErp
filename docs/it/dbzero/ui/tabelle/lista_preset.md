{% include-markdown "it/dbzero/ui/manual/lista_preset.md" %}
# 📚 Tabella `lista_preset`

> 📝 **Descrizione**
>
> Le configurazioni predefinite di una lista per ambito: di sistema, per un'azienda (emittente fiscale) o per un profilo di accesso (ruolo). Dice quali colonne mostrare (ui.lista_preset_colonna), l'ordinamento di partenza e le righe per pagina. Il posto del preset (lista, ambito, profilo, azienda) non cambia, e ha un solo preset acceso. La scelta del preset di base è ui.fn_preset_di_base.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| lista_id | integer | NO |  |
| codice | character varying(80) | NO |  |
| descrizione | character varying(200) | NO |  |
| ambito | ui.ambito_preset | NO |  |
| profilo_accesso_id | integer | YES |  |
| emittente_fiscale_id | bigint | YES |  |
| pagina_dimensione | integer | YES |  |
| ordinamento_default | jsonb | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying(80) | NO |  |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying(80) | NO | CURRENT_USER |
| contenuto_aggiornato_il | jsonb | NO |  |
| composizione_impronta | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ui_lista_preset_ambito_refs |  |
| FOREIGN KEY | fk_lista_preset_emittenti_fiscali | emittente_fiscale_id |
| FOREIGN KEY | fk_lista_preset_lista_definizione | lista_id |
| FOREIGN KEY | fk_lista_preset_misure_pagina | pagina_dimensione |
| FOREIGN KEY | fk_lista_preset_profili_accesso | profilo_accesso_id |
| PRIMARY KEY | lista_preset_pkey | id |
| UNIQUE | uq_ui_lista_preset_id_lista | id, lista_id |
| UNIQUE | uq_ui_lista_preset_lista_codice | lista_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_lista_preset_emittente_fiscale_id | `CREATE INDEX ix_ui_lista_preset_emittente_fiscale_id ON ui.lista_preset USING btree (emittente_fiscale_id) WHERE (emittente_fiscale_id IS NOT NULL)` |
| ix_ui_lista_preset_profilo_accesso_id | `CREATE INDEX ix_ui_lista_preset_profilo_accesso_id ON ui.lista_preset USING btree (profilo_accesso_id) WHERE (profilo_accesso_id IS NOT NULL)` |
| lista_preset_pkey | `CREATE UNIQUE INDEX lista_preset_pkey ON ui.lista_preset USING btree (id)` |
| uq_ui_lista_preset_id_lista | `CREATE UNIQUE INDEX uq_ui_lista_preset_id_lista ON ui.lista_preset USING btree (id, lista_id)` |
| uq_ui_lista_preset_lista_codice | `CREATE UNIQUE INDEX uq_ui_lista_preset_lista_codice ON ui.lista_preset USING btree (lista_id, codice)` |
| uq_ui_lista_preset_posto | `CREATE UNIQUE INDEX uq_ui_lista_preset_posto ON ui.lista_preset USING btree (lista_id, ambito, profilo_accesso_id, emittente_fiscale_id) NULLS NOT DISTINCT WHERE attivo` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_lista_preset_a00_seed_primo_impianto_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_seed_primo_impianto('COLONNA', 'lista_id,codice,ambito,profilo_accesso_id,emittente_fiscale_id', 'descrizione,pagina_dimensione,ordinamento_default,attivo,contenuto_aggiornato_il,composizione_impronta')` |
| trg_lista_preset_a00_seed_primo_impianto_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_seed_primo_impianto('COLONNA', 'lista_id,codice,ambito,profilo_accesso_id,emittente_fiscale_id', 'descrizione,pagina_dimensione,ordinamento_default,attivo,contenuto_aggiornato_il,composizione_impronta')` |
| trg_lista_preset_a00_seed_primo_impianto_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_seed_primo_impianto('COLONNA', 'lista_id,codice,ambito,profilo_accesso_id,emittente_fiscale_id', 'descrizione,pagina_dimensione,ordinamento_default,attivo,contenuto_aggiornato_il,composizione_impronta')` |
| trg_lista_preset_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('ambito', 'E_UI_PRESET_POSTO_IMMUTABILE', 'emittente_fiscale_id', 'E_UI_PRESET_POSTO_IMMUTABILE', 'lista_id', 'E_UI_PRESET_POSTO_IMMUTABILE', 'profilo_accesso_id', 'E_UI_PRESET_POSTO_IMMUTABILE')` |
| trg_lista_preset_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_lista_preset_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ui_lista_preset_a10_guard_ordinamento_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_ui_lista_preset_guard_ordinamento()` |
| trg_ui_lista_preset_a10_guard_ordinamento_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_ui_lista_preset_guard_ordinamento()` |
| trg_ui_lista_preset_a10_guard_pagina_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_ui_lista_preset_guard_pagina_dimensione()` |
| trg_ui_lista_preset_a10_guard_pagina_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_ui_lista_preset_guard_pagina_dimensione()` |
| trg_ui_lista_preset_a20_contenuto_aggiornato_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preset_contenuto_aggiornato()` |
| trg_ui_lista_preset_a20_contenuto_aggiornato_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preset_contenuto_aggiornato()` |

---
{% include-markdown "signature-core.md" %}
