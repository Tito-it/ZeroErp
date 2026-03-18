## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_expired()`

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
La funzione **`anagrafiche.fn_sync_auth_user_expired()`** esegue una
sincronizzazione batch degli utenti Django collegati a risorse umane con
finestra di validita' scaduta.

Serve a coprire il caso in cui una risorsa diventi non valida per semplice
decorrenza della data, senza che avvenga un `UPDATE` esplicito sulla tabella.

---

### Regole applicate

* Cerca le righe di `anagrafiche.risorse_umane` con `valido_al < CURRENT_DATE`.
* Considera solo le risorse che hanno un collegamento in
  `anagrafiche.risorse_umane_auth_user`.
* Considera solo gli `auth_user` ancora attivi.
* Per ogni risorsa trovata chiama
  `anagrafiche.fn_sync_auth_user_is_active(risorsa_umana_id)`.
* Ritorna il numero di utenti effettivamente aggiornati.
* In ambienti senza schema `django`, non esegue nulla e ritorna `0`.

---

### Ruolo nel processo

La funzione e' pensata come job periodico di riallineamento. Non sostituisce i
trigger reattivi, ma li completa per il caso di scadenza "overnight" della
validita' temporale della risorsa umana.

---

{% include-markdown "signature-core.md" %}
