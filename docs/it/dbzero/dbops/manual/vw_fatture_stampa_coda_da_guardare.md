## 📘 Documentazione Concettuale – Vista `dbops.vw_fatture_stampa_coda_da_guardare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda delle stampe che la vista guarda
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, che la conta ogni giorno
>
> Approfondimento viste:
>
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — la gemella sulla coda generica
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — conta la vista da proprietario per il digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — che cosa vuol dire una vista che deve restare vuota
> * [Documenti e stampe](/guide/documenti-e-stampe) — la coda delle stampe e il suo drenatore

---

### 🎯 Scopo Principale

Le stampe in coda che chiedono un occhio: fallite, prese e mai chiuse, o mai prese. Deve restare
vuota. È la gemella di `dbops.vw_coda_lavori_da_guardare` per `vendite.fatture_stampa_coda`.

Le due code sono simmetriche per decisione — stessa forma, stessa bandiera `archiviato`, un pgTAP
che le confronta — ma il presidio ce l'aveva una sola: se il drenatore delle stampe si fermava, le
fatture restavano in coda e il digest non diceva niente.

---

### ⭐ Tre motivi, perché sono tre guasti diversi

| Motivo | Che cosa è successo | Che cosa si fa |
| --- | --- | --- |
| **fallito** | `ERRORE`: la stampa ha esaurito i tentativi | si legge `ultimo_errore` e si decide |
| **preso e mai chiuso** | `IN_CORSO` da oltre un'ora: il drenatore è morto a metà, e il reaper non è passato | si riaccende il drenatore |
| **mai preso** | ⛔ `PENDING` da oltre un'ora: il drenatore delle stampe non sta girando | si riaccende il drenatore |

⚠️ Il secondo caso, con il drenatore vivo, non succede: il suo reaper riporta una riga presa da
troppo tempo a `PENDING` prima dell'ora. Se compare, è morto anche il reaper, cioè il drenatore
intero.

---

### ⭐ `data_update` è l'ultima transizione di stato

La coda delle stampe non ha `claimed_at`, e non serve: il trigger di audit porta `data_update` a
ora a **ogni** scrittura, e sulle righe vive l'unica scrittura del drenatore è una transizione di
stato (presa, esito, reaper). L'archiviazione vale solo sugli stati finali.

Quindi `data_update` dice da quando la riga è nello stato in cui si trova: per una riga tornata
`PENDING` misura da quando è tornata, non da quando è nata. Il reaper del drenatore la legge allo
stesso modo: il presidio e il recupero guardano la stessa colonna.

⚠️ Non è un vincolo del database. Una scrittura non di stato su una riga viva azzererebbe
l'orologio: il presidio tacerebbe un'ora in più, non suonerebbe a vuoto.

---

### ⚠️ Le soglie sono una scelta, non una misura

Un'ora, come la gemella. Non viene dalla cadenza del drenatore: una soglia dedotta dai tempi di
oggi si taglierebbe addosso al carico di oggi. Una stampa ferma da un'ora è un drenatore morto o
un arretrato che nessuno ha deciso, e due soglie uguali tengono la simmetria.

---

### Che cosa resta fuori

* le righe **archiviate**: qualcuno le ha già guardate e messe via;
* niente `ANNULLATO`: la coda delle stampe non ha quello stato.

---

### ⛔ Perimetro `DEFINER`

`vendite.fatture_stampa_coda` ha la row level security (gli emittenti dell'operatore) e la vista è
`security_invoker`: una persona la legge col suo perimetro. Il digest la conta con
`dbops.fn_conta_presidio` da proprietario e riporta il numero. Sta in `dbops` e non in `vendite`
perché il catalogo dei presidi legge il perimetro dagli schemi in cui le viste stanno.

---

### Test

* `db/pgtap/dbops/test-vw-fatture-stampa-coda-da-guardare.sql` — una stampa in `ERRORE`, una
  `IN_CORSO` da oltre un'ora e una `PENDING` da oltre un'ora compaiono col loro motivo; una appena
  accodata, una appena presa e una archiviata no. ⚠️ Vuole quattro fatture dell'operatore senza
  riga di stampa viva: dove non ci sono, lo dichiara con uno `skip`.

---

### Note di migrazione

* 2026-09-11 — nasce, perché delle due code gemelle una sola aveva il presidio
  (`brief-db-quattro-processi-senza-presidio`).

---

{% include-markdown "signature-core.md" %}
