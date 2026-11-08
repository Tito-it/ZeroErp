## 📘 Documentazione Concettuale – Funzione `dbops.fn_accensione_a_mano_ammessa_su_valori`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — `accendibile_in_produzione`, il valore che il divieto legge
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la scelta a mano che il divieto giudica
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_processi_accensione_guard](/dbzero/dbops/funzioni/trgfn_processi_accensione_guard) — rifiuta la scelta che il divieto non ammette
> * [dbops.fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori) — ignora la riga che il divieto non ammette

---

### 🎯 Scopo Principale

Il divieto di accendere a mano, in un'installazione di produzione, un processo che il catalogo
dichiara non accendibile in produzione, puro sui valori. È l'unico posto dove il divieto è scritto.

---

### La regola, in ordine

| Caso | Risposta |
| --- | --- |
| la scelta non accende (spegne, o torna al default) | ammessa |
| il processo è accendibile in produzione, o non ha una sveglia (valore vuoto) | ammessa |
| l'ambiente è `SVILUPPO` | ammessa |
| l'ambiente è `PRODUZIONE` | **non** ammessa |
| l'ambiente non è dichiarato | vuoto: non decidibile |

L'ordine dei rami è la regola: il divieto riguarda solo l'accensione di un non accendibile, e solo
in produzione.

---

### ⭐ Tre lettori, una regola

* il guard della scelta a mano rifiuta la scelta non ammessa, e la risposta vuota la trasforma in
  `E_CONFIG_MANCANTE`;
* la regola dello stato effettivo ignora una riga accesa che il divieto non ammette, e vale il
  default;
* il backend la chiede per sapere se mostrare l'interruttore «accendi» nel drawer.

È pura sui valori, e non legge l'ambiente da sé, perché l'ambiente di un'installazione non cambia e
la CI è `SVILUPPO`: il ramo `PRODUZIONE` si prova passando il valore. Non è `STRICT`: i valori
vuoti sono casi normali, e una funzione `STRICT` risponderebbe vuoto anche dove la regola sa
rispondere.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-v1.sql` — la forma (immutabile, `LANGUAGE sql`, senza
  `STRICT`) e ogni ramo sui valori: spegnere e tornare al default sempre ammessi, un accendibile o
  un processo senza sveglia ammessi, un non accendibile ammesso in sviluppo, rifiutato in
  produzione, non decidibile senza ambiente.

---

### Note di migrazione

* 2026-10-18 — nasce col divieto di accensione in produzione (`brief-db-processi-accensione-per-ambiente`,
  R-BE-5). Prima la stessa protezione stava solo in un consenso nel `.env` di una macchina.

---

{% include-markdown "signature-core.md" %}
