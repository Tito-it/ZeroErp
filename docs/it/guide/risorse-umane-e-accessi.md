# 📘 Guida Tecnica – Risorse Umane e Accessi al Software

> (latest review 07-01-26)
>
> 📋 **Destinatari:** sviluppatori database, backend, integratori e analisti funzionali
>
> 👀 **Vedi anche**
>
> * [Guida Soggetti & Ruoli](/guide/soggetti-e-ruoli-anagrafici)
> * [Gestione dei contatti](/guide/gestione-dei-contatti)
>
---

## 🎯 Obiettivo

Definire un modello coerente per:

* rappresentare le **risorse umane** (dipendenti, consulenti, collaboratori);
* collegare opzionalmente una risorsa a un **utente Django**;
* governare l’**accesso al software** in base allo stato della risorsa;
* demandare le **autorizzazioni** ai gruppi/permessi di Django.

---

## 🧩 Modello dati (sintesi)

### 1) `anagrafiche.risorse_umane`

Tabella operativa che rappresenta una **persona** legata a un soggetto tramite ruolo **RISORSA_UMANA**.

Campi chiave:

* `soggetto_id`: soggetto (azienda) a cui la risorsa appartiene
* `soggetto_ruolo_id`: ruolo RISORSA_UMANA
* `qualifica_id`: mansione/posizione (es. Amministratore, Dipendente, Consulente)
* `unita_organizzativa_id`: reparto/ufficio (opzionale)
* `valido_dal`, `valido_al`: finestra di validita
* `attivo`: flag operativo

### 2) `anagrafiche.risorse_umane_auth_user`

Tabella ponte **1:1** tra una risorsa e un utente Django.

Campi chiave:

* `risorsa_umana_id`
* `auth_user_id`
* `attivo`

---

## ✅ Regole di dominio

### R1 — Ruolo corretto
Ogni `risorsa_umana` deve riferire un `soggetto_ruolo_id` con tipo ruolo **RISORSA_UMANA**.

### R2 — Coerenza soggetto
`risorse_umane.soggetto_id` deve corrispondere al `soggetto_id` del ruolo associato.

### R3 — Validita temporale
Se `valido_al` e' valorizzato, deve essere >= `valido_dal`.

### R4 — Collegamento a Django (solo gestore)
Il collegamento a `django.auth_user` e' consentito **solo** per risorse appartenenti al **soggetto gestore**.

---

## 🔐 Accesso al software

L’accesso applicativo e' governato dalla risorsa:

* se `attivo = false` **oppure** fuori periodo (`valido_dal/valido_al`), la risorsa **non accede**
* l’utente Django collegato va quindi disattivato (`auth_user.is_active = false`)

### Strategie operative

**A) Sync applicativo (consigliato)**

Un servizio backend legge `risorse_umane` e aggiorna `django.auth_user.is_active`.

**B) Sync DB (opzionale)**

Trigger sulla tabella ponte che aggiorna `django.auth_user.is_active`.

> Nota: toccare direttamente lo schema `django` da trigger DB richiede cautela.

---

## 🔑 Autorizzazioni e gruppi

La gestione **permessi/gruppi** resta in Django:

* `auth_group`
* `auth_permission`
* `auth_user_groups`

Possibili mapping:

* `qualifica_id` -> gruppo Django
* `unita_organizzativa_id` -> gruppo o policy applicativa

---

## 🧭 Distinzione con i contatti

* `anagrafiche.contatti` = **referenti/canali** (email, telefono, pec)
* `anagrafiche.risorse_umane` = **persona reale** con ruolo e validita

I contatti non sostituiscono le risorse umane, ma possono riferirle (se previsto).

---

## ✅ Best practice

* Usa `risorse_umane` solo quando vuoi descrivere **persone interne**.
* Mantieni i referenti esterni su `contatti`.
* Centralizza le autorizzazioni su Django, non su DB.
* Mantieni una policy chiara su `attivo` e periodi di validita.

---

{% include-markdown "signature-core.md" %}
