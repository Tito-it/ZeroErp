## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_auth_user_sync_active`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)
La trigger function
**`anagrafiche.trgfn_risorse_umane_auth_user_sync_active()`** sincronizza lo
stato `django.auth_user.is_active` quando cambia il **bridge**
`anagrafiche.risorse_umane_auth_user`.

La funzione interviene sia alla creazione del collegamento sia quando cambia il
flag `attivo` del bridge.

---

### Regole applicate

* Trigger **AFTER INSERT** e **AFTER UPDATE OF attivo** su
  `anagrafiche.risorse_umane_auth_user`, fase `z90`.
* Chiama `anagrafiche.fn_sync_auth_user_is_active(NEW.auth_user_id)`.
* Essendo un trigger `AFTER`, il valore di ritorno è ignorato (`RETURN NULL`).

---

### Storico del refactor

**2026-04-18 (§4.5 F2 WIP multi-face-auth)**: cambiato il parametro passato
alla funzione sync da `NEW.risorsa_umana_id` a `NEW.auth_user_id`, coerente
con la nuova firma della funzione
[`fn_sync_auth_user_is_active(p_auth_user_id integer)`](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active).
Il trigger installato sulla tabella non cambia (stesso nome, stessa fase,
stessi eventi): cambia solo il body della trigger function.

---

### Ruolo nel processo

La funzione mantiene allineato l'utente Django con lo stato operativo del
bridge, evitando che la gestione dell'attivazione resti distribuita tra
backend e database. È uno dei 3 trigger reattivi che mantengono
`auth_user.is_active` coerente con i bridge:

* Questo trigger: reagisce ai cambi del bridge legacy operatori.
* `trgfn_risorse_umane_sync_auth_user_active`: reagisce ai cambi della
  risorsa umana parent.
* `trgfn_identita_digitali_sync_auth_user_active` (§4.5 F4): reagisce
  ai cambi del nuovo bridge generico (tutti i ruoli applicativi).

---

{% include-markdown "signature-core.md" %}
