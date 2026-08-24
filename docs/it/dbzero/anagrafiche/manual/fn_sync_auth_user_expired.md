## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_expired()`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/views/risorse_umane_auth_user)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`anagrafiche.fn_sync_auth_user_expired()`** esegue una
sincronizzazione batch degli utenti Django collegati a bridge auth con
finestra di validità scaduta.

Copre il caso in cui un'identità (o una risorsa umana) diventi non valida
per semplice decorrenza della data, senza che avvenga un `UPDATE` esplicito
che triggeri i trigger reattivi.

---

### Estensione §4.5 multi-face-auth

Con la generalizzazione del modello (§4.5.5 WIP multi-face-auth), la
funzione ora copre **entrambi i modelli**:

* **Ramo legacy** (`risorse_umane`): risorse umane con `valido_al <
  CURRENT_DATE` che hanno un collegamento in `risorse_umane_auth_user`.
* **Ramo nuovo** (`identita_digitali`): qualsiasi identità attiva (tutti i
  ruoli applicativi: operatori, clienti portale, fornitori portale, shop
  customer, api_client) con `valido_al < CURRENT_DATE`.

Le due sorgenti sono combinate via `UNION` e poi filtrate con
`SELECT DISTINCT auth_user_id` per evitare double-sync quando lo stesso
utente è presente in entrambi i modelli durante la transizione.

---

### Regole applicate

* La query interna seleziona solo `auth_user` ancora `is_active = true`
  (gli utenti già disattivati non serve re-sincronizzarli).
* Per ogni `auth_user_id` trovato chiama
  `anagrafiche.fn_sync_auth_user_is_active(auth_user_id)` che applica la
  logica fail-closed (fuori finestra → `false`).
* Incrementa il contatore solo se la funzione ritorna `true` (ovvero se
  `auth_user.is_active` è stato effettivamente modificato).
* In ambienti CI senza schema `django`, la funzione esce subito con `0`.

---

### Output

Ritorna `integer` — numero di utenti effettivamente disattivati.

---

### Uso previsto

* **pgAgent**: job giornaliero schedulato (tipicamente alle prime ore del
  mattino) via `db/changelog/migrations_v2/85_pgagent/`.
* **Management command Django**: `python manage.py sync_auth_user_active`
  per esecuzioni manuali o invocate da pipeline di manutenzione.

---

### Ruolo nel processo

La funzione completa il sistema di propagazione dello stato di login: i
trigger reattivi gestiscono i cambi espliciti, questa funzione gestisce i
cambi temporali impliciti (scadenza overnight). Con l'estensione del ramo
`identita_digitali`, copre ora anche portali clienti/fornitori e shop.

---

{% include-markdown "signature-core.md" %}
