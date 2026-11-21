{% include-markdown "it/dbzero/ui/manual/dashboard_preferenza_utente.md" %}
# 📚 Tabella `dashboard_preferenza_utente`

> 📝 **Descrizione**
>
> La personalizzazione di una dashboard per un utente: una riga per utente e dashboard. La configurazione porta solo le chiavi che l'utente ha scelto (widget, dimensione_max); le altre le dà il preset di base (ui.fn_preset_di_base), e ui.fn_resolve_dashboard_config compone le due. La forma la controlla ui.trgfn_preferenza_guard_forma. Senza audit, per scelta: e' un dato personale, scritto solo dal suo proprietario e spesso; data_update la scrive il database a ogni scrittura (ui.trgfn_preferenza_data_update), e non c'e' user_update.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| auth_user_id | integer | NO |  |
| dashboard_id | integer | NO |  |
| preset_base_id | integer | YES |  |
| preset_base_contenuto_aggiornato_il | jsonb | YES |  |
| configurazione | jsonb | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_auth_user | auth_user_id |
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_dashboard_definizione | dashboard_id |
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_dashboard_preset | preset_base_id |
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_preset_della_dashboard | preset_base_id, dashboard_id |
| PRIMARY KEY | dashboard_preferenza_utente_pkey | id |
| UNIQUE | uq_ui_dashboard_preferenza_utente_user_dashboard | auth_user_id, dashboard_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| dashboard_preferenza_utente_pkey | `CREATE UNIQUE INDEX dashboard_preferenza_utente_pkey ON ui.dashboard_preferenza_utente USING btree (id)` |
| ix_ui_dashboard_preferenza_utente_dashboard_id | `CREATE INDEX ix_ui_dashboard_preferenza_utente_dashboard_id ON ui.dashboard_preferenza_utente USING btree (dashboard_id)` |
| ix_ui_dashboard_preferenza_utente_preset_base_id | `CREATE INDEX ix_ui_dashboard_preferenza_utente_preset_base_id ON ui.dashboard_preferenza_utente USING btree (preset_base_id) WHERE (preset_base_id IS NOT NULL)` |
| uq_ui_dashboard_preferenza_utente_user_dashboard | `CREATE UNIQUE INDEX uq_ui_dashboard_preferenza_utente_user_dashboard ON ui.dashboard_preferenza_utente USING btree (auth_user_id, dashboard_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ui_dashboard_preferenza_utente_a10_guard_forma_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preferenza_guard_forma()` |
| trg_ui_dashboard_preferenza_utente_a10_guard_forma_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preferenza_guard_forma()` |
| trg_ui_dashboard_preferenza_utente_a20_set_data_update_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preferenza_data_update()` |
| trg_ui_dashboard_preferenza_utente_a20_set_data_update_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preferenza_data_update()` |
| trg_ui_dashboard_preferenza_utente_z90_snapshot_base_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION ui.trgfn_preferenza_preset_base_snapshot('ui.dashboard_preset')` |
| trg_ui_dashboard_preferenza_utente_z90_snapshot_base_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_preferenza_preset_base_snapshot('ui.dashboard_preset')` |

---
{% include-markdown "signature-core.md" %}
