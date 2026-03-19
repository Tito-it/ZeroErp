## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_resellers_guard_ruolo_reseller`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
**Approfondimento funzioni:**
>
[script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)

---
### 🎯 Scopo Principale
(latest review 10-03-2026)
La trigger function **`anagrafiche.trgfn_resellers_guard_ruolo_reseller()`**
garantisce che il record in `anagrafiche.resellers` sia sempre collegato a un
`soggetto_ruolo_id` coerente con il ruolo **RESELLER** (`codice_interno = 'RE'`).

La funzione delega il controllo a `script.fn_guard_soggetto_ruolo(...)` e
sostituisce `NEW.soggetto_ruolo_id` con l'ID valido restituito dalla funzione
generica.

---

### Regola applicata

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.resellers`.
* La funzione chiama `script.fn_guard_soggetto_ruolo(...)` con:
  * `p_soggetto_id := NULL`
  * `p_soggetto_ruolo_id := NEW.soggetto_ruolo_id`
  * `p_cd_int_ruolo := 'RE'`
* Il valore ritornato viene assegnato a `NEW.soggetto_ruolo_id`.

---

### Ruolo nel processo

La guard evita che un reseller venga salvato con un ruolo errato o non
allineato al dominio reseller, centralizzando la logica di verifica/creazione
del bridge in `anagrafiche.soggetti_ruoli`.

---

{% include-markdown "signature-core.md" %}
