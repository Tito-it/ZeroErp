## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_sync_auth_user_active`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)

---

### 🎯 Scopo Principale

(latest review 10-03-2026)
La trigger function
**`anagrafiche.trgfn_risorse_umane_sync_auth_user_active()`** sincronizza
`django.auth_user.is_active` quando cambiano gli attributi di stato della
tabella `anagrafiche.risorse_umane`.

La sincronizzazione dipende da:

* `attivo`
* `valido_dal`
* `valido_al`

---

### Regola applicata

* Trigger **AFTER UPDATE OF attivo, valido_dal, valido_al** su
  `anagrafiche.risorse_umane`.
* Esegue la sincronizzazione solo se esiste un collegamento in
  `anagrafiche.risorse_umane_auth_user`.
* Se il bridge esiste, chiama
  `anagrafiche.fn_sync_auth_user_is_active(NEW.id)`.
* Essendo un trigger `AFTER`, il valore di ritorno e' ignorato (`RETURN NULL`).

---

### Ruolo nel processo

La funzione fa si' che la validita' temporale e lo stato operativo della
risorsa umana si riflettano automaticamente sull'accesso applicativo
dell'utente collegato, senza demandare al backend il ricalcolo a ogni update.

---

{% include-markdown "signature-core.md" %}
