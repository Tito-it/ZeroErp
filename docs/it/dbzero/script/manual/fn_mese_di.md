## 📘 Documentazione Concettuale – Funzione `script.fn_mese_di`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_fine_mese_di](/dbzero/script/funzioni/fn_fine_mese_di) — l'ultimo giorno dello stesso mese
> * [script.fn_giorno_operativo](/dbzero/script/funzioni/fn_giorno_operativo) — il giorno aziendale di un istante, da cui si parte quando il dato è un `timestamptz`
>
> Guide:
>
> * [Linee guida SQL, §11.10](/linee-guida-sql#1110-timestamp-nudo-e-senza-fuso-si-scrive-timestamptz-sempre) — il fuso della sessione e il mese di un giorno

---

### 🎯 Scopo Principale

Il primo giorno del mese di un giorno: il **mese di competenza** di una data, calcolato sul
calendario.

È la sede unica di questo calcolo nel database. Ogni colonna `competenza_mese`, ogni parametro
`p_competenza_mese` normalizzato e ogni proiezione «mese di un documento» lo chiedono qui.

---

### ⭐ Un giorno non passa da un istante

Il mese di un giorno è aritmetica di date: si tolgono i giorni già passati del mese. La funzione
non conosce ore, fusi né la sessione che la chiama, e per questo è `IMMUTABLE`.

La forma che sostituisce, il troncamento al mese di una data, in PostgreSQL non ha una variante
per le date: la data diventa la mezzanotte nel fuso della **sessione**, si tronca lì e torna data.
Il risultato coincide, ma il calcolo di un giorno dipende da un istante, non può stare in un
vincolo o in un indice, e dove il giorno veniva dal fuso aziendale andava scritto con un
`timestamp` senza fuso, da dichiarare a ogni ricreazione della vista.

---

### ⚠️ Lavora su un giorno, non su un istante

L'argomento è una data. Un valore `timestamptz` (l'emissione di un documento, l'inserimento di
una riga) passa **prima** da `script.fn_giorno_operativo`, che dà il giorno nel fuso dell'azienda:
convertirlo direttamente a data lo leggerebbe nel fuso della sessione, e il backend lavora in UTC.

---

### Un giorno assente non ha mese

`NULL` restituisce `NULL`, come il calcolo che sostituisce. Non è un ripiego: un documento senza
data non ha un mese di competenza, e chi lo chiama decide che cosa fare dell'assenza.

---

### ⭐ Gratuita dove la si usa

È una funzione SQL di una sola espressione, senza clausole che la rendano opaca: il planner la
espande nel punto in cui la si chiama. In una vista o in un filtro costa quanto l'espressione
scritta a mano, e il nome dice il significato.

---

### Test

`db/pgtap/script/test-mese-di-un-giorno-v1.sql`: volatilità e `STRICT` dal catalogo, i casi
costruiti (primo e ultimo del mese, 29 febbraio, fine anno), l'uguaglianza col troncamento su ogni
giorno dal 1899 al 2101 sotto due fusi di sessione, e l'espansione nel piano.

---

### Note di migrazione

* 2026-11-15 — nasce col secondo consumatore e oltre: il troncamento al mese era ricopiato in viste
  e funzioni di `vendite`, nel SQL del backend e negli helper pgTAP. Le copie si ritirano con
  brief-db-mese-di-un-giorno, e un cancello statico (`date-trunc`) rifiuta le nuove.

---

{% include-markdown "signature-core.md" %}
