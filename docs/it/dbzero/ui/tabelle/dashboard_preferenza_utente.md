{% include-markdown "it/dbzero/ui/manual/dashboard_preferenza_utente.md" %}
# 📚 Tabella `dashboard_preferenza_utente`

> 📝 **Descrizione**
>
> Preferenza personale utente per dashboard. JSONB per resilienza ad evoluzioni. Ricalca ui.lista_preferenza_utente.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| auth_user_id | integer | NO |  |
| dashboard_id | integer | NO |  |
| preset_base_id | integer | YES |  |
| preset_base_contenuto_aggiornato_il | timestamp with time zone | YES |  |
| preset_aggiornato_ignored_at | timestamp with time zone | YES |  |
| configurazione | jsonb | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_auth_user | auth_user_id |
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_dashboard_definizione | dashboard_id |
| FOREIGN KEY | fk_ui_dashboard_preferenza_utente_dashboard_preset | preset_base_id |
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
| trg_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts_upd | BEFORE | UPDATE | `EXECUTE FUNCTION ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts()` |

---
{% include-markdown "signature-core.md" %}
