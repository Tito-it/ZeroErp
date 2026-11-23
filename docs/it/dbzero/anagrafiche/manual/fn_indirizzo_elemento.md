## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — i tipi, per id o per codice interno
>
> Approfondimento funzioni:
>
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il guard che rifiuta la chiave fuori elenco (`E_CAMPO_NON_AMMESSO`)
> * [anagrafiche.fn_indirizzo_elemento_dettaglio](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_dettaglio) — il passo dopo: il dettaglio dell'elemento
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la madre del soggetto
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la madre del ruolo
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — la forma dell'indirizzo libero, che qui non si giudica
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — le tre forme di un indirizzo

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzo_elemento` legge un indirizzo scritto in jsonb per le madri che scrivono gli indirizzi, e lo
restituisce col tipo risolto in `tipo_indirizzo_id`. È la grammatica comune: le singolari e le plurali del soggetto e
del ruolo la usano tutte, quindi accettano le stesse chiavi.

---

### Tre controlli

| Controllo | Rifiuto |
| --- | --- |
| l'elemento è un oggetto | `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| ha solo chiavi di un indirizzo | `E_CAMPO_NON_AMMESSO`, col nome della chiave |
| il tipo c'è | `E_TIPO_INDIRIZZO_NON_TROVATO`, col campo `tipo_indirizzo_codice_interno` |

Le chiavi ammesse sono le colonne della riga (il testo libero, lo stato, comune e CAP, i campi della forma estera, il
dettaglio, il tipo) più quelle di una via da risolvere (la via del catalogo, tipo strada e nome di una via nuova, il
civico e i suoi dettagli). Il tipo per codice si legge senza spazi e in maiuscolo.

Le madri passano il proprio nome, per il log, e le chiavi da aggiungere al contesto dei rifiuti (il soggetto o il
ruolo).

---

### Che cosa non fa

* **Non giudica la completezza né la forma** dell'indirizzo libero: lo fa il guard della tabella,
  `anagrafiche.trgfn_indirizzi_guard_forma_libera`.
* **Non conosce l'istanza**: un indirizzo del soggetto non ne ha, e quella di un indirizzo del ruolo la legge la
  singolare del ruolo prima di chiamarla.
* **Non risolve la via**: è il passo dopo, `anagrafiche.fn_indirizzo_elemento_dettaglio`.

---

### ⚠️ Che cosa oggi non copre

* **Il tipo indicato per id non si verifica.** Il catalogo dei tipi si legge solo quando il tipo arriva per codice: un
  `tipo_indirizzo_id` che non esiste passa, e il rifiuto arriva dopo, dal motivo «non ammesso dalla natura» se la
  natura ha una matrice, altrimenti dalla chiave esterna della tabella, con l'errore grezzo del database. Con id e codice
  insieme vale l'id, e il codice non si confronta.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — l'elemento non è un oggetto.
* `E_CAMPO_NON_AMMESSO` — una chiave che un indirizzo non ha.
* `E_TIPO_INDIRIZZO_NON_TROVATO` — nessun tipo, o un codice che non esiste.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` — le chiavi estranee, la chiave ritirata
  `tipo_indirizzo_codice`, l'elemento che non è un oggetto, il codice vuoto o inesistente, attraverso la madre del
  soggetto.
* `db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql` — gli stessi rifiuti attraverso la plurale del ruolo.

---

### Note di migrazione

* 2026-10-18 — nasce. Prima la madre del ruolo aveva queste regole nel suo corpo, e la madre del soggetto non le aveva
  affatto: due grammatiche, già divergenti.

---

{% include-markdown "signature-core.md" %}
