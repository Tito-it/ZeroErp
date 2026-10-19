## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_ruolo_di_altro_soggetto()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto) — la gemella per l'istanza
> [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/manual/trgfn_contatti_guard_contesto_soggetto) — il guard dei contatti

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-15 del backend, decisioni D-17a e D-17b di Tid,
`brief-db-processi-accensione-per-ambiente` §6.17)

**Risponde alla domanda «questo ruolo è di un altro soggetto?».**

È la gemella di
[`fn_istanza_di_altro_soggetto`](/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto) e
funziona allo stesso modo: `NULL` se il ruolo è del soggetto dato (o se non c'è niente da
confrontare), altrimenti il soggetto del ruolo. Il rifiuto lo dà chi la chiama.

---

### Chi la usa

* `anagrafiche.trgfn_contatti_guard_contesto_soggetto` (un contatto sta su un ruolo del suo soggetto);
* `pratiche.trgfn_pratiche_guard_contesto` (regola 3).

---

### Test

`db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (test 2).

---

{% include-markdown "signature-core.md" %}
