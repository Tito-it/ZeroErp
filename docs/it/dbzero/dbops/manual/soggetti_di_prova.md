## 📘 Documentazione Concettuale – Tabella `dbops.soggetti_di_prova`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.credenziali_di_prova](/dbzero/dbops/tabelle/credenziali_di_prova) — la gemella: l'etichetta delle credenziali di prova
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto etichettato
>
> Approfondimento viste:
>
> * [dbops.vw_radici_di_prova_in_produzione](/dbzero/dbops/views/vw_radici_di_prova_in_produzione) — il presidio che legge le etichette
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — il verbo dei dati di sviluppo, unico scrittore
> * [dbops.trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard) — il guard: nasce solo in sviluppo, poi non cambia

---

### 🎯 Scopo Principale

**L'etichetta dei soggetti di prova**: una riga per ogni soggetto creato dal verbo dei dati
di sviluppo (le aziende emittenti, i clienti, il fornitore, le persone dietro le credenziali
di prova), con la sua chiave, per esempio `DEV-EMITTENTE-A`.

L'etichetta nasce nella stessa transazione del soggetto. L'applicazione la legge e non la
scrive.

---

### ⭐ Si etichettano le radici, non le righe

Contratti, conti di fatturazione e documenti non hanno un'etichetta loro: si ritrovano dal
soggetto a cui sono legati. Basta quindi un'etichetta per radice perché il presidio veda
tutto ciò che il verbo ha costruito.

---

### ⛔ Non cambia, non si toglie, in produzione non nasce

Stesse regole delle [credenziali di prova](/dbzero/dbops/tabelle/credenziali_di_prova), con
lo stesso guard: la scrive solo il verbo dei dati di sviluppo, nasce solo in un'installazione
dichiarata `SVILUPPO`, modifica e svuotamento sono sempre rifiutati, e la cancellazione è
rifiutata finché il soggetto c'è.

Come la gemella, il soggetto è legato con una chiave esterna, e l'etichetta non può puntare a
un soggetto che non esiste. A differenza della gemella il legame non è in cascata: un soggetto
con l'etichetta non si cancella, e l'etichetta resta con lui.

---

### Codici errore

Li solleva il guard [trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard):

* `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` — un'etichetta nuova su un'installazione che non è di
  sviluppo;
* `E_CONFIG_MANCANTE` — un'etichetta nuova su un'installazione che non ha dichiarato
  l'ambiente;
* `E_ETICHETTA_DI_PROVA_IMMUTABILE` — modifica, cancellazione o svuotamento.

---

### Test

* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — l'applicazione legge e non scrive; in
  sviluppo l'etichetta nasce, poi modifica, cancellazione e svuotamento sono rifiutati; in
  produzione e con l'ambiente non dichiarato un'etichetta nuova è rifiutata.
* `db/pgtap/anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1.sql` — il verbo etichetta i
  soggetti che crea.

---

### Note di migrazione

* 2026-10-18 — nasce con il verbo dei dati di sviluppo (`brief-db-processi-accensione-per-ambiente`, R-4).

---

{% include-markdown "signature-core.md" %}
