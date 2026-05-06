{% include-markdown "it/dbzero/ui/manual/lista_preferenza_utente.md" %}

# 📚 Tabella `lista_preferenza_utente`

## 🗂️ Campi principali

| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | identity |
| auth_user_id | integer | NO | |
| lista_id | integer | NO | |
| preset_base_id | integer | YES | |
| preset_base_data_update | timestamp | YES | |
| configurazione | jsonb | NO | |
| data_insert | timestamp | NO | now() |
| data_update | timestamp | YES | |

> Nota: non ha `user_insert`/`user_update` — l'identità dell'utente è già in `auth_user_id`.

## 🔒 Vincoli

| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk (id) | id |
| UNIQUE | uq_ui_lista_preferenza_utente_user_lista | auth_user_id, lista_id |
| FOREIGN KEY | fk_lista_preferenza_utente_lista_definizione | lista_id → ui.lista_definizione(id) |
| FOREIGN KEY | fk_lista_preferenza_utente_lista_preset | preset_base_id → ui.lista_preset(id) |
| FOREIGN KEY | fk_lista_preferenza_utente_auth_user | auth_user_id → django.auth_user(id) ON DELETE CASCADE |

> La FK `fk_lista_preferenza_utente_auth_user` è aggiunta in `90_end` perché `django.auth_user` è creata da Django migrate, che gira dopo Liquibase.

## 📑 Indici

| Nome | Definizione |
|------|-------------|
| uq_ui_lista_preferenza_utente_user_lista | `CREATE UNIQUE INDEX ON ui.lista_preferenza_utente USING btree (auth_user_id, lista_id)` |
| ix_ui_lista_preferenza_utente_lista_id | `CREATE INDEX ON ui.lista_preferenza_utente USING btree (lista_id)` |
| ix_ui_lista_preferenza_utente_preset_base_id | `CREATE INDEX ON ui.lista_preferenza_utente (preset_base_id) WHERE preset_base_id IS NOT NULL` |

---
{% include-markdown "signature-core.md" %}
