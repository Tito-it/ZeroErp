## 📘 Documentazione Concettuale – Vista `dbops.vw_stati_check_da_sanare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.stati_check_dichiarazioni](/dbzero/dbops/tabelle/stati_check_dichiarazioni) — il registro da allargare, o da cui togliere
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove la vista è un cancello
>
> Approfondimento viste:
>
> * [dbops.vw_stati_check_scrittori](/dbzero/dbops/views/vw_stati_check_scrittori) — la misura da cui la vista è ricavata
>
> Guide:
>
> * [Presidi e registri del debito — uno stato mai scritto](/guide/presidi-e-registri-del-debito#36-uno-stato-previsto-dal-modello-e-mai-scritto) — il presidio per intero

---

### 🎯 Scopo Principale

La lista di lavoro del presidio degli stati mai scritti: la misura ridotta alle sole righe che
chiedono un gesto. **Deve restare vuota**, e ogni riga dice che cosa fare (`da_fare`).

---

### Le due righe possibili

| `esito` | Che cos'è | Il gesto |
| --- | --- | --- |
| `NON_DICHIARATO` | un valore ammesso che nessuno scrive e nessuno ha guardato | o si scrive chi lo scrive, o la riga entra nel registro con il canale e la ragione |
| `DEBITO_ESTINTO` | una riga di registro che non serve più: il valore ha trovato uno scrittore nel database, o è uscito dal vincolo | si toglie dal seed del registro, e si cancella con una migrazione in avanti |

`scrittori_tabella` accompagna ogni riga con le funzioni che scrivono quella tabella: è da lì che
si parte per capire se il valore manca davvero.

---

### ⭐ È un cancello, non un promemoria

Nel catalogo dei presidi è classificata come **cancello**: il test
`db/pgtap/dbops/test-stati-check-scrittori-v1.sql` la fa rossa in CI, quindi non entra nel digest.
Un avviso che ripete ciò che un cancello ha già fermato è rumore.

⚠️ Il cancello ha **due lati**, e questa vista ne mostra uno. Le righe che il programma dichiara di
scrivere (`DICHIARATO_APPLICAZIONE` nella misura) qui non compaiono: le verifica il test del backend,
che cerca il valore nei file che scrivono quella tabella e diventa rosso se sparisce.

⛔ Non si allarga il filtro per farla tacere: si allarga il **registro**, con la ragione.

---

### Test

* `db/pgtap/dbops/test-stati-check-scrittori-v1.sql`, test 2, 3 e 5 — nessuna riga `NON_DICHIARATO` e
  nessuna `DEBITO_ESTINTO`; un valore nuovo costruito apposta compare nella lista di lavoro.

---

### Note di migrazione

* 2026-09-21 — nasce col presidio degli stati mai scritti (`brief-db-presidio-stati-mai-scritti`).

---

{% include-markdown "signature-core.md" %}
