## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_or_create_indirizzo_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico che trova o crea
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via, obbligatoria
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — la normalizzazione con cui cerca
> * [anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_guard_chiave) — il giudizio sulla chiave del civico che crea
> * [anagrafiche.fn_create_indirizzo](/dbzero/anagrafiche/funzioni/fn_create_indirizzo) — chi la chiama per creare via e civico insieme
> * [anagrafiche.fn_search_indirizzi_dettaglio](/dbzero/anagrafiche/funzioni/fn_search_indirizzi_dettaglio) — la ricerca, che non crea
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
  ferma con `E_INDIRIZZO_VIA_NON_RISOLTA`, invece di cercare con una chiave vuota.
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
* `E_INDIRIZZO_VIA_NON_RISOLTA` — la via non si risolve nella catena comune → provincia → CAP.
* `E_INDIRIZZO_DETTAGLIO_NON_RILETTO` — la creazione è stata rifiutata come doppione, e il doppione non si trova.
* Quelli del guard della chiave, quando crea: `E_INDIRIZZO_CIVICO_NON_POSITIVO`, `E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE`.

---

### Test

* `db/pgtap/anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql` — la creazione, la stessa chiave che
  restituisce lo stesso id, i rifiuti sulla via.
* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — i modi diversi di scrivere la stessa chiave,
  il civico spento che si riaccende, la via che non si risolve.

---

### Note di migrazione

* 2026-10-25 — la ricerca passa dai valori normalizzati (prima confrontava quelli grezzi, e un'estensione
  minuscola creava un doppione), si ferma sulla via non risolta e riaccende il civico spento.

---

{% include-markdown "signature-core.md" %}
