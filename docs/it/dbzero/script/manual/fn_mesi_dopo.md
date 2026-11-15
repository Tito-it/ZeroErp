## 📘 Documentazione Concettuale – Funzione `script.fn_mesi_dopo`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_mesi_del_tratto](/dbzero/script/funzioni/fn_mesi_del_tratto) — i mesi che un tratto di giorni tocca, costruiti su questa
> * [script.fn_fine_mese_di](/dbzero/script/funzioni/fn_fine_mese_di) — l'ultimo giorno del mese, su cui il giorno d'arrivo si taglia
> * [script.fn_mese_di](/dbzero/script/funzioni/fn_mese_di) — il primo giorno del mese di un giorno
> * [script.fn_giorno_operativo](/dbzero/script/funzioni/fn_giorno_operativo) — il giorno aziendale di un istante, da cui si parte quando il dato è un `timestamptz`

---

### 🎯 Scopo Principale

Un giorno spostato di un certo numero di mesi di calendario, in avanti o indietro (un numero
negativo va indietro).

È il passo dei periodi che durano un numero di mesi: l'inizio del periodo successivo di un canone
trimestrale, il mese di partenza di un periodo che contiene una data.

---

### ⭐ Il giorno che non c'è diventa l'ultimo del mese

Se il giorno di partenza non esiste nel mese d'arrivo, il risultato è l'ultimo giorno di quel mese.
Il 31 gennaio più un mese è il 28 febbraio, o il 29 in un anno bisestile, e il 29 febbraio più un
anno è il 28 febbraio. È la stessa regola che PostgreSQL applica a una data più un intervallo di
mesi, scritta una volta sola. Da un primo del mese il giorno non si taglia mai.

---

### Come si calcola

Il mese diventa un numero progressivo (anno per dodici, più il mese), a cui si sommano i mesi; da
lì si ricava il primo del mese d'arrivo, e il giorno si taglia sulla sua fine con
`script.fn_fine_mese_di`. Ci sono solo numeri interi e date. Non ci sono intervalli, che sommati a
una data restituiscono un `timestamp` senza fuso, e non c'è la sessione. Per questo è `IMMUTABLE`.

Vale per gli anni dopo Cristo: un arrivo prima dell'anno 1 fa fallire il calcolo, perché il
calendario non ha un anno zero.

---

### ⚠️ Lavora su un giorno, non su un istante

Come `script.fn_mese_di`: un `timestamptz` passa prima da `script.fn_giorno_operativo`. Un
argomento `NULL` restituisce `NULL`.

---

### ⚠️ Perché non è `STRICT`

Il calcolo è un'espressione sola, che il planner espande nel punto d'uso come `fn_mese_di` e
`fn_fine_mese_di`. Il planner però non espande una funzione `STRICT` il cui corpo non è strict, e
`least()` non lo è. Per questo la funzione non è `STRICT`: il `NULL` lo dà l'espressione stessa,
perché con un argomento `NULL` tutti e due i rami di `least()` sono `NULL`. Da chiamata non espansa
lo stesso calcolo costa circa tre volte tanto.

---

### Test

`db/pgtap/script/test-mesi-dal-calendario-v1.sql`:

* i casi costruiti: il 31 su febbraio e su un mese di 30 giorni, il 29 febbraio più un anno,
  dicembre verso gennaio e ritorno, zero mesi;
* l'uguaglianza con la data più `make_interval(months => n)`, su ogni giorno dal 1899 al 2101 e
  per tredici valori di n;
* sul catalogo vivo, nessuna vista e nessuna funzione somma mesi per conto suo (test 16).

Per i changeSet nuovi lo dice la regola `mesi-intervallo` di `scripts/guardrail_forme_changeset.py`.

---

### Note di migrazione

* 2026-11-15 — nasce al posto di `make_interval(months => n)` sommato a una data in
  `vendite.fn_canone_periodi` (brief-db-mese-di-un-giorno, giro 6).

---

{% include-markdown "signature-core.md" %}
