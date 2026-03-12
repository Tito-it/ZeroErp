## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
> **Approfondimento funzioni:**
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)

---

### 🎯 Scopo Principale

(latest review 12-03-2026)
La trigger function **`anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis()`**
garantisce che ogni record in `anagrafiche.emittenti_fiscali` sia collegato a un
`soggetto_ruolo_id` valido e coerente con il ruolo di **emittente fiscale**
(`codice_interno = 'EF'`).

La funzione demanda il controllo a `script.fn_guard_soggetto_ruolo(...)` e
riscrive `NEW.soggetto_ruolo_id` con l'identificativo canonico restituito dalla
guard centrale.

---

### 🔍 Regola applicata

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.emittenti_fiscali`.
* La funzione invoca `script.fn_guard_soggetto_ruolo(...)` con:
  * `p_soggetto_id := NULL`
  * `p_soggetto_ruolo_id := NEW.soggetto_ruolo_id`
  * `p_cd_int_ruolo := 'EF'`
* Il valore restituito sostituisce `NEW.soggetto_ruolo_id` prima del salvataggio.

---

### ✅ Ruolo nel processo

Questa guard impedisce di associare un emittente fiscale a un ruolo anagrafico
errato e mantiene centralizzata la logica di validazione del legame
`soggetto -> ruolo` nello strato `script`.

In questo modo `anagrafiche.emittenti_fiscali` conserva solo riferimenti
semanticamente corretti verso `anagrafiche.soggetti_ruoli`.

---

{% include-markdown "signature-core.md" %}
