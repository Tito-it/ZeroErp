## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_is_active()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired)

---

### 🎯 Scopo Principale

(latest review 10-03-2026)
La funzione **`anagrafiche.fn_sync_auth_user_is_active()`** allinea il campo
`django.auth_user.is_active` allo stato effettivo della risorsa umana
collegata.

La funzione centralizza in un solo punto il calcolo dell'abilitazione
applicativa dell'utente.

---

### Regole applicate

L'utente deve risultare attivo solo se tutte queste condizioni sono vere:

* `anagrafiche.risorse_umane.attivo = true`
* `anagrafiche.risorse_umane_auth_user.attivo = true`
* la data corrente rientra nella finestra `[valido_dal, valido_al]`

Inoltre:

* il parametro `p_risorsa_umana_id` deve essere valorizzato e maggiore di zero;
* se non esiste il collegamento verso `auth_user`, la funzione non fa nulla;
* se lo schema `django` non e' presente, la funzione non fa nulla;
* aggiorna `django.auth_user.is_active` solo se il valore atteso e quello
  corrente sono diversi;
* ritorna `true` solo se ha realmente modificato la riga `auth_user`.

---

### Ruolo nel processo

Questa funzione e' il punto unico di sincronizzazione tra stato HR e stato di
accesso applicativo. I trigger su `risorse_umane` e `risorse_umane_auth_user`
la richiamano per evitare che il backend debba replicare la stessa logica.

---

{% include-markdown "signature-core.md" %}
