## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_contatto`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — la riga che la funzione fa nascere
>
> Approfondimento funzioni:
>
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il guard che rifiuta la chiave fuori elenco (`E_CAMPO_NON_AMMESSO`)
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura della riga dai campi
> * [anagrafiche.trgfn_contatti_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_set_default_contatto) — il predefinito del contesto
> * [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_contesto_soggetto) — ruolo e istanza sono del soggetto
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — chi la chiama per il primo contatto di una persona fisica
> * [anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) — chi la chiama per il primo contatto di una società
> * [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente) — chi la chiama per il contatto del ruolo cliente
> * [anagrafiche.fn_crea_fornitore](/dbzero/anagrafiche/funzioni/fn_crea_fornitore) — chi la chiama per il contatto del ruolo fornitore
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — chi la chiama per il contatto di un utente tecnico
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il modello dei contatti

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_contatto` crea un contatto di un soggetto, oppure di un suo ruolo (il contatto dell'ufficio
acquisti di un fornitore, per esempio), e restituisce la riga creata.

È la sede unica della nascita di un contatto: la usano i verbi di nascita del soggetto, del cliente e del
fornitore, la creazione degli utenti tecnici, le fixture dei test e l'applicazione.

---

### Nominativo e tipo di contatto, o niente

Un contatto senza nominativo (o con un nominativo di soli spazi) o senza tipo è rifiutato con
`E_CONTATTO_INCOMPLETO`, che porta il campo che manca perché il form lo accenda; si guarda prima il nominativo.

---

### I campi sono un elenco chiuso

Recapiti (email, telefono, cellulare, PEC), note, titolo di cortesia, unità organizzativa, istanza, e il segno
del predefinito. Un campo assente prende il valore predefinito della colonna; una chiave fuori elenco è rifiutata
col suo nome (`E_CAMPO_NON_AMMESSO`). Soggetto e ruolo non sono fra i campi: sono i due parametri della funzione,
e il ruolo vuoto fa un contatto del soggetto.

Il segno del predefinito, se chiesto, fa il contatto predefinito del suo contesto e lo toglie a quello di prima.
`default_context` è fra le chiavi ammesse, ma il valore passato non conta: lo scrive il trigger.

---

### Che cosa lascia agli altri

* **Il permesso** lo decide l'applicazione; la funzione gira coi privilegi di chi la chiama.
* **Se** creare il contatto, quando in un form è facoltativo e l'utente l'ha lasciato vuoto, lo decide
  l'applicazione: il database decide **come** si scrive.
* **Le regole della tabella** scattano come per ogni scrittura: ruolo e istanza del soggetto, un contatto per
  tipo in ogni contesto, il soggetto e il reparto attivi, il predefinito del contesto.

---

{% include-markdown "it/dbzero/anagrafiche/_contatto-predefinito.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il doppione per tipo non ha un codice.** Un secondo contatto dello stesso tipo nello stesso contesto urta
  l'indice unico, e chi chiama riceve l'errore del database invece di un rifiuto col campo.
* **Un tipo di contatto che non è un numero** arriva come errore di conversione, non come `E_CONTATTO_INCOMPLETO`.
* **Un'istanza senza ruolo** è accettata: il contatto prende il contesto `istanza` e nessun indice ne limita i
  doppioni per tipo.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — soggetto mancante, o campi che non sono un oggetto.
* `E_CAMPO_NON_AMMESSO` — una chiave fuori elenco fra i campi, col suo nome.
* `E_CONTATTO_INCOMPLETO` — nominativo vuoto o tipo di contatto mancante, col campo.

Dai trigger della tabella arrivano `E_RUOLO_ALTRO_SOGGETTO` e `E_ISTANZA_ALTRO_SOGGETTO`.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-contatto-v1.sql` — la funzione che gira coi privilegi di chi chiama, il
  contatto di soggetto e quello di ruolo, la chiave assente al valore predefinito, il nominativo vuoto e il tipo
  mancante col loro campo, la chiave fuori elenco, il soggetto mancante, e i quattro verbi che non scrivono più la
  tabella a mano.

---

### Note di migrazione

* 2026-10-17 — nasce, e prende il posto degli inserimenti diretti nei verbi di nascita del soggetto, nella
  creazione degli utenti tecnici, nella fixture della società e nell'applicazione.

---

{% include-markdown "signature-core.md" %}
