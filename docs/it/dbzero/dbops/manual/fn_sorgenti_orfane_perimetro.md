## 📘 Documentazione Concettuale – Funzione `dbops.fn_sorgenti_orfane_perimetro`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo verso cui puntano le chiavi esterne che il perimetro cerca
>
> Approfondimento viste:
>
> * [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — il presidio degli orfani
>
> Approfondimento funzioni:
>
> * [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane) — la funzione che esamina queste tabelle
> * [script.trgfn_guard_sorgente_polimorfa_tipizzata](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata) — il guard che fa entrare una tabella nel perimetro
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello del collegamento tipo + chiave

---

### 🎯 Scopo Principale

Le tabelle che il presidio degli orfani di sorgente esamina, rese visibili: quelle con una chiave
esterna su una colonna sola verso `config.sorgenti`, le due colonne di chiave `sorgente_riga` e
`sorgente_uid`, **e il guard tipizzato montato**.

---

### ⭐ Il perimetro si ricava dal vincolo, non da un elenco

Una tabella nuova con quella forma entra da sola, senza che nessuno aggiorni una lista. E il
perimetro è visibile per un motivo preciso: un presidio che esamina zero tabelle è verde e muto. Il
test asserisce che le tabelle di magazzino ci sono.

---

### ⛔ È il guard a decidere, non le colonne

Il guard tipizzato è il contratto del collegamento: «un tipo, esattamente una chiave, che punta al
bersaglio dichiarato». Alcune tabelle di vendite hanno la stessa chiave esterna e le stesse colonne,
ma un'altra semantica: la riga è la riga del documento e l'identificativo universale è il documento.
Esaminate col criterio degli orfani darebbero falsi orfani: il criterio cercherebbe la riga del
documento nel bersaglio del documento. Restano fuori finché non
prendono il guard.

⚠️ Il guard si riconosce dal nome della funzione del trigger, senza schema.

---

### Test

* `db/pgtap/dbops/test-sorgenti-orfane-v1.sql`, test 1 e 2 — il perimetro contiene le tabelle di
  magazzino, e solo tabelle con il guard tipizzato montato.

---

### Note di migrazione

* 2026-09-18 — nasce con il secondo lotto del magazzino (`brief-db-magazzino-lotto-2-motore`). Senza
  il filtro sul guard, le tabelle di vendite davano 112 falsi orfani sul database di sviluppo.

---

{% include-markdown "signature-core.md" %}
