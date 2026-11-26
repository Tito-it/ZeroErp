## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_soggetto_pf`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la riga che la funzione fa nascere
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — il contatto di default
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — i dati societari della ditta individuale
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che decide le regole
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) — la porta gemella, per società ed enti
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il contatto di default
> * [anagrafiche.fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari_alla_nascita) — quando scrivere i dati societari
> * [script.fn_stato_id_da_iso2](/dbzero/script/funzioni/fn_stato_id_da_iso2) — lo stato detto dal chiamante
> * [script.fn_stato_proposto_id](/dbzero/script/funzioni/fn_stato_proposto_id) — lo stato proposto, se il chiamante non lo dice
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore) — chi la usa per il soggetto dell'operatore
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il modello del soggetto

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_soggetto_pf` fa nascere un soggetto persona fisica (un privato o una ditta individuale) col
suo contatto di default e, per la ditta individuale, i suoi dati societari, in una chiamata sola. Restituisce
l'id del soggetto.

La usano l'applicazione, dal form anagrafico, la creazione dell'operatore e le fixture dei test. Non crea
indirizzi né ruoli.

---

### Che cosa pretende

* **Cognome, nome, codice fiscale e un'email**, non vuoti: l'email è quella del contatto di default.
* **La natura**, che deve essere una persona fisica. Una società o un ente qui sono un chiamante che ha
  sbagliato porta, e il rifiuto è tecnico: la porta giusta è `anagrafiche.fn_crea_soggetto_pg`.
* **La partita IVA** non la pretende la funzione: per la ditta individuale la pretende il guard della presenza.
* **Il sesso** passa così com'è, senza default: se la natura lo pretende e manca, lo rifiuta il guard del sesso.

---

### Lo stato

Lo stato detto dal chiamante, col codice ISO2, si cerca con `script.fn_stato_id_da_iso2`, che rifiuta un codice
con più stati; un codice che non indica nessuno stato è rifiutato dalla funzione. Senza codice, il soggetto
riceve lo stato proposto, che non ripiega mai su un valore scritto nel codice.

---

### Che cosa scrive

* **Il soggetto**, col codice fiscale e la partita IVA in maiuscolo e senza spazi ai lati (una partita IVA vuota
  diventa NULL), il comune di nascita e la riga attiva. Prima di scriverlo cerca il codice fiscale fra gli
  identificativi dello stesso stato, e se lo trova si ferma.
* **Il contatto di default**, con `anagrafiche.fn_crea_contatto`: il nominativo è cognome e nome, l'email quella
  ricevuta, il tipo quello indicato o, se manca, quello proposto da
  [script.fn_tipo_contatto_proposto_id](/dbzero/script/manual/fn_tipo_contatto_proposto_id) (il parametro
  `TIPO_CONTATTO_PROPOSTO`, con gli override per utente, azienda o per questa funzione).
* **I dati societari**, con `anagrafiche.fn_scrivi_dati_societari_alla_nascita`, lo stesso building block della
  porta delle società: se la natura li pretende, o se almeno un campo della sezione ha un valore (socio unico e
  liquidazione da soli non contano). Per una ditta individuale senza sezione non nasce nessuna riga; un privato
  con la sezione è rifiutato dal guard della natura, mai scartato in silenzio. Socio unico e liquidazione non
  passati li decidono i parametri del verbo.

Le regole del soggetto (presenza, formato e blocco di CF e P.IVA, sesso, regime PA) restano nei suoi trigger.

---

### ⭐ Il soggetto si completa nella stessa operazione

La funzione restituisce un soggetto che può essere ancora incompleto: gli indirizzi che la natura pretende li
crea il chiamante, e i guard differiti del soggetto li controllano alla conferma dell'operazione.

---

### ⚠️ Che cosa oggi non copre

* **Il controllo del codice fiscale già presente guarda il CF da solo.** L'identificativo di un soggetto con CF
  e P.IVA diversi è la coppia: il controllo non trova una ditta individuale che ha lo stesso codice fiscale.
  Una ditta individuale nuova con lo stesso CF e la stessa P.IVA di una esistente non la ferma il controllo, ma
  l'indice unico, con un errore tecnico al posto di `E_ADMIN_CF_DUPLICATO`; con lo stesso CF e una P.IVA
  diversa, o un privato col CF di una ditta, il soggetto nasce. Al contrario, una ditta individuale col CF di un
  privato esistente la ferma il controllo, anche se l'indice la ammetterebbe: la porta e l'indice non dicono la
  stessa regola.

---

### Codici errore

* `E_ADMIN_VALIDAZIONE` — cognome, nome, codice fiscale, email o natura mancanti, natura che non esiste. Il contesto nomina il parametro.
* `E_SOGGETTO_CREAZIONE_NATURA_ERRATA` — la natura non è una persona fisica.
* `E_STATO_ISO2_AMBIGUO` — il codice dello stato indica più stati.
* `E_CODICE` — il codice dello stato non indica nessuno stato.
* `E_CONFIG_MANCANTE`, `E_DEFAULT_ERRATO` — senza codice, lo stato proposto non è configurato o non esiste;
  senza tipo di contatto, lo stesso per il tipo proposto.
* `E_ADMIN_CF_DUPLICATO` — il codice fiscale è già l'identificativo di un soggetto dello stesso stato.

Dai trigger del soggetto e dei dati societari arrivano gli altri rifiuti, per esempio `E_PIVA_OBBLIGATORIA`,
`E_CF_NON_VALIDO`, `E_SESSO_OBBLIGATORIO`, `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-soggetto-pf.sql` — la nascita del privato col contatto di default e il
  comune di nascita, il codice fiscale già presente, il cognome vuoto, l'email mancante.
* `db/pgtap/anagrafiche/test-soggetti-sesso-policy-v1.sql` — il privato senza sesso rifiutato, la ditta
  individuale che nasce con la P.IVA e senza sesso, la natura mancante, la società alla porta sbagliata.
* `db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql` — la sezione della ditta individuale, una
  regola sola per le due porte.

---

### Note di migrazione

* 2026-10-09 — la natura la sceglie il chiamante (prima era il privato, fisso: una ditta individuale nasceva
  privato e senza partita IVA); il sesso perde il default `M`.
* 2026-10-17 — il contatto lo scrive `anagrafiche.fn_crea_contatto`.
* 2026-10-18 — lo stato non ripiega più sull'Italia: lo dice il chiamante, o lo stato proposto.
* 2026-10-20 — riceve i dati societari della ditta individuale, che prima il form mandava e la funzione perdeva.
* 2026-11-24 — il tipo di contatto non detto è quello proposto, non più il primo per id del catalogo
  (decisione D-T5-6 b di Tid).

---

{% include-markdown "signature-core.md" %}
