## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_notify_cambio_reparto`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
>
> **Approfondimento funzioni:**
>
> * [anagrafiche.fn_notify_cambio_reparto](/dbzero/anagrafiche/funzioni/fn_notify_cambio_reparto)

---

### 🎯 Scopo Principale

(latest review 10-03-2026)
La trigger function
**`anagrafiche.trgfn_risorse_umane_notify_cambio_reparto()`** emette una
notifica PostgreSQL quando una risorsa umana cambia
`unita_organizzativa_id`.

La notifica e' pensata per il backend applicativo, che puo' intercettarla via
`LISTEN/NOTIFY` e invalidare cache o permessi derivati dal reparto.

---

### 🔍 Regola applicata

* Trigger **AFTER UPDATE OF unita_organizzativa_id** su
  `anagrafiche.risorse_umane`.
* Chiama `anagrafiche.fn_notify_cambio_reparto(...)` passando:
  * `NEW.id`
  * `OLD.unita_organizzativa_id`
  * `NEW.unita_organizzativa_id`
* Essendo un trigger `AFTER`, il valore di ritorno e' ignorato (`RETURN NULL`).

---

### ✅ Ruolo nel processo

La funzione collega una modifica dati lato DB a una reazione applicativa
asincrona, senza introdurre dipendenze dirette del database dal backend.

Il cambio reparto diventa cosi' un evento esplicito e osservabile.

---

{% include-markdown "signature-core.md" %}
