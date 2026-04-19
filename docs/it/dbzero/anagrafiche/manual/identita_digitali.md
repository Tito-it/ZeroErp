## 📘 Documentazione Concettuale – Tabella `anagrafiche.identita_digitali`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> [Risorse umane e accessi](/guide/risorse-umane-e-accessi)
>
Tabelle correlate:
>
[anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user) (bridge storico, mantenuto fino al cutover)
> [django.auth_user](/dbzero/django/auth_user)

---
### 🎯 Scopo Principale
(latest revision 19-04-2026)

La tabella **`anagrafiche.identita_digitali`** è il **bridge generico** tra un
`soggetti_ruoli` e l'utente software Django (`django.auth_user`). Generalizza
il ruolo di `risorse_umane_auth_user` (oggi limitato ai soli dipendenti interni)
estendendolo a:

* **Operatori interni** (ruolo applicativo `OPERATORE` – equivalente al bridge storico)
* **Clienti portale B2B** (`CLIENTE_PORTALE`)
* **Fornitori portale** (`FORNITORE_PORTALE`)
* **Clienti shop self-service** (`SHOP_CUSTOMER`)
* **Sistemi terzi integrati** (`API_CLIENT`)
* **Identità disattivate** (`DISABILITATO`)

Ogni record rappresenta **una veste** con cui un soggetto si logga nel sistema.
Un soggetto può avere più identità nel tempo, ma una sola attiva.

---

### Collegamenti principali

* `soggetto_ruolo_id` → `anagrafiche.soggetti_ruoli(id)` – ruolo del soggetto che si logga
* `auth_user_id` → `django.auth_user(id)` – utente Django associato (1:1)

---

### Regole di dominio

* **Un solo auth_user per identità** (`UNIQUE auth_user_id`). Un utente Django
  rappresenta un'identità in uno specifico contesto, non una persona fisica.
* **Una sola identità attiva per soggetto_ruolo**: indice parziale
  `uq_identita_digitali_soggetto_ruolo_attivo` su `(soggetto_ruolo_id) WHERE attivo = true`.
  Ammesse identità storicizzate multiple (cessazione e riassunzione).
* **Finestra temporale**: `valido_dal` obbligatorio (default oggi), `valido_al`
  opzionale. CHECK `valido_al >= valido_dal` se entrambi valorizzati.
* **Coerenza ruolo_applicativo ↔ soggetto_ruolo** garantita dal guard
  [trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_coerenza):
  * `OPERATORE` → soggetto_ruolo con tipo `RIS_UMANA` + soggetto persona fisica pura
    (CF obbligatorio, P.IVA vietata)
  * `CLIENTE_PORTALE` / `SHOP_CUSTOMER` → tipo `CL` (cliente)
  * `FORNITORE_PORTALE` → tipo `FO` (fornitore)
  * `API_CLIENT` / `DISABILITATO` → nessun vincolo specifico

---

### Campi di gestione autenticazione

| Campo | Default | Scopo |
|-------|---------|-------|
| `attivo` | `true` | Soft flag. Se `false`, `auth_user.is_active` viene sincronizzato a `false` (gestione tramite `fn_sync_auth_user_is_active`). |
| `valido_dal` | `CURRENT_DATE` | Inizio validità. |
| `valido_al` | NULL | Fine validità (NULL = aperto). Scaduto → identità non utilizzabile. |
| `deve_cambiare_password` | `false` | Se `true`, il middleware Django forza il cambio password al prossimo login. |
| `invito_inviato_at` | NULL | Timestamp dell'ultimo invito di attivazione inviato (token monouso `INVITO_PORTALE`). |
| `tentativi_falliti` | `0` | Contatore tentativi login KO consecutivi. Reset a 0 al login riuscito o allo scadere del blocco (§4.6.A.1). |
| `bloccato_fino_a` | NULL | Timestamp fino al quale l'identità è bloccata per troppi falliti. `fn_check_blocco_login` effettua auto-unlock quando `bloccato_fino_a < now()` (§4.6.A.1). |
| `totp_obbligatorio` | `false` | Flag MFA: se `true`, il login richiede TOTP. Generalizzato cross-ruolo (§4.6.A.1). |
| `storicizza` | `true` | Flag opt-out per lo snapshot storico automatico (`trgfn_storico_generic`). |

---

### Super admin via binding profilo

A partire da §4.6.A-B WIP multi-face-auth (decisione 2026-04-19) il
privilegio di **bypass totale dei permessi** (equivalente al vecchio
`risorse_umane_auth_user.ruolo_sistema = 'ADMIN'`) non è più una colonna
speciale ma un **binding** tra l'identità e un profilo con
`tipo = 'SUPER_ADMIN'` (seed id `9100`).

* Il check viene fatto da [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin).
* Il binding è gestito via [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings).
* Durante la transizione, il trigger-ponte
  [trgfn_risorse_umane_auth_user_sync_identita](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_auth_user_sync_identita)
  crea/rimuove automaticamente il binding in base al valore di
  `ruolo_sistema` sul bridge legacy.
* La vista di compatibilità
  [vw_risorse_umane_auth_user](/dbzero/anagrafiche/viste/vw_risorse_umane_auth_user)
  ricostruisce dinamicamente la stringa `ruolo_sistema` dal nuovo modello.

---

### Relazione con la tabella storica `risorse_umane_auth_user`

Durante la migrazione del modello multi-face auth i due bridge convivono:

* `risorse_umane_auth_user` resta il bridge **per gli operatori interni**,
  con la logica storica (guard PF pura) e i trigger sync esistenti.
* `identita_digitali` copre **tutti i nuovi ruoli applicativi**.

Al cutover finale (`§4.6` del WIP multi-face-auth), `risorse_umane_auth_user`
diventa una vista letta costruita su `identita_digitali WHERE ruolo_applicativo = 'OPERATORE'`
per compatibilità con il codice legacy; la sorgente dati unica diventa
`identita_digitali`.

---

### FK condizionale verso Django

La FK `fk_identita_digitali_auth_user` viene creata **solo se lo schema `django`
e la tabella `auth_user` esistono**. In ambienti CI senza Django (test pgTAP
puri) il vincolo non viene installato, permettendo alle migration di applicarsi
comunque.

---

### Note operative

* La presenza del bridge è **opzionale**: non tutti i `soggetti_ruoli` devono
  avere un accesso al software (es. clienti che non usano il portale).
* L'attivazione di una nuova identità triggera la sincronizzazione di
  `auth_user.is_active` tramite automation (trigger `sync_auth_user_active`).
* I trigger framework (audit, tx_id, storico) sono applicati via automation
  sulla tabella; non richiedono intervento manuale.

---

{% include-markdown "signature-core.md" %}
