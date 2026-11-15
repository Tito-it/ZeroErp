## 📘 Documentazione Concettuale – Funzione `script.fn_fine_mese_di`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_mese_di](/dbzero/script/funzioni/fn_mese_di) — il primo giorno dello stesso mese, su cui si appoggia
> * [script.fn_giorno_operativo](/dbzero/script/funzioni/fn_giorno_operativo) — il giorno aziendale di un istante, da cui si parte quando il dato è un `timestamptz`

---

### 🎯 Scopo Principale

L'ultimo giorno del mese di un giorno (il 28, il 29, il 30 o il 31), calcolato sul calendario.

È il confine destro di un mese di competenza: la data di un documento emesso a fine mese, la
scadenza «fine mese», l'ultimo giorno di un periodo di canone.

---

### ⭐ Il giorno prima del mese successivo

L'ultimo giorno di un mese è il giorno prima del primo del mese seguente. Al mese seguente si
arriva dal primo del mese con un salto fisso di 31 giorni, che cade sempre nel mese dopo e mai in
quello dopo ancora, perché nessun mese ha più di 31 giorni né meno di 28. È aritmetica di date
soltanto: niente intervalli, che sommati a una data restituiscono un `timestamp` senza fuso, e
niente sessione. Per questo è `IMMUTABLE`, come `script.fn_mese_di`.

Gli anni bisestili non hanno un ramo a parte: il calendario delle date li conosce già, compresi
quelli di secolo (il 1900 e il 2100 non lo sono, il 2000 sì).

---

### ⚠️ Lavora su un giorno, non su un istante

Come `script.fn_mese_di`: un `timestamptz` passa prima da `script.fn_giorno_operativo`. `NULL`
restituisce `NULL`. Il planner la espande nel punto d'uso, insieme a `script.fn_mese_di`.

---

### Test

`db/pgtap/script/test-mese-di-un-giorno-v1.sql`: i casi costruiti (mesi di 28, 29, 30 e 31 giorni,
i febbrai di secolo, dicembre), l'uguaglianza col calcolo che sostituisce su ogni giorno dal 1899
al 2101 sotto due fusi di sessione, e l'espansione nel piano.

---

### Note di migrazione

* 2026-11-15 — nasce con `script.fn_mese_di` al posto del troncamento al mese più un mese meno un
  giorno, ricopiato nelle funzioni di `vendite` e negli helper pgTAP (brief-db-mese-di-un-giorno).

---

{% include-markdown "signature-core.md" %}
