## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_automazione_guard_utility_tipo_ruolo`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il catalogo con cui confronta lo schema
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_guard_utility](/dbzero/dbops/funzioni/fn_run_automations_guard_utility) — il runner che monta il guard sulle righe del catalogo
> * [dbops.fn_apply_automazione_guard_utility_tipo_ruolo](/dbzero/dbops/funzioni/fn_apply_automazione_guard_utility_tipo_ruolo) — la porta storica che la segue nel primo giro di `ci_apply`
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — l'ambito degli schemi da guardare
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — le esclusioni per tabella dell'ambito
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione GUARD utility/tipo ruolo fra le altre

---

### 🎯 Scopo Principale

Una diagnosi: cerca nello schema le tabelle che qualificano per il guard **utility → tipo ruolo**
e che non sono nel catalogo `dbops.automazione_guard_utility_tipo_ruolo`, e le elenca in un
`NOTICE`. ⛔ Nonostante il nome, **non scrive** nel catalogo: il catalogo è un mirror del CSV, e
chi legge la diagnosi decide se aggiungere la riga al CSV.

La chiama il primo giro della passata `ci_apply` del rilascio, prima della porta storica del guard.

---

### Quando una tabella qualifica

Una tabella ordinaria degli schemi dell'ambito (`p_schemas`, o l'ambito risolto se è vuoto), lo
schema `storico` escluso, che ha la colonna `utility_id` e una colonna del soggetto-ruolo. Cerca
prima una colonna con una FK verso `anagrafiche.soggetti_ruoli`, qualunque nome abbia; in
mancanza, una colonna che si chiami `soggetto_ruolo_id` o `<prefisso>_soggetto_ruolo_id`. Fra più
candidate sceglie la prima in ordine alfabetico.

Nessun filtro sul prefisso: il guard è generico, e il runner accetta la colonna che la riga del
registro dichiara.

---

### ⭐ Perché non scrive più

Quando scriveva, inseriva solo le righe mancanti e non correggeva mai una riga già scritta: il
catalogo raccontava lo schema del giorno in cui l'aveva visto, e mentre lo schema cambiava restava
fermo. Rilevare dallo schema resta utile; decidere che una tabella va protetta è una scelta
esplicita, che passa dal CSV, come le decisioni di `dbops.fk_index_policy`.

⚠️ Il limite della forma: un `NOTICE` nell'output della passata `ci_apply` si legge solo se lo si
cerca. Una tabella nuova che qualifica non ferma niente, perché non è un guasto ma una decisione
da prendere.

---

### Codici errore

La funzione non solleva codici suoi.

---

### Test

* `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql` — dopo la chiamata il contenuto
  del catalogo è identico a prima, riga per riga: la funzione non scrive.

---

### Note di migrazione

* 2026-02-16 — nasce come popolamento del catalogo, con un inserimento che saltava le righe già
  presenti.
* 2026-08-18 — smette di scrivere e diventa una diagnosi: il catalogo passa al CSV
  (`brief-db-automazione-guard-utility-righe-sfuggite`).
* 2026-11-08 — esce il filtro sul nome della colonna: qualifica anche `soggetto_ruolo_id` senza
  prefisso, e la FK verso `anagrafiche.soggetti_ruoli` vale qualunque nome abbia la colonna
  (`20261110-03`, `brief-db-revisione-dbops`, giro 10c).

---

{% include-markdown "signature-core.md" %}
