## 📘 Documentazione Concettuale – Funzione `vendite.fn_check_fondo_fattura_capiente`

> 👀 **Vedi anche**
>
> **I due chiamanti, che la usano in versi opposti:**
>
> • [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura) — `AND …` : se è falso, **non applica**
> • [vendite.vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere) — `AND NOT …` : se è falso, **la mostra**
>
> **Da dove viene il numero:**
>
> • [vendite.fn_saldo_sorgente_fondo](/dbzero/vendite/funzioni/fn_saldo_sorgente_fondo)
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-10

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**La sorgente regge ancora questo fondo?**

```text
capienza  =  quanto resta da incassare sulla fattura sorgente
importo   =  quanto vale l'atto

vero  ⟺  stesso segno  E  |capienza| ≥ |importo|
```

Un predicato **puro**: prende due numeri già calcolati e non legge niente.

---

### ⚠️ Segno e valore assoluto, non un `>=` nudo

```text
sorgente a credito:   capienza = −80,00     fondo = −80,00
        −80 >= −80  ✅ ma è un caso fortunato
        −40 >= −80  ✅ ❌  direbbe «capiente» con metà del residuo
```

Su una sorgente a credito i numeri sono negativi e il confronto diretto si
comporta al rovescio. È lo stesso errore che, un livello più in là, avrebbe
spento il capo a credito della banda delle soglie: qui non è un caso di bordo,
è **metà del meccanismo**.

---

### ⭐ Perché è una funzione e non due righe di `WHERE`

Fino al 2026-08-15 la regola viveva in **un** posto: il guard di
`fn_applica_fondi_fattura`. Poi è servita anche all'elenco «da decidere», che
mostra il caso `NON_PIU_CAPIENTE` — cioè la stessa regola, negata.

Due copie avrebbero detto, senza nessun errore e senza nessun log, **due cose
diverse**: l'elenco che dichiara inapplicabile un fondo che il giro applica, o
viceversa un fondo scartato a ogni corsa senza che compaia da nessuna parte.

> ℹ️ È la «regola del 2» del progetto: alla seconda occorrenza la regola si
> estrae. Il momento giusto è **quello**, non dopo — perché a quel punto le due
> copie esistono già e la divergenza è solo questione di tempo.

---

### 🔴 Il NULL non è neutro: è il dettaglio più delicato

Con un argomento `NULL` la funzione ritorna **`FALSE`**, non `NULL`. La
differenza sembra pedanteria e non lo è, perché i due chiamanti la usano in versi
opposti:

| Chi | Come | `FALSE` significa |
| --- | --- | --- |
| `fn_applica_fondi_fattura` | `AND fn_check_…` | **non applico** → fail-closed |
| `vw_fondi_fattura_da_decidere` | `AND NOT fn_check_…` | **la mostro** → fail-visible |

Con un ritorno `NULL` il primo si sarebbe comportato allo stesso modo, ma il
secondo avrebbe fatto **sparire la riga dall'elenco**: il caso più anomalo
sarebbe stato l'unico invisibile.

*Chiuso dove si scrive, visibile dove si guarda — con la stessa funzione.*

---

### Regole principali

* `IMMUTABLE` e `LANGUAGE sql`: il planner la **inlinea**, quindi dentro un
  `WHERE` non costa niente.
* Non prende id e non fa `SELECT`. ⭐ La scelta è deliberata: una firma
  `(source_id)` avrebbe dovuto rileggere la riga, trasformando una
  moltiplicazione in due letture e — soprattutto — rendendo la funzione
  `VOLATILE`, cioè non inlinabile.
* `fn_check_*` = predicato puro, nessuna `raise`. Qui la convenzione è letterale:
  la funzione non sa nemmeno di quale fondo si stia parlando.

---

### Esempio d'uso

```sql
-- Questo atto è ancora applicabile?
SELECT vendite.fn_check_fondo_fattura_capiente(
         vendite.fn_saldo_sorgente_fondo(s.fattura_sorgente_id, s.id),
         s.importo)
  FROM vendite.fatture_fondi_fattura_source s
 WHERE s.id = 987;
```

---

{% include-markdown "signature-core.md" %}
