## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_scrivi_dati_societari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga che la funzione crea o aggiorna
> * [config.parameters](/dbzero/config/tabelle/parameters) — i valori proposti per socio unico e liquidazione
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari_alla_nascita) — chi la chiama alla nascita del soggetto
> * [anagrafiche.fn_elimina_dati_societari](/dbzero/anagrafiche/funzioni/fn_elimina_dati_societari) — la porta gemella, per l'eliminazione
> * [script.fn_get_parameter_di_sessione](/dbzero/script/funzioni/fn_get_parameter_di_sessione) — il parametro letto col contesto della sessione

---

### 🎯 Scopo Principale

`anagrafiche.fn_scrivi_dati_societari` è la porta di scrittura dei dati societari di un soggetto: crea la riga
se manca, la aggiorna se c'è, e restituisce il suo id. L'applicazione non scrive la tabella direttamente.

La chiamano l'applicazione quando si modifica un soggetto, `anagrafiche.fn_scrivi_dati_societari_alla_nascita`
quando nasce, e le fixture dei test.

---

### Riceve lo stato intero della sezione

Ogni chiamata scrive tutte le colonne: un valore non passato scrive `NULL` dove la colonna lo ammette, non
lascia il valore di prima. Chi vuole cambiare un campo solo rilegge la riga e la rimanda intera.

* **I testi** (REA, canale, PEC, codice SDI) si ripuliscono degli spazi in testa e in coda, e un testo vuoto
  vale `NULL`.
* **Socio unico e liquidazione**, che sono obbligatori, se non passati prendono il valore proposto dai
  parametri `dati_societari_default_socio_unico` e `dati_societari_default_liquidazione`, letti col contesto
  della sessione (quindi con l'eventuale valore dell'azienda attiva). Un parametro che manca è un errore: non
  c'è un valore di riserva, e il default della colonna non si usa.
* **La forma** non ha un valore proposto: se manca, la riga è rifiutata dal vincolo `NOT NULL` della colonna.

---

### ⭐ Una porta senza regole

La funzione controlla soltanto il soggetto: che sia passato e che esista. Tutto il resto (la natura che
ammette la riga, la forma, REA e capitale, il canale) lo dicono i trigger della tabella, che scattano anche da
qui. Il permesso lo decide l'applicazione, come per `anagrafiche.soggetti`: la funzione gira coi privilegi del
proprietario, perché l'applicazione sulla tabella ha solo la lettura.

Se nella stessa operazione cambia anche la natura del soggetto, si scrive prima il soggetto e poi si chiama
la funzione: la forma nuova si giudica sulla natura nuova.

---

### ⚠️ Che cosa oggi non copre

* **Due prime scritture concorrenti dello stesso soggetto.** La funzione prova l'aggiornamento e, se non
  trova la riga, la inserisce, senza bloccare il soggetto: due chiamate parallele che la trovano entrambe
  assente inseriscono tutte e due, e la seconda è rifiutata da `uq_ds_soggetto` con l'errore grezzo del
  vincolo.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il soggetto non è passato.
* `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` — il soggetto passato non esiste.

Gli altri rifiuti vengono dai trigger della tabella, coi loro codici.

---

### Test

* `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` — la porta (eseguibile dall'applicazione, non da
  tutti; la tabella in sola lettura), la creazione e l'aggiornamento a stato intero, socio unico dal
  parametro, il soggetto mancante o inesistente, la forma con REA e capitale, il cambio di natura nei due
  ordini.
* `db/pgtap/anagrafiche/test-dati-societari-canale-fe-v1.sql` — il canale e i suoi recapiti passando dal verbo.

---

### Note di migrazione

* 2026-10-11 — nasce, e diventa l'unica porta di scrittura: all'applicazione resta la sola lettura della
  tabella.

---

{% include-markdown "it/dbzero/anagrafiche/_dati-societari.md" %}

---

{% include-markdown "signature-core.md" %}
