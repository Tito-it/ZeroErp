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

### Note operative

* La presenza del collegamento e' opzionale: non tutte le risorse
  devono avere un account software.
* La tabella ponte viene creata solo se lo schema `django` e la tabella
  `auth_user` sono presenti nel database (precondition in Liquibase).

---

{% include-markdown "signature-core.md" %}
