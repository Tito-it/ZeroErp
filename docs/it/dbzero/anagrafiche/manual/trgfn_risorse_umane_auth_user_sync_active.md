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

(latest review 10-03-2026)
La trigger function
**`anagrafiche.trgfn_risorse_umane_auth_user_sync_active()`** sincronizza lo
stato `django.auth_user.is_active` quando cambia il **bridge**
`anagrafiche.risorse_umane_auth_user`.

La funzione interviene sia alla creazione del collegamento sia quando cambia il
flag `attivo` del bridge.

---

### Regola applicata

* Trigger **AFTER INSERT** e **AFTER UPDATE OF attivo** su
  `anagrafiche.risorse_umane_auth_user`.
* Chiama `anagrafiche.fn_sync_auth_user_is_active(NEW.risorsa_umana_id)`.
* Essendo un trigger `AFTER`, il valore di ritorno e' ignorato (`RETURN NULL`).

---

### Ruolo nel processo

La funzione mantiene allineato l'utente Django con lo stato operativo del
bridge risorsa→auth_user, evitando che la gestione dell'attivazione resti
distribuita tra backend e database.

---

{% include-markdown "signature-core.md" %}
