## 📘 Documentazione Concettuale – Funzione `catalogo.fn_uom_operativa_alla_data`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — le mappature che legge
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — la chiama per il fattore
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — la chiama per le regole della quantità
> * [catalogo.fn_distinta_alla_data](/dbzero/catalogo/funzioni/fn_distinta_alla_data) — la gemella della distinta, con la stessa forma

---

### 🎯 Scopo Principale

Restituisce la mappatura di un'unità per un articolo a una data: il fattore verso l'unità
base e le regole della quantità (`qty_step`, `max_decimals`, `forbid_fraction`) della riga
attiva di `catalogo.articoli_uom_operativa` la cui validità contiene quel giorno.

---

### Al più una riga

La mappatura è versionata ma i periodi della stessa unità per lo stesso articolo non si
sovrappongono: la funzione restituisce una riga, o nessuna.

* **Nessuna riga** se l'unità non è mappata a quella data, se la mappatura di quel giorno è
  spenta, o se la data è vuota: la data non si sottintende.
* **La riga base** vale a ogni data, perché non ha date: per l'unità base dell'articolo la
  funzione risponde sempre.

---

### ⭐ Una sede per la lettura della mappatura

La leggono il fattore (`fn_get_uom_factor`) e le regole della quantità sulle righe di vendita
(`trgfn_qta_from_operativa`), tutti e due alla data del documento. Prima ognuno la leggeva per
conto suo, alla data di oggi.

---

### Come legge

`LANGUAGE sql` con corpo `BEGIN ATOMIC`: le tabelle che legge stanno in `pg_depend`.
Restituisce le colonne che servono ai due chiamanti, per nome. `STABLE`, `SECURITY INVOKER`:
la tabella non ha row level security.

---

### Test

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — la mappatura versionata letta a due
  date, attraverso il fattore e le regole della quantità sulle righe di preventivo.

---

### Note di migrazione

* 2026-11-09 — nasce come sede unica della lettura della mappatura, alla data
  (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
