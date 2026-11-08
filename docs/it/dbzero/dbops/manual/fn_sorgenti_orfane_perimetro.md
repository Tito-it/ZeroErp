## 📘 Documentazione Concettuale – Funzione `dbops.fn_sorgenti_orfane_perimetro`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento a cui rimanda `sorgente_tipo_id`
>
> Approfondimento viste:
>
> * [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — il presidio degli orfani
>
> Approfondimento funzioni:
>
> * [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane) — la funzione che esamina queste tabelle
> * [script.fn_sorgente_guard_montaggi](/dbzero/script/funzioni/fn_sorgente_guard_montaggi) — i montaggi del guard unico, da cui si legge la grammatica
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga, dettaglio

---

### 🎯 Scopo Principale

Il perimetro della provenienza, reso visibile: ogni tabella che dice «nasce da», cioè che ha
`sorgente_tipo_id` e almeno una fra `sorgente_id` e `sorgente_uid`, con le colonne della provenienza
che porta, la sua **grammatica** e le esenzioni dichiarate. Lo leggono il presidio degli orfani e il
presidio di struttura.

---

### ⭐ Il perimetro si ricava dalle colonne, non da un elenco

Una tabella nuova con la provenienza entra da sola, senza che nessuno aggiorni una lista. Restano
fuori lo schema `storico` (le copie della storia non sono provenienze vive) e le tabelle temporanee
di altre sessioni; una temporanea della sessione entra se chi chiede la può leggere, ed è così che i
test costruiscono i loro casi. Il perimetro è visibile per un motivo preciso: un presidio che esamina
zero tabelle è verde e muto.

---

### La grammatica: chi monta il guard unico

* **`UNICO`** — la tabella monta il guard unico (`script.trgfn_guard_sorgente`), come lo elenca
  `script.fn_sorgente_guard_montaggi`: tipo, una chiave fra `sorgente_id` e `sorgente_uid` secondo il
  catalogo, riga e dettaglio. Gli orfani si cercano ai tre livelli.
* **`TESTUALE`** — la tabella non monta il guard unico: la chiave sta in `sorgente_uid`, come id o
  come uid, e si riconosce solo nella forma canonica. Gli orfani si cercano al solo livello del
  documento.

Il presidio di struttura fa rossa ogni tabella `TESTUALE` che non sia esente dal guard o iscritta nel
suo elenco chiuso del debito: oggi sono le quattro tabelle degli acquisti (`acquisti.ordini`,
`acquisti.ordini_righe`, `acquisti.ddt`, `acquisti.ddt_righe`), che non sono ancora sul modello.

---

### ⛔ Le esenzioni sono dichiarate, col motivo

Due colonne dicono perché una tabella resta fuori, e da che cosa:

* `orfani_esclusi_perche` — fuori dal presidio degli orfani;
* `guard_esente_perche` — fuori dal guard unico.

Le esenzioni sono due:

* `pratiche.reconcile_errori`, da tutte e due: è un log scritto dentro un `EXCEPTION`, un guard
  d'esistenza lo farebbe tacere, e per costruzione rimanda anche a documenti che non ci sono più;
* `vendite.fatture_stampa_coda`, dal solo guard: la sua chiave è una FK vera verso la fattura, ed
  esistenza e cancellazione le tiene la FK. Per gli orfani resta nel perimetro.

---

### Test

* `db/pgtap/dbops/test-sorgenti-orfane-v1.sql`, test 1, 2, 3 e 7 — il perimetro contiene le tabelle
  di magazzino e le testate di vendita, tutte `UNICO`; le esenzioni sono due, col loro motivo; una
  tabella col guard unico entra con la sua grammatica.
* `db/pgtap/dbops/test-sorgenti-struttura-v1.sql` — il presidio di struttura: chi ha la provenienza
  monta il guard unico, salvo le esenzioni e l'elenco chiuso del debito.

---

### Note di migrazione

* 2026-09-18 — nasce con il secondo lotto del magazzino (`brief-db-magazzino-lotto-2-motore`). Senza
  il filtro sul guard, le tabelle di vendite davano 112 falsi orfani sul database di sviluppo.
* 2026-11-08 — con il cantiere della provenienza documento e riga (`brief-db-sorgente-documento-e-riga`)
  il perimetro non si ricava più dalla chiave esterna verso `config.sorgenti` e dal guard
  «tipizzato», ritirato, ma dalle colonne della provenienza, con la grammatica di ogni tabella e le
  esenzioni in colonna. La grammatica `MODELLO_A`, quella del guard tipizzato, esce quando l'ultima
  tabella passa al guard unico.

---

{% include-markdown "signature-core.md" %}
