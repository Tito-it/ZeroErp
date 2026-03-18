## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
>
**Approfondimento funzioni:**
>
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale
(latest review 10-03-2026)
La trigger function
**`anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()`**
impedisce di collegare un account Django (`auth_user`) a una risorsa umana che
non corrisponde a una **persona fisica pura**.

La guard richiede:

* **codice fiscale presente**
* **partita IVA assente**

---

### Regole applicate

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.risorse_umane_auth_user`.
* Risale dalla `risorsa_umana` al `soggetto` associato.
* Se il soggetto ha `partita_iva` valorizzata:
  * blocca l'operazione con errore `E_AUTH_USER_SOGGETTO_CON_PIVA`.
* Se il soggetto non ha `codice_fiscale`:
  * blocca l'operazione con errore `E_AUTH_USER_SOGGETTO_SENZA_CF`.

---

### Ruolo nel processo

La funzione separa nettamente:

* l'**appartenenza organizzativa** della risorsa umana
* dalla mera esistenza del soggetto anagrafico

e garantisce che il bridge verso `auth_user` sia riservato a soggetti
effettivamente utilizzabili come persone fisiche interne al sistema.

La verifica dell'ambito emittente non avviene qui, ma nel flusso applicativo
di login/autorizzazione.

---

{% include-markdown "signature-core.md" %}
