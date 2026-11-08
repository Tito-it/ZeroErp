## 📘 Documentazione Concettuale – Funzione `dbops.fn_processo_acceso_dichiarato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il default per ambiente e le regole del catalogo
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la scelta a mano
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama, che ne fa la colonna `acceso`
>
> Approfondimento funzioni:
>
> * [dbops.fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori) — la regola, a cui passa i valori
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — chi decide, e rende errori i vuoti di questa
> * [script.fn_ambiente_dichiarato](/dbzero/script/funzioni/fn_ambiente_dichiarato) — l'ambiente, letto senza sollevare

---

### 🎯 Scopo Principale

Lo stato della sveglia di un processo su questa installazione, per chi **descrive**: legge il
catalogo, la scelta a mano e l'ambiente, e chiede la risposta alla regola. Non solleva mai.

---

### ⭐ La lettura di chi descrive, non di chi decide

La funzione risponde vuoto in tre casi, tutti normali per chi mostra uno stato:

* il processo non ha una sveglia (canale `CODA`, o ritiro raggiunto: un ritiro programmato ha la
  sveglia fino al suo giorno);
* il codice non è a catalogo;
* l'ambiente non è dichiarato e né il catalogo né una scelta a mano bastano a decidere.

La leggono il panorama dei processi, che ne fa la colonna `acceso`, il backend per il drawer dei
processi, e il verbo [fn_imposta_accensione_processo](/dbzero/dbops/funzioni/fn_imposta_accensione_processo)
per restituire lo stato dopo il gesto.

Chi invece **decide** se una sveglia deve partire passa da
[maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa), che chiede a
questa funzione e rende i vuoti degli errori: un processo inesistente, un processo senza sveglia,
un ambiente mancante.

La regola non è qui: sta in [fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori),
e questa funzione si limita a passarle i valori del dato.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` — in una produzione costruita, una
  riga accesa scritta prima non accende un processo non accendibile.
* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — con l'ambiente non dichiarato il panorama,
  che la legge, non solleva e mostra `acceso` vuoto dove non si sa.

---

### Note di migrazione

* 2026-10-16 — nasce col default di accensione per ambiente (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}
