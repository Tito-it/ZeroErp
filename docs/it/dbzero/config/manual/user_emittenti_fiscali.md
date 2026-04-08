## 📘 Documentazione Concettuale – Tabella `config.user_emittenti_fiscali`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
WIP/refactor:
>
[Refactor operatore ↔ emittente](/dev/work-in-progress/refactor-operatore-emittenti)
>
Tabelle correlate:
>
[anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
Funzioni e trigger:
>
[script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
> [script.fn_check_user_can_create_ba](/dbzero/script/funzioni/fn_check_user_can_create_ba)
> [config.trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete)

---

La tabella **`config.user_emittenti_fiscali`** definisce l'**ambito operativo** di un utente: a quale emittente fiscale appartiene operativamente.

> ⚠️ **Modello attuale (refactor 2026-04-08): 1‑a‑1**.
> Ogni utente può avere **al massimo una** riga in questa tabella. Il vincolo precedente
> `UNIQUE (auth_user_id, emittente_fiscale_id)` è stato sostituito da `UNIQUE (auth_user_id)`.

---

### 🎯 Scopo Principale

* Legare in modo univoco un operatore al proprio emittente fiscale.
* Discriminare gli **admin globali** (utenti senza riga, ruolo `ADMIN`) dagli **admin di emittente** (utenti con 1 riga, ruolo `ADMIN`) e dagli **operatori standard** (utenti con 1 riga, ruolo `OPERATIVO`).
* Fornire il dato per il **filtering queryset** (`EmittenteFiscaleScopeMixin`) e per il **defense‑in‑depth** DB (trigger guard su `billing_account`, fatture, ordini, pagamenti).

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | Utente Django (riferimento logico a `django.auth_user`). UNICO. |
| `emittente_fiscale_id` | Emittente fiscale di appartenenza (FK → `anagrafiche.emittenti_fiscali.id`). **Immutabile** dopo l'inserimento. |

---

### Semantica delle righe

| Righe per l'utente | `ruolo_sistema` | Significato                                                                                                                                                                       |
| ------------------ | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0**              | `ADMIN`         | **Admin globale**: vede tutti gli emittenti, può crearli/cancellarli, può creare admin di emittente e operatori standard per qualunque emittente. Bypass completo dei permessi.   |
| **0**              | `OPERATIVO`     | **Vietato** se esistono emittenti nel sistema. Ammesso solo nello scenario edge "0 emittenti / gestore = emittente".                                                              |
| **1**              | `ADMIN`         | **Admin di emittente**: ha tutti i permessi su quel singolo emittente, può gestire (creare/disattivare) operatori standard di quell'emittente. **Non** può creare altri admin.    |
| **1**              | `OPERATIVO`     | **Operatore di emittente**: opera sull'unico emittente associato. Permessi standard via reparto + override.                                                                       |
| qualunque          | `DISABILITATO`  | Nessun accesso.                                                                                                                                                                   |

---

### Regole di immutabilità (refactor 2026-04-08)

* **Nessuna modifica di `emittente_fiscale_id`** dopo l'inserimento (trigger `trg_user_emittenti_fiscali_a10_lock_emittente_upd` che riusa `script.trgfn_lock_columns`). Errore: `EMITTENTE_NON_MODIFICABILE`.
* **Nessuna eliminazione finché l'utente Django è attivo** (trigger `trg_user_emittenti_fiscali_a10_guard_delete_dlt`). La riga può essere cancellata solo se `django.auth_user.is_active = false` (cessazione utente). Errore: `E_USER_EMITTENTE_DELETE_VIETATO`.
* Override di manutenzione (entrambi i trigger): `SET LOCAL zeroerp.allow_lock_columns_override = 'on'` / `SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on'`.

**Motivazione**: audit trail naturale. Ogni utente = una sola azienda, sempre. Per "trasferire" un dipendente da un emittente A a un emittente B, l'admin **disattiva l'utente** e **crea un nuovo account** legato a B. Vedi [refactor-operatore-emittenti §D3](/dev/work-in-progress/refactor-operatore-emittenti).

---

### Enforcement a due livelli

| Livello | Meccanismo | Dove |
|---------|-----------|------|
| **Django** | `EmittenteFiscaleScopeMixin` filtra il queryset | View DRF |
| **DB** | Trigger guard sulle tabelle operative + funzioni `script.fn_check_user_*` | Tabelle `billing_account`, `fatture`, `ordini`, `pagamenti` |

Il livello DB è un **defense‑in‑depth**: garantisce che nessun bypass applicativo possa inserire dati su emittenti non autorizzati.

---

### Funzioni resolver

| Funzione                                                                                                      | Ritorna                       | Uso                                                                          |
| ------------------------------------------------------------------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------- |
| [`script.fn_resolve_emittente_for_user(auth_user_id)`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) | `emittenti_fiscali.id` o NULL | Restituisce l'emittente di un utente. NULL se admin globale o "0 emittenti". |
| [`script.fn_check_user_can_create_ba(auth_user_id)`](/dbzero/script/funzioni/fn_check_user_can_create_ba)     | `boolean`                     | Pure check usato dal guard `BEFORE INSERT` su `billing_account`.             |

---

> **"`config.user_emittenti_fiscali` è il pilastro dell'ambito multi‑azienda: 1‑a‑1, immutabile, audit‑friendly."**
