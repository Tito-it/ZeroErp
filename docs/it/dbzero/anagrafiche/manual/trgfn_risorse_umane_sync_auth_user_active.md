## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_sync_auth_user_active`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/views/risorse_umane_auth_user)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)
La trigger function
**`anagrafiche.trgfn_risorse_umane_sync_auth_user_active()`** sincronizza
`django.auth_user.is_active` quando cambiano gli attributi di stato della
tabella `anagrafiche.risorse_umane`.

La sincronizzazione dipende da:

* `attivo`
* `valido_dal`
* `valido_al`

---

### Regole applicate

* Trigger **AFTER UPDATE OF attivo, valido_dal, valido_al** su
  `anagrafiche.risorse_umane`.
* Risolve l'`auth_user_id` dal bridge `risorse_umane_auth_user` tramite
  `SELECT rau.auth_user_id ... WHERE rau.risorsa_umana_id = NEW.id LIMIT 1`.
* Se `FOUND`, chiama
  `anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id)`.
* Se la risorsa non ha un collegamento auth_user, salta silenziosamente
  (niente da sincronizzare).
* Essendo un trigger `AFTER`, il valore di ritorno è ignorato (`RETURN NULL`).

---

### Storico del refactor

**2026-04-18 (§4.5 F2 WIP multi-face-auth)**: la funzione ora risolve
esplicitamente l'`auth_user_id` dal bridge prima di chiamare la funzione
sync, coerente con la nuova firma di
[`fn_sync_auth_user_is_active(p_auth_user_id integer)`](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active).

Prima del refactor la funzione passava direttamente `NEW.id`
(`risorsa_umana.id`) sfruttando il fatto che la vecchia firma accettava
`p_risorsa_umana_id`. Con la nuova firma serve l'`auth_user_id`, che va
risolto tramite il bridge RUA.

Ottimizzazione: `SELECT INTO` + `FOUND` in una sola query, invece del
pattern precedente `IF EXISTS(...) THEN PERFORM fn_sync(NEW.id);` che
faceva due query.

---

### Ruolo nel processo

La funzione fa sì che la validità temporale e lo stato operativo della
risorsa umana si riflettano automaticamente sull'accesso applicativo
dell'utente collegato, senza demandare al backend il ricalcolo a ogni
UPDATE. È uno dei 3 trigger reattivi che mantengono allineato
`auth_user.is_active` con i bridge auth.

---

{% include-markdown "signature-core.md" %}
