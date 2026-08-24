## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_notify_cambio_reparto()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/views/risorse_umane_auth_user)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
>
**Approfondimento funzioni:**
>
[anagrafiche.trgfn_risorse_umane_notify_cambio_reparto](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_notify_cambio_reparto)

---
### 🎯 Scopo Principale
(latest review 10-03-2026)
La funzione **`anagrafiche.fn_notify_cambio_reparto()`** emette una notifica
PostgreSQL sul canale `cambio_reparto` quando una risorsa umana viene spostata
da un'unita' organizzativa a un'altra.

La funzione non aggiorna dati di business: pubblica un evento tecnico
utilizzabile dal backend per invalidare cache, permessi o contesti derivati dal
reparto.

---

### Regole applicate

* Il parametro `p_risorsa_umana_id` deve essere valorizzato e maggiore di zero.
* Recupera l'eventuale `auth_user_id` collegato alla risorsa umana.
* Costruisce un payload JSON con:
  * `risorsa_umana_id`
  * `old_uo_id`
  * `new_uo_id`
  * `auth_user_id`
* Emette `pg_notify('cambio_reparto', payload)`.

---

### Ruolo nel processo

La funzione rende osservabile a livello infrastrutturale il cambio reparto di
una risorsa umana. Viene richiamata dal trigger su `anagrafiche.risorse_umane`
per trasformare una modifica tabellare in un evento asincrono consumabile dal
backend.

---

{% include-markdown "signature-core.md" %}
