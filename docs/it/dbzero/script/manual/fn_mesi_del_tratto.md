## 📘 Documentazione Concettuale – Funzione `script.fn_mesi_del_tratto`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_mesi_dopo](/dbzero/script/funzioni/fn_mesi_dopo) — un giorno n mesi dopo, il passo da un mese al seguente
> * [script.fn_mese_di](/dbzero/script/funzioni/fn_mese_di) e [script.fn_fine_mese_di](/dbzero/script/funzioni/fn_fine_mese_di) — il primo e l'ultimo giorno di ogni riga
> * [vendite.fn_canone_periodi](/dbzero/vendite/funzioni/fn_canone_periodi) — la conta dei giorni coperti di un periodo di canone, che la usa

---

### 🎯 Scopo Principale

I mesi di calendario che un tratto di giorni tocca, dal mese del primo giorno a quello
dell'ultimo, compresi: una riga per mese, in ordine, con il primo giorno (`mese`) e l'ultimo
(`fine_mese`).

Serve a chi divide un tratto per mese, per esempio la frazione di un canone, che conta mese per
mese i giorni coperti.

---

### ⭐ Il mese intero, non il pezzo coperto

Gli estremi del tratto scelgono **quali** mesi, ma non li tagliano: dal 15 gennaio al 10 marzo
escono gennaio, febbraio e marzo interi. Chi vuole i giorni coperti li taglia lui con `greatest` e
`least` sugli estremi del tratto.

Se l'ultimo giorno cade in un mese prima di quello del primo, non c'è nessuna riga. Se manca un
estremo (`NULL`), non c'è nessuna riga. Questo lo dà la serie vuota, non `STRICT`: il planner non
espande mai una funzione che restituisce righe se è `STRICT`, e questa la espande nel punto d'uso.

---

### Perché non `generate_series` sulle date

`generate_series(<date>, <date>, interval '1 month')` restituisce gli stessi mesi, ma
`generate_series` non ha una variante per le date: PostgreSQL usa quella su `timestamptz`. Ogni
mese diventa così un istante, la mezzanotte nel fuso della sessione, riportato a data con un cast.
Il risultato coincide, ma il calendario passa da un istante.

Qui la serie è di numeri interi (zero, uno, due… i mesi fra i due estremi), e ogni mese si ricava
con `script.fn_mesi_dopo`. Ci sono solo numeri interi e date, quindi la funzione è `IMMUTABLE`.

---

### Test

`db/pgtap/script/test-mesi-dal-calendario-v1.sql`:

* i casi costruiti: tre mesi, il cambio d'anno con il febbraio bisestile, un giorno solo, gli
  estremi `NULL` e la fine in un mese prima;
* l'uguaglianza con la serie che sostituisce, su circa 14.000 tratti sotto due fusi di sessione;
* sul catalogo vivo, nessuna vista e nessuna funzione conta i mesi per conto suo (test 16).

---

### Note di migrazione

* 2026-11-15 — nasce al posto di `generate_series(<date>, <date>, interval '1 month')` in
  `vendite.fn_canone_periodi` (brief-db-mese-di-un-giorno, giro 6).

---

{% include-markdown "signature-core.md" %}
