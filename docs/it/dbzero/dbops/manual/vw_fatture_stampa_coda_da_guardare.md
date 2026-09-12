## 📘 Documentazione Concettuale – View `dbops.vw_fatture_stampa_coda_da_guardare`

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/manual/vw_coda_lavori_da_guardare) — *la gemella, sulla coda generica*
>
Approfondimenti tabelle:
>
[vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda)
> [dbops.presidi](/dbzero/dbops/manual/presidi)
>
Approfondimenti funzioni:
>
[dbops.fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio)

---
### 🎯 Scopo Principale
(latest review 11-09-2026)

Elenca le stampe in coda che **chiedono un occhio**. Deve restare vuota.

È la gemella di [vw_coda_lavori_da_guardare](/dbzero/dbops/manual/vw_coda_lavori_da_guardare):
le due code sono simmetriche per decisione — stessa forma, stessa bandiera
`archiviato`, un pgTAP che le confronta — ma il presidio ce l'aveva **una sola**.
Se il drenatore della stampa si fermava, le fatture restavano in coda e il
digest non diceva niente.

---

### ⭐ Tre motivi, perché sono tre guasti diversi

| Motivo | Che cos'è successo | Che cosa si fa |
| --- | --- | --- |
| **fallito** | la stampa ha esaurito i tentativi (`ERRORE`) | si legge `ultimo_errore` e si decide |
| **preso e mai chiuso** | `IN_CORSO` da oltre un'ora: il worker è morto a metà — **e il reaper non è passato** | si riaccende il drenatore |
| **mai preso** | ⛔ `PENDING` da oltre un'ora: **il drenatore della stampa non sta girando** | si riaccende il drenatore |

⚠️ Il secondo caso, col drenatore vivo, **non può succedere**: il suo reaper
riporta a `PENDING` dopo 30 minuti. Se compare, è morto anche il reaper — cioè
il drenatore intero.

---

### ⭐ `data_update` è l'ultima transizione di stato

La tabella non ha `claimed_at`. Non serve: l'audit trigger porta `data_update`
a `now()` a **ogni** scrittura, e sulle righe vive (`PENDING`, `IN_CORSO`)
l'unica scrittura che il drenatore fa è una **transizione di stato** — claim,
esito, reaper. `archiviato` è ammesso solo sugli stati terminali.

⇒ `data_update` dice **da quando la riga è nello stato in cui si trova**. È più
preciso di `claimed_at`: misura da quando è *tornata* `PENDING`, non da quando è
nata. ⭐ Il reaper del drenatore la legge già così: il presidio e il recupero
guardano la stessa colonna.

⚠️ **Non è un vincolo del database.** Una scrittura non di stato su una riga viva
— oggi nessuno la fa — azzererebbe l'orologio. L'effetto sarebbe un presidio che
tace **un'ora in più**, non uno che suona a vuoto: il verso meno grave, ma
dichiarato.

---

### ⚠️ Le soglie sono una scelta, non una misura

Un'ora, come la gemella. Il drenatore gira ogni due minuti e un'ora sono «30
giri», ma non è quello l'argomento: una soglia dedotta dai tempi di oggi si
taglierebbe addosso al carico di oggi. Una stampa `PENDING` da un'ora, con un
drenatore che prende 500 righe ogni due minuti, è un drenatore morto o un
arretrato che nessuno ha deciso. E due soglie uguali tengono la promessa di
simmetria.

---

### Che cosa resta fuori, e perché

* **archiviato** — qualcuno l'ha già guardato e messo via.
* ⚠️ Niente `ANNULLATO`: la stampa non ce l'ha (quattro stati contro cinque).

---

### ⛔ Perimetro `DEFINER`

`vendite.fatture_stampa_coda` ha la row level security (whitelist emittenti
dell'operatore) e questa vista è `security_invoker`: una persona la legge col
suo perimetro; il digest la **conta** con
[fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio) da proprietario e
riporta il numero. Sta in `dbops` e non in `vendite` perché il catalogo dei
presidi legge il proprio perimetro dagli schemi che vi compaiono.

---

### Verifica

`db/pgtap/dbops/test-vw-fatture-stampa-coda-da-guardare.sql` — il gemello riga
per riga del test della coda generica: i tre casi che devono comparire, i due
freschi che non devono, l'archiviato. ⚠️ Vuole quattro fatture libere
dell'operatore (una riga viva per fattura): dove non ci sono, lo dichiara con
`skip()`.

Origine: `docs/it/dev/work-done/brief-db-quattro-processi-senza-presidio.md` §4 · §10.1 (D1, D2).
