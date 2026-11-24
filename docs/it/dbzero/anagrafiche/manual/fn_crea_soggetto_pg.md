## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_soggetto_pg`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la riga che la funzione fa nascere
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — il contatto di default
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — i dati societari
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che decide le regole
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — la porta gemella, per le persone fisiche
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il contatto di default
> * [anagrafiche.fn_scrivi_dati_societari_alla_nascita](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari_alla_nascita) — quando scrivere i dati societari
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — il verbo che li scrive
> * [script.fn_stato_id_da_iso2](/dbzero/script/funzioni/fn_stato_id_da_iso2) — lo stato detto dal chiamante
> * [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo) — i ruoli, che la funzione non assegna
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il modello del soggetto

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_soggetto_pg` fa nascere un soggetto società o ente col suo contatto di default e, se vanno
scritti, i suoi dati societari, in una chiamata sola. Restituisce l'id del soggetto.

Nel database la chiamano il provisioning dei dati di sviluppo e le fixture dei test. Non crea indirizzi né ruoli.

---

### Che cosa pretende

* **La ragione sociale e un'email**, non vuote: l'email è quella del contatto di default.
* **La natura**, che deve esistere e non essere una persona fisica. Un privato o una ditta individuale qui sono un
  chiamante che ha sbagliato porta, e il rifiuto è tecnico: la porta giusta è `anagrafiche.fn_crea_soggetto_pf`,
  che riceve nome, cognome e sesso.
* **Codice fiscale e partita IVA** non li pretende la funzione: li pretende, secondo la natura, il guard della
  presenza. Il sesso non si scrive: società ed enti non lo indicano.

---

### Lo stato

Come nella porta delle persone fisiche: lo stato detto dal chiamante col codice ISO2, cercato con
`script.fn_stato_id_da_iso2`, o, senza codice, lo stato proposto, che non ripiega mai.

---

### Che cosa scrive

* **Il soggetto**, con la ragione sociale senza spazi ai lati, il codice fiscale e la partita IVA in maiuscolo e
  senza spazi (un valore vuoto diventa NULL) e la riga attiva. Prima di scriverlo cerca il codice fiscale e la
  partita IVA, ognuno per conto suo, fra gli identificativi dello stesso stato, e se li trova si ferma.
* **Il contatto di default**, con `anagrafiche.fn_crea_contatto`: il nominativo è la ragione sociale, l'email
  quella ricevuta, il tipo quello indicato o, se manca, quello proposto da
  [script.fn_tipo_contatto_proposto_id](/dbzero/script/manual/fn_tipo_contatto_proposto_id) (il parametro
  `TIPO_CONTATTO_PROPOSTO`, con gli override per utente, azienda o per questa funzione).
* **I dati societari**, con `anagrafiche.fn_scrivi_dati_societari_alla_nascita`, lo stesso building block della
  porta delle persone fisiche: se la natura li pretende, o se almeno un campo della sezione ha un valore (socio
  unico e liquidazione da soli non contano). Una sezione passata a una natura che non la ammette la rifiuta il
  guard della natura. La scrittura la fa il verbo `anagrafiche.fn_scrivi_dati_societari`, e le regole restano nei
  trigger della tabella.

Il significato dei campi della sezione sta nella scheda dei dati societari. Due cose che dipendono da chi
chiama: socio unico e liquidazione non passati li decidono i parametri del verbo; REA e capitale li pretende la
forma giuridica, PEC o codice SDI il canale della fattura elettronica; PEC e codice SDI non sono unici fra i
soggetti.
`ragione_sociale_completa` non la scrive nessuno: è una colonna generata.

---

### ⭐ Il soggetto si completa nella stessa operazione

La funzione restituisce un soggetto che può essere ancora incompleto: gli indirizzi che la natura pretende li
crea il chiamante, e i guard differiti del soggetto li controllano alla conferma dell'operazione, insieme ai dati
societari che la natura pretende.

---

### ⚠️ Che cosa oggi non copre

* **Il controllo dell'identificativo già presente guarda CF e P.IVA uno alla volta.** Quando i due sono diversi
  l'identificativo è la coppia, e il controllo non lo trova: un soggetto nuovo con lo stesso CF e la stessa P.IVA
  di uno esistente lo ferma l'indice unico, con un errore tecnico al posto di `E_ADMIN_CF_DUPLICATO`; uno con la
  sola P.IVA di un soggetto che ha anche un CF diverso nasce accanto a lui.

---

### Codici errore

* `E_ADMIN_VALIDAZIONE` — ragione sociale, natura o email mancanti, natura che non esiste.
* `E_SOGGETTO_CREAZIONE_NATURA_ERRATA` — la natura è una persona fisica.
* `E_STATO_ISO2_AMBIGUO` — il codice dello stato indica più stati.
* `E_CODICE` — il codice dello stato non indica nessuno stato.
* `E_CONFIG_MANCANTE`, `E_DEFAULT_ERRATO` — senza codice, lo stato proposto non è configurato o non esiste;
  senza tipo di contatto, lo stesso per il tipo proposto.
* `E_ADMIN_CF_DUPLICATO`, `E_ADMIN_PIVA_DUPLICATA` — il codice fiscale, o la partita IVA, è già l'identificativo
  di un soggetto dello stesso stato.

Dai trigger del soggetto e dei dati societari arrivano gli altri rifiuti, per esempio `E_PIVA_OBBLIGATORIA`,
`E_PIVA_NON_VALIDA`, `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`.

---

### Test

* `db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql` — la data di costituzione della società, l'ente
  con i soli socio unico e liquidazione che nasce senza riga, una regola sola per le due porte.
* `db/pgtap/anagrafiche/test-soggetti-sesso-policy-v1.sql` — la società che nasce senza sesso, il privato alla
  porta sbagliata.
* `db/pgtap/anagrafiche/test-fn-pgtap-crea-soggetto-pg-v1.sql` — la fixture che passa da questa funzione: il
  contatto di default e i dati societari della natura che li pretende.

---

### Note di migrazione

* 2026-10-09 — una persona fisica non passa più da qui: una ditta individuale nasceva con la sola ragione
  sociale.
* 2026-10-11 — i dati societari li scrive il verbo, e le regole restano nei trigger della tabella.
* 2026-10-18 — lo stato non ripiega più sull'Italia: lo dice il chiamante, o lo stato proposto.
* 2026-10-20 — riceve la data di costituzione, che prima si perdeva; quando scrivere i dati societari lo decide il
  building block condiviso con la porta delle persone fisiche, e una sezione passata a una natura che non la
  ammette non si scarta più in silenzio.
* 2026-11-24 — il tipo di contatto non detto è quello proposto, non più il primo per id del catalogo
  (decisione D-T5-6 b di Tid).

---

{% include-markdown "signature-core.md" %}
