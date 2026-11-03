## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_coda_archiviazione`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — la coda generica: uno dei due bersagli
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda delle stampe: l'altro bersaglio
>
> Approfondimento viste:
>
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — il presidio che non elenca le righe archiviate
> * [dbops.vw_fatture_stampa_coda_da_guardare](/dbzero/dbops/views/vw_fatture_stampa_coda_da_guardare) — la gemella sulla coda delle stampe
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — da dove passa il rifiuto
>
> Guide:
>
> * [Gestione delle code di lavoro](/guide/gestione-code-di-lavoro) — le code e chi le legge

---

### 🎯 Scopo Principale

Governa la bandiera `archiviato` delle due code, `dbops.coda_lavori` e
`vendite.fatture_stampa_coda`: rifiuta l'archiviazione di una riga ancora viva, riabbassa la
bandiera quando una riga archiviata torna viva, e scrive lei la data e l'autore
dell'archiviazione.

---

### ⭐ Una funzione per due tabelle

Le colonne dell'archiviazione sono identiche sulle due code per costruzione, e due copie della
regola divergerebbero al primo che ne tocca una sola. I due trigger nascono nello stesso changeSet,
con la stessa definizione, e un pgTAP lo verifica.

«Viva» ha una definizione sola, la stessa del badge in topbar: `PENDING` oppure `IN_CORSO`. Si
scrive così, e non come elenco degli stati finali, perché gli stati finali delle due code sono
diversi (la coda delle stampe non ha `ANNULLATO`).

---

### Che cosa fa, riga per riga

* **Una riga viva si sta archiviando** (la bandiera passa da falsa a vera): rifiuto,
  `E_CODA_ARCHIVIAZIONE_NON_AMMESSA`. Il rifiuto guarda la **direzione**, non la sola menzione della
  colonna: un aggiornamento che riscrive lo stesso valore non archivia niente e passa.
* ⭐ **Una riga archiviata torna viva** (requeue, reaper, nuovo tentativo): la bandiera si abbassa
  da sola. Una riga rimessa al lavoro deve tornare nell'elenco, altrimenti sarebbe viva e
  invisibile.
* **La bandiera si alza**: data e autore li mette il database. L'autore è l'utente applicativo
  della sessione, o il ruolo del database quando manca.
* **La bandiera si abbassa**: data e autore si svuotano con lei, così la riga non dice «non
  archiviata, archiviata il 3 settembre».
* **La riga resta archiviata**: data e autore restano quelli di prima, qualunque valore il
  chiamante provi a scrivere. Sono immutabili finché la bandiera resta alzata.

Il nome non porta `guard` perché la funzione scrive la riga, oltre a rifiutarla.

---

### Dove scatta, e dove non scatta

È agganciata `BEFORE UPDATE` per riga sulle quattro colonne della bandiera e sullo stato, nella
fase `_a10_`, prima dei trigger di audit e del `tx_id`. Una clausola sul trigger la tiene fuori
dalla corsia del drenatore: sulle righe mai archiviate, dove nessuno scrive la bandiera né i suoi
timbri, la funzione non viene nemmeno chiamata, anche se lo stato cambia.

Il vincolo `chk_coda_lavori_archiviato_non_vivo` (e il gemello sulla coda delle stampe) resta la
sede dell'invariante: vale anche per una scrittura che non passa da questa funzione, come un
inserimento già archiviato. La funzione è la sede del messaggio.

---

### Codici errore

* `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` — si archivia una riga `PENDING` o `IN_CORSO`; il messaggio
  nomina lo stato della riga.

---

### Test

* `db/pgtap/dbops/test-coda-archiviazione.sql` — i due trigger hanno la stessa definizione e la
  stessa funzione; archiviare una riga viva è rifiutato su entrambe le code, una finita passa; i
  timbri li deriva il database e restano immutabili; al requeue bandiera e timbri si azzerano; un
  inserimento archiviato e vivo, o archiviato senza timbri, lo prende il vincolo.

---

### Note di migrazione

* 2026-09-04 — nasce con l'archiviazione delle righe di coda, sulle due code insieme
  (`brief-db-archiviazione-righe-code`).

---

{% include-markdown "signature-core.md" %}
