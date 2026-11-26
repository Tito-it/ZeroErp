## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento`

> **Ultimo aggiornamento**: 24 novembre 2026
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

### I controlli

| Controllo | Rifiuto |
| --- | --- |
| l'elemento è un oggetto | `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| ha solo chiavi di un indirizzo | `E_CAMPO_NON_AMMESSO`, col nome della chiave |
| il tipo c'è | `E_TIPO_INDIRIZZO_NON_TROVATO`, col campo `tipo_indirizzo_codice_interno` |
| l'id del tipo, se c'è, è un numero e un tipo del catalogo | `E_TIPO_INDIRIZZO_NON_TROVATO`, col campo `tipo_indirizzo_id` |
| l'id e il codice, se ci sono tutti e due, dicono lo stesso tipo | `E_TIPO_INDIRIZZO_DISCORDE`, col campo `tipo_indirizzo_codice_interno` e i due valori |

Le chiavi ammesse sono le colonne della riga (il testo libero, lo stato, comune e CAP, i campi della forma estera, il
dettaglio, il tipo) più quelle di una via da risolvere (la via del catalogo, tipo strada e nome di una via nuova, il
civico e i suoi dettagli). Il tipo per codice si legge senza spazi e in maiuscolo. Il tipo per id si verifica sul
catalogo: un id che non esiste, o che non è un numero, si rifiuta qui col suo campo, invece di arrivare al guard del
tipo con un motivo sbagliato o al database con l'errore grezzo.

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

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — l'elemento non è un oggetto.
* `E_CAMPO_NON_AMMESSO` — una chiave che un indirizzo non ha.
* `E_TIPO_INDIRIZZO_NON_TROVATO` — nessun tipo, un codice che non esiste, o un id che non esiste o non è un numero.
* `E_TIPO_INDIRIZZO_DISCORDE` — l'id e il codice dicono due tipi diversi.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` — le chiavi estranee, la chiave ritirata
  `tipo_indirizzo_codice`, l'elemento che non è un oggetto, il codice vuoto o inesistente, attraverso la madre del
  soggetto.
* `db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql` — gli stessi rifiuti attraverso la plurale del ruolo.
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (17, 18, 19, 20) — l'id che non esiste e quello
  non numerico, l'id e il codice discordi, il solo codice che passa.

---

### Note di migrazione

* 2026-10-18 — nasce. Prima la madre del ruolo aveva queste regole nel suo corpo, e la madre del soggetto non le aveva
  affatto: due grammatiche, già divergenti.
* 2026-11-24 — l'id del tipo si verifica, e si confronta col codice quando ci sono tutti e due: prima l'id si
  prendeva com'era, e con id e codice insieme vinceva l'id.

---

{% include-markdown "signature-core.md" %}
