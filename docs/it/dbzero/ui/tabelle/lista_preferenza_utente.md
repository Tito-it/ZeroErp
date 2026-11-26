{% include-markdown "it/dbzero/ui/manual/lista_preferenza_utente.md" %}
# 📚 Tabella `lista_preferenza_utente`

> 📝 **Descrizione**
>
> La personalizzazione di una lista per un utente: una riga per utente e lista. La configurazione porta solo le chiavi che l'utente ha scelto (colonne, pagina_dimensione); le altre le dà il preset di base (ui.fn_preset_di_base), e ui.fn_resolve_lista_config compone le due. La forma la controlla ui.trgfn_preferenza_guard_forma. Senza audit, per scelta: e' un dato personale, scritto spesso dal suo proprietario; il database lo riscrive quando ritira una voce uscita dal catalogo (ui.trgfn_voce_ritira_dalle_preferenze per una colonna, ui.trgfn_misure_pagina_ritira_dalle_preferenze per una misura). data_update la scrive il database a ogni scrittura (ui.trgfn_preferenza_data_update), anche la sua: e' l'ultima scrittura della riga. Non c'e' user_update.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| auth_user_id | integer | NO |  |
| lista_id | integer | NO |  |
| preset_base_id | integer | YES |  |
| preset_base_contenuto_aggiornato_il | jsonb | YES |  |
| configurazione | jsonb | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_lista_preferenza_utente_auth_user | auth_user_id |
| FOREIGN KEY | fk_lista_preferenza_utente_lista_definizione | lista_id |
| FOREIGN KEY | fk_lista_preferenza_utente_lista_preset | preset_base_id |
| FOREIGN KEY | fk_ui_lista_preferenza_utente_preset_della_lista | preset_base_id, lista_id |
| PRIMARY KEY | lista_preferenza_utente_pkey | id |
| UNIQUE | uq_ui_lista_preferenza_utente_user_lista | auth_user_id, lista_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ui_lista_preferenza_utente_lista_id | `CREATE INDEX ix_ui_lista_preferenza_utente_lista_id ON ui.lista_preferenza_utente USING btree (lista_id)` |
| ix_ui_lista_preferenza_utente_preset_base_id | `CREATE INDEX ix_ui_lista_preferenza_utente_preset_base_id ON ui.lista_preferenza_utente USING btree (preset_base_id) WHERE (preset_base_id IS NOT NULL)` |
| lista_preferenza_utente_pkey | `CREATE UNIQUE INDEX lista_preferenza_utente_pkey ON ui.lista_preferenza_utente USING btree (id)` |
| uq_ui_lista_preferenza_utente_user_lista | `CREATE UNIQUE INDEX uq_ui_lista_preferenza_utente_user_lista ON ui.lista_preferenza_utente USING btree (auth_user_id, lista_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_lista_preferenza_utente_a10_guard_forma_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preferenza_guard_forma()` |
| trg_ui_lista_preferenza_utente_a10_guard_forma_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preferenza_guard_forma()` |
| trg_ui_lista_preferenza_utente_a20_set_data_update_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preferenza_data_update()` |
| trg_ui_lista_preferenza_utente_a20_set_data_update_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preferenza_data_update()` |
| trg_ui_lista_preferenza_utente_z90_snapshot_base_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preferenza_preset_base_snapshot('ui.lista_preset')` |
| trg_ui_lista_preferenza_utente_z90_snapshot_base_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preferenza_preset_base_snapshot('ui.lista_preset')` |

---
{% include-markdown "signature-core.md" %}
