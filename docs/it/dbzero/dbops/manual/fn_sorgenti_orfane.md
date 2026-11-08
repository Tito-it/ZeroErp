## 📘 Documentazione Concettuale – Funzione `dbops.fn_sorgenti_orfane`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento: tabella del documento, delle righe e del dettaglio, e la chiave di ciascuno
>
> Approfondimento viste:
>
> * [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — la vista che la espone, iscritta fra i presidi
>
> Approfondimento funzioni:
>
> * [dbops.fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro) — le tabelle che esamina, con la loro grammatica
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico, che impedisce di scrivere un orfano
> * [script.trgfn_sorgente_in_uscita](/dbzero/script/funzioni/trgfn_sorgente_in_uscita) — il lato «in uscita», che impedisce di crearne cancellando l'origine
> * [script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id) e [script.fn_sorgente_chiave_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid) — la forma canonica di una chiave in testo, per le tabelle testuali
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga, dettaglio

---

### 🎯 Scopo Principale

Trova le righe la cui **provenienza** punta a qualcosa che non c'è più: un documento che non
esiste, una riga che non c'è o non è di quel documento, un dettaglio che non c'è o non è di quella
riga. Per ogni tabella del perimetro e per ogni tipo di documento presente, cerca l'origine nelle
tabelle che il catalogo dichiara, e restituisce una riga per orfano, col **livello** a cui manca
(`DOCUMENTO`, `RIGA`, `DETTAGLIO`) e la tabella dove manca. È il calcolo dietro
`dbops.vw_sorgenti_orfane`.

---

### ⭐ Perché serve, se c'è il guard

La provenienza è un tipo a catalogo più la chiave del documento (con la riga e il dettaglio), e la
tabella d'origine cambia con il tipo: non è una chiave esterna e non può esserlo. Il guard unico
impedisce di **scrivere** una provenienza che non si risolve; il lato «in uscita» impedisce di
cancellare un'origine ancora referenziata, o cancella i figli con lei. Questa funzione trova gli
orfani nati per altre strade: una tabella senza guard, una cancellazione fatta a trigger spenti.
Il risultato atteso è vuoto.

---

### Come confronta

* Il perimetro lo dà `dbops.fn_sorgenti_orfane_perimetro`; le tabelle esenti dagli orfani (il log
  dei reconcile) non si esaminano.
* I livelli li dice il catalogo, tipo per tipo: la tabella del documento, quella delle righe con la
  colonna che le lega al documento, quella del dettaglio con la colonna che lo lega alla riga. Un
  tipo senza tabella del documento non si esamina; un livello che il tipo non ha, o che la tabella
  non porta, si salta.
* **Grammatica `UNICO`** (la tabella monta il guard unico): la chiave del documento è nella colonna
  che dice `config.sorgenti.key_selector`, `sorgente_uid` per i tipi a chiave `uid`, `sorgente_id`
  per gli altri, e si confronta con la chiave omonima del documento. La riga deve esistere **ed
  essere di quel documento**; il dettaglio deve esistere **ed essere di quella riga**.
* **Grammatica `TESTUALE`** (la tabella non monta il guard unico): la chiave sta in `sorgente_uid`,
  come id o come uid, e si riconosce solo nella forma canonica, con `script.fn_sorgente_chiave_id`
  e `script.fn_sorgente_chiave_uuid`; si controlla il solo livello del documento.
* I nomi di tabelle e colonne vengono dal catalogo di PostgreSQL, dal perimetro e da
  `config.sorgenti`, mai da un input.

---

### ⚠️ Gira coi privilegi del proprietario

È `SECURITY DEFINER` del proprietario degli schemi, con il `search_path` fissato, e legge soltanto.
Il motivo è la row level security: un orfano in una tabella protetta va visto comunque, anche da chi
non ne vedrebbe la riga.

---

### ⚠️ La forma del ciclo interno

Il ciclo che legge «quali tipi di documento ci sono in questa tabella» è una query dinamica, e il suo
bersaglio è una variabile tipizzata sulla colonna di `config.sorgenti`, non un record. Un record
riempito da una query dinamica ha una forma che il controllo statico delle funzioni non conosce, e il
presidio dei riferimenti morti lo segnala come difetto reale. La regola vale per ogni ciclo su una
query dinamica del progetto: chi tocca questa funzione tiene la forma.

---

### Test

* `db/pgtap/dbops/test-sorgenti-orfane-v1.sql` — zero orfani di magazzino sul mondo costruito; un
  orfano per livello sulle tabelle `UNICO` (il documento che non c'è, la riga di un altro documento,
  il dettaglio di un'altra riga) e uno sulla grammatica `TESTUALE`, ognuno come una sola riga; il
  conteggio del presidio uguale alla vista.
* `db/pgtap/magazzino/test-porta-ledger-v1.sql`, test 10 — la funzione è `SECURITY DEFINER` con il
  `search_path` fissato.

---

### Note di migrazione

* 2026-09-18 — nasce con il secondo lotto del magazzino (`brief-db-magazzino-lotto-2-motore`). Lo
  stesso giorno il ciclo interno passa dal record ai tre scalari tipizzati, dopo il rosso del presidio
  dei riferimenti morti; firma e comportamento invariati.
* 2026-11-08 — con il cantiere della provenienza documento e riga (`brief-db-sorgente-documento-e-riga`)
  passa ai tre livelli (documento, riga, dettaglio) e alle grammatiche del perimetro; prima cercava
  la sola chiave nel bersaglio del tipo, con un confronto su testo. Il guard di riferimento non è più
  il guard «tipizzato», ritirato, ma il guard unico.

---

{% include-markdown "signature-core.md" %}
