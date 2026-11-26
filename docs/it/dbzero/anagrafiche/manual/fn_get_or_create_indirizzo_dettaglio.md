## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_or_create_indirizzo_dettaglio`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico che trova o crea
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via, obbligatoria
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio) — i civici da leggere, su cui il backend fa la ricerca
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — la normalizzazione con cui cerca
> * [anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_guard_chiave) — il giudizio sulla chiave del civico che crea
> * [anagrafiche.fn_create_indirizzo](/dbzero/anagrafiche/funzioni/fn_create_indirizzo) — chi la chiama per creare via e civico insieme
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi e dello stradario

---

### 🎯 Scopo Principale

`anagrafiche.fn_get_or_create_indirizzo_dettaglio` restituisce l'id del civico che corrisponde a una via e a
un dettaglio, creandolo se non c'è. Non restituisce mai un valore vuoto: o un id, o un errore.

---

### ⭐ Cerca coi valori come si salvano

I valori passati attraversano `anagrafiche.fn_build_indirizzo_normalizzato`, la stessa normalizzazione del
trigger, e la ricerca confronta quelli: un'estensione `a`, `A` o `/A`, un interno minuscolo o con uno spazio in
più trovano la stessa riga. Il confronto tratta due vuoti come uguali, come l'indice della chiave, così il civico
senza numero si trova come gli altri.

---

### Che cosa fa

* **La via è obbligatoria e deve esistere**: senza via, o con una via che non c'è, si ferma subito.
* **La via deve risolversi**: se la normalizzazione non trova la via nella catena comune → provincia → CAP, si
  ferma con `E_INDIRIZZO_VIA_NON_RISOLTA`, invece di cercare con una chiave vuota. Lo stesso codice arriva
  anche da chi scrive il civico senza passare di qui, con un inserimento diretto o modificando un civico: lo dà
  il guard della chiave, su ogni strada.
* **Trovato**: ne restituisce l'id. Se il civico era spento lo riaccende: chi usa di nuovo un indirizzo fisico lo
  rimette in uso, e un civico spento non si potrebbe collegare.
* **Non trovato**: lo crea. I trigger della tabella scrivono le colonne derivate e giudicano la chiave, quindi un
  civico zero o un dettaglio di soli segni si fermano col codice del guard.
* **Due sessioni insieme**: se un'altra sessione crea lo stesso civico fra la ricerca e la creazione, l'indice
  rifiuta il secondo e la funzione rilegge, restituendo l'id dell'altra. Se nemmeno la rilettura lo trova, è
  un'incoerenza del database, e lo dice con `E_INDIRIZZO_DETTAGLIO_NON_RILETTO`.

Una via soppressa non riceve civici nuovi: la creazione si ferma sul guard del ritiro della via.

---

### Chi la usa

`anagrafiche.fn_create_indirizzo`, i builder delle fixture pgTAP e l'applicazione, dopo che l'operatore ha
scelto via e civico.

---

### Codici errore

* `E_ADMIN_VALIDAZIONE` — la via non è passata, o non è un id valido.
* `E_CODICE` — la via non esiste.
* `E_INDIRIZZO_VIA_NON_RISOLTA` — la via non si risolve nella catena comune → provincia → CAP. La funzione si
  ferma prima di cercare; lo stesso codice, con lo stesso campo, lo dà il guard della chiave a chi scrive il
  civico per un'altra strada.
* `E_INDIRIZZO_DETTAGLIO_NON_RILETTO` — la creazione è stata rifiutata come doppione, e il doppione non si trova.
* Quelli del guard della chiave, quando crea: `E_INDIRIZZO_CIVICO_NON_POSITIVO`, `E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE`.

---

### Test

* `db/pgtap/anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql` — la creazione, la stessa chiave che
  restituisce lo stesso id, i rifiuti sulla via.
* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — i modi diversi di scrivere la stessa chiave,
  il civico spento che si riaccende, la via che non si risolve.
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (9, 10) — sulla via di un comune senza
  provincia, l'inserimento diretto di un civico e il «trova o crea» danno lo stesso codice.

---

### Note di migrazione

* 2026-10-25 — la ricerca passa dai valori normalizzati (prima confrontava quelli grezzi, e un'estensione
  minuscola creava un doppione), si ferma sulla via non risolta e riaccende il civico spento.
* 2026-11-24 — `E_INDIRIZZO_VIA_NON_RISOLTA` non è più solo suo: lo dà anche il guard della chiave, a un
  inserimento diretto o alla modifica di un civico, che prima cadevano su un vincolo di colonna. Si ritira
  `anagrafiche.fn_search_indirizzi_dettaglio`, la ricerca dei civici: la fa il backend leggendo
  `anagrafiche.vw_indirizzi_dettaglio`.

---

{% include-markdown "signature-core.md" %}
