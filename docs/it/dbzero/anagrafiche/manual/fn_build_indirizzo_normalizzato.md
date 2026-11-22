## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_build_indirizzo_normalizzato`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico, che si salva coi valori di questa funzione
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via
>
> Approfondimento viste:
>
> * [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo) — dove la funzione legge toponimo e nome della via
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) — il trigger che scrive questi valori sulla riga
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) — il «trova o crea», che cerca con questi valori
> * [script.fn_check_indirizzo_duplicato](/dbzero/script/funzioni/fn_check_indirizzo_duplicato) — il controllo del doppione, che confronta la stringa normalizzata
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi e dello stradario

---

### 🎯 Scopo Principale

`anagrafiche.fn_build_indirizzo_normalizzato` dice come si salva un civico: riceve la via e i valori del
dettaglio come li scrive una persona, e restituisce i valori normalizzati e le tre stringhe derivate. È la
sola sede di queste regole.

---

### ⭐ Una normalizzazione sola, per chi salva e per chi cerca

La usano il trigger che scrive la riga, il «trova o crea» che cerca il civico prima di crearlo e il controllo
del doppione. Se chi cerca normalizzasse in un altro modo da chi salva, cercherebbe una riga che non può
esistere e ne creerebbe una seconda: un'estensione `a` scritta oggi non troverebbe la `/A` di ieri.

---

### Le regole

* **Il dettaglio** (estensione, palazzina, scala, piano, interno): spazi in testa e in coda tolti, maiuscolo, e
  un testo vuoto diventa nessun valore. Il «non c'è» ha una forma sola, perché l'indice della chiave tratta i
  vuoti come uguali.
* **L'estensione** prende il `/` davanti, se non l'ha: `a`, `A` e `/A` sono la stessa estensione.
* **La via normalizzata** (`o_via_norm`) è toponimo e nome della via, in maiuscolo, letti dalla via risolta.
* **Il civico normalizzato** (`o_civico_norm`) è il numero seguito dall'estensione; senza numero è `SNC`. Il
  civico zero o negativo non è un modo di dire «senza numero»: lo rifiuta il guard della chiave.
* **L'indirizzo normalizzato** (`o_indirizzo_normalizzato`) mette in fila, separati da virgola e spazio, la via,
  il civico e, quando ci sono, palazzina, scala, piano e interno coi loro prefissi `Pal.`, `Scala `, `Piano `,
  `Int.`: per esempio `VIA ROMA, 12/A, Pal.B, Scala C, Piano 2, Int.3`. È la stringa su cui lavora la ricerca
  per testo.

---

### Una via che non si risolve dà tutto vuoto

Se la via non c'è, o non si risolve nella catena via → comune → provincia → CAP di `script.vw_indirizzo_completo`
(un comune senza provincia, per esempio), la funzione restituisce tutto vuoto, anche il dettaglio. Chi la usa
deve fermarsi lì: il «trova o crea» risponde `E_INDIRIZZO_VIA_NON_RISOLTA`, invece di cercare con una chiave
vuota e trovare il civico nudo della via.

La funzione non solleva errori e non scrive niente.

---

### ⚠️ Che cosa oggi non copre

* **Il trigger non si ferma sulla via non risolta**: assegna i valori vuoti alla riga, e l'inserimento o la
  modifica falliscono con l'errore tecnico della colonna obbligatoria `via_norm`, senza un codice che dica qual è
  il problema.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — la stessa chiave scritta maiuscola, con spazi
  o col `/` che trova la stessa riga, il testo vuoto uguale a nessun valore, la via che non si risolve.

---

### Note di migrazione

* 2026-10-25 — il testo vuoto del dettaglio diventa nessun valore, e `SNC` vale solo per il civico senza
  numero: prima lo zero era un secondo modo di dirlo.

---

{% include-markdown "signature-core.md" %}
