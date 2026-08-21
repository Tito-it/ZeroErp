## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_soggetto_ruolo()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna a un soggetto un **ruolo** (`VT`, `CL`, `FO`…) e ne restituisce l'id.

⚠️ **Va chiamata in un'istruzione separata dalla creazione del soggetto.** Non è una
preferenza di stile: le CTE che scrivono condividono la stessa *snapshot*, e una policy che
risolve il perimetro dal padre non lo troverebbe — negando fail-closed. In `LANGUAGE sql` non
si può separare: serve `plpgsql` con due chiamate e una variabile in mezzo.

⭐ È la ragione per cui questa funzione esiste separata invece di essere un parametro della
precedente: la separazione è **obbligatoria**, e averla come funzione distinta la rende
evidente.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
