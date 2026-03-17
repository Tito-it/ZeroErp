## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_fornitori_guard_ruolo_fornitore`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
**Approfondimento funzioni:**
>
[script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)

---

### 🎯 Scopo Principale

(latest review 12-03-2026)
La trigger function **`anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()`**
assicura che ogni record di `anagrafiche.fornitori` punti a un
`soggetto_ruolo_id` coerente con il ruolo **fornitore**
(`codice_interno = 'FO'`).

La verifica e l'eventuale riallineamento dell'identificativo vengono delegati a
`script.fn_guard_soggetto_ruolo(...)`.

---

### Regola applicata

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.fornitori`.
* La funzione richiama `script.fn_guard_soggetto_ruolo(...)` con:
  * `p_soggetto_id := NULL`
  * `p_soggetto_ruolo_id := NEW.soggetto_ruolo_id`
  * `p_cd_int_ruolo := 'FO'`
* Il valore ritornato viene assegnato a `NEW.soggetto_ruolo_id`.

---

### Ruolo nel processo

La guard evita il salvataggio di fornitori agganciati a ruoli non coerenti e
centralizza la logica di validazione del bridge anagrafico nello strato comune.

Questo mantiene il dominio `fornitori` allineato alla semantica dei ruoli
anagrafici senza duplicare controlli nella tabella applicativa.

---

{% include-markdown "signature-core.md" %}
