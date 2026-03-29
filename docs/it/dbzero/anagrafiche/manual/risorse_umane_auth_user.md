## 📘 Documentazione Concettuale – Tabella `anagrafiche.risorse_umane_auth_user`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [django.auth_user](/dbzero/django/auth_user)

---
### 🎯 Scopo Principale
(latest revision 06-01-26)
La tabella **`anagrafiche.risorse_umane_auth_user`** gestisce il collegamento **1:1**
tra una risorsa umana e l'utente software Django.

---

### Collegamenti principali

* `risorsa_umana_id` → `anagrafiche.risorse_umane(id)`
* `auth_user_id` → `django.auth_user(id)`

---

### Regole

* Un solo utente per risorsa (`UNIQUE risorsa_umana_id`).
* Una risorsa per utente (`UNIQUE auth_user_id`).
* Il collegamento e' consentito solo se la risorsa appartiene al soggetto gestore.

---

### Campi di gestione autenticazione avanzata

Aggiunti con changeset `20260328-19`:

| Campo | Tipo | Default | Scopo |
|-------|------|---------|-------|
| `deve_cambiare_password` | boolean NOT NULL | `false` | Se `true`, l'operatore deve cambiare password al prossimo login. Impostato a `true` alla creazione account o su richiesta admin. Dopo il cambio password viene resettato a `false`. |
| `invito_inviato_at` | timestamptz | NULL | Timestamp dell'ultimo invito inviato. `NULL` = mai invitato. Usato per il flusso di invito primo accesso (Fase 3). |
| `totp_obbligatorio` | boolean NOT NULL | `false` | Se `true`, l'operatore DEVE configurare il 2FA TOTP per accedere. Se il device non e' configurato, un middleware blocca la navigazione e forza il setup. (Fase 4, changeset -21) |

Il campo `deve_cambiare_password` viene letto dal login (`AuditTokenObtainPairView`): se `true`, il response include `password_change_required: true` e un middleware blocca la navigazione fino al cambio password.

Il campo `totp_obbligatorio` viene letto da `fn_get_user_profile` e propagato al frontend. Se `true` e il 2FA non e' configurato, il comportamento e' analogo al cambio password: blocco navigazione fino al completamento del setup.

---

### Note operative

* La presenza del collegamento e' opzionale: non tutte le risorse
  devono avere un account software.
* La tabella ponte viene creata solo se lo schema `django` e la tabella
  `auth_user` sono presenti nel database (precondition in Liquibase).

---

{% include-markdown "signature-core.md" %}
