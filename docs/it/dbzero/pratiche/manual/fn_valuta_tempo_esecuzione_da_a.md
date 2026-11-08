## 📘 Documentazione Concettuale – Funzione `pratiche.fn_valuta_tempo_esecuzione_da_a`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.formule_tempo](/dbzero/pratiche/tabelle/formule_tempo) — la formula: giorni di esecuzione e soglie
>
> Approfondimento funzioni:
>
> * [pratiche.fn_calcola_tempo_netto_da_a](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a) — i giorni netti fra i due flussi

---

### 🎯 Scopo Principale

`pratiche.fn_valuta_tempo_esecuzione_da_a` è un controllo puro che confronta il tempo netto trascorso fra
due flussi di una pratica con la formula di tempo configurata, e ne ricava lo stato temporale: `OK`,
`WARNING`, `CRITICO` o `SFORATO`.

---

### La formula

La formula si cerca per tipo di prestazione della pratica e per la coppia di template dei due flussi
(da, a), fra le formule attive. Porta i giorni di esecuzione ammessi e le due soglie di avviso.

La funzione restituisce una riga con i giorni netti, i giorni di esecuzione, i giorni rimanenti
(esecuzione meno netti) e lo stato.

---

### Lo stato

* `SFORATO` — non resta nessun giorno.
* `CRITICO` — i giorni rimanenti sono entro la soglia critica.
* `WARNING` — i giorni rimanenti sono entro la soglia di avviso.
* `OK` — altrimenti.

---

### ⚠️ Quando non valuta

La funzione non restituisce nessuna riga, invece di un errore, quando:

* uno dei due flussi non ha template (un flusso manuale);
* non c'è una formula attiva per quel tipo e quella coppia di template;
* i giorni netti non si possono calcolare, perché il flusso di partenza non è ancora finito.

Chi la chiama legge l'assenza di righe come «nessuna valutazione», non come «in tempo».

---

{% include-markdown "signature-core.md" %}
