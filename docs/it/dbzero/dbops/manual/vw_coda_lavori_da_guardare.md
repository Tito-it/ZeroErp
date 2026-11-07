## 📘 Documentazione Concettuale – Vista `dbops.vw_coda_lavori_da_guardare`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — la coda che la vista guarda
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, che la conta ogni giorno
>
> Approfondimento viste:
>
> * [dbops.vw_fatture_stampa_coda_da_guardare](/dbzero/dbops/views/vw_fatture_stampa_coda_da_guardare) — la gemella sulla coda delle stampe
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta da cui i lavori entrano
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — che cosa vuol dire una vista che deve restare vuota

---

### 🎯 Scopo Principale

I lavori della coda generica che chiedono un occhio: falliti, presi e mai chiusi, o mai presi.
Deve restare vuota.

---

### ⭐ Tre motivi, perché sono tre guasti diversi

| Motivo | Che cosa è successo | Che cosa si fa |
| --- | --- | --- |
| **fallito** | `ERRORE`: il lavoro ha esaurito i tentativi | si legge `ultimo_errore` e si decide |
| **preso e mai chiuso** | `IN_CORSO` preso da oltre un'ora: il drenatore è morto a metà | si rimette in coda |
| **mai preso** | ⛔ `PENDING` eleggibile da oltre un'ora: il drenatore non sta girando | si riaccende il drenatore |

⚠️ Il terzo è il più importante e il meno visibile: un drenatore spento non produce errori, produce
**assenza**. Non c'è niente da leggere, ed è per questo che nessuno se ne accorge.

L'età di un lavoro in attesa si conta dall'istante da cui è eleggibile (`run_after`, o la nascita):
un lavoro differito non è in ritardo prima della sua ora. `da_quanto` si conta dalla presa in
carico, se c'è, altrimenti dallo stesso istante di eleggibilità.

---

### ⛔ Prima il posto dove guardare, poi il lavoro

L'argomento per togliere i processi di dominio da pgAgent è che pgAgent non racconta i suoi
fallimenti: la traccia finisce in una tabella di sistema che nessuno guarda. Ma la coda senza
questa vista non era meglio: spostarci il lavoro avrebbe trasferito il silenzio invece di toglierlo.
Per questo la vista è nata prima dello spostamento.

---

### ⚠️ Le soglie sono una scelta, non una misura

Un'ora per «preso e mai chiuso» e un'ora per «mai preso». Vengono dal fatto che il drenatore gira
di continuo, quindi un'ora di attesa non è lentezza, è un guasto. Una soglia dedotta dai tempi di
oggi si taglierebbe addosso al carico di oggi.

---

### Che cosa resta fuori, e perché

* `ANNULLATO`: qualcuno ha deciso che non si fa.
* le righe **archiviate**: qualcuno le ha già guardate e messe via.

Un presidio che elenca anche ciò che è stato visto smette di essere una lista di cose da fare.
È anche il modo in cui la vista torna vuota: si archivia ciò che si è risolto.

---

### Una persona legge col suo perimetro, il digest conta tutto

La vista è `security_invoker`, come la gemella della coda stampa: chi la interroga legge
`dbops.coda_lavori` coi propri occhi, quindi sotto la sua policy. Un operatore vede i lavori della
sua azienda, il super admin anche quelli di sistema. Il conteggio del digest passa da
`dbops.fn_conta_presidio`, che conta come proprietario e vede tutte le aziende: per questo nel
catalogo dei presidi il perimetro è `DEFINER`, e il digest riporta il numero, non le righe.

⚠️ Finché la row level security della coda non è accesa, chiunque la legga vede ancora tutto.

Un lavoro mai preso può voler dire due cose: il drenatore è fermo, oppure l'azienda del lavoro non
ha l'utente tecnico del drenatore, che lavora un'azienda alla volta.

---

### Test

* `db/pgtap/dbops/test-vw-coda-lavori-da-guardare.sql` — un lavoro in `ERRORE`, uno `IN_CORSO` da
  oltre un'ora e uno `PENDING` da oltre un'ora compaiono col loro motivo; uno appena accodato, uno
  appena preso, uno annullato e uno archiviato no.
* `db/pgtap/rls/test-rls-coda-lavori-perimetro-v1.sql` (test 11) — letta da un operatore, mostra
  solo i lavori del suo perimetro.

---

### Note di migrazione

* 2026-09-05 — nasce, prima della migrazione dei processi di dominio sulla coda
  (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-11-07 — diventa `security_invoker`, perimetro `DEFINER` nel catalogo dei presidi
  (`brief-db-revisione-dbops`, giro 5, `20261107-55`).

---

{% include-markdown "signature-core.md" %}
