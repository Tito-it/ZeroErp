## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_scrivi_dati_societari_alla_nascita`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga che nasce, o no
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — il verbo a cui passa la sezione
> * [anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) — la nascita di una società o di un ente
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — la nascita di una persona fisica

---

### 🎯 Scopo Principale

`anagrafiche.fn_scrivi_dati_societari_alla_nascita` decide, quando nasce un soggetto, se i suoi dati societari
vanno scritti, e li scrive col verbo `anagrafiche.fn_scrivi_dati_societari`. Restituisce l'id della riga, o
`NULL` se non c'era niente da scrivere.

La chiamano le due porte di creazione, `anagrafiche.fn_crea_soggetto_pg` e `anagrafiche.fn_crea_soggetto_pf`:
la decisione ha una sede sola, e una ditta individuale, che nasce come persona fisica, ha la sua sezione come
una società. Soggetto e dati societari nascono nella stessa chiamata, o non nasce nessuno dei due.

---

### Quando la sezione si scrive

* **La natura la pretende** (la società di capitali): si scrive sempre, anche vuota. Una sezione senza forma è
  allora rifiutata dal vincolo `NOT NULL` della forma.
* **Altrimenti, se la sezione c'è**: almeno un campo ha un valore fra forma, provincia e numero REA, capitale,
  canale, PEC, codice SDI e data di costituzione. Un testo di soli spazi non conta.
* **Socio unico e liquidazione da soli non contano**: hanno sempre un valore, perché il verbo li riempie dai
  parametri, e il form li manda anche quando la sezione è vuota.

---

### ⛔ Una sezione non ammessa si rifiuta, non si scarta

Una sezione passata per una natura che non la ammette (il privato) arriva al verbo, e la rifiuta uno dei
guard della tabella. Il codice dipende da che cosa la sezione contiene, perché i guard parlano in ordine: un
canale senza recapito parla per primo, una forma parla coi rifiuti della forma (di norma quella non ammessa
dalla natura, `E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO`), e solo una sezione senza forma la ferma il guard della
natura (`E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO`). In nessun caso il soggetto nasce perdendo in silenzio i dati
che l'utente ha scritto.

La funzione non aggiunge regole: forma, REA, capitale e canale stanno nei trigger della tabella. Gira coi
privilegi di chi chiama: la porta di scrittura resta il verbo.

---

### ⚠️ Che cosa oggi non copre

* **Una società di capitali creata senza forma** riceve l'errore grezzo del vincolo `NOT NULL`, senza un
  codice del catalogo né il campo da compilare.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il soggetto non è passato.
* `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` — il soggetto passato non esiste.

Gli altri rifiuti vengono dal verbo e dai trigger della tabella.

---

### Test

* `db/pgtap/anagrafiche/test-dati-societari-alla-nascita-v1.sql` — le due porte chiamano la funzione e nessuna
  il verbo; una SRL con la data di costituzione; un ente coi soli socio unico e liquidazione, senza riga; la
  ditta individuale con e senza sezione; il canale senza codice, che non fa nascere nemmeno il soggetto; la
  sezione senza forma; il privato con la sola data, rifiutato.

---

### Note di migrazione

* 2026-10-20 — nasce. Prima la decisione stava nella sola porta delle società: la ditta individuale perdeva la
  sezione in creazione, e la data di costituzione si perdeva per tutti.

---

{% include-markdown "it/dbzero/anagrafiche/_dati-societari.md" %}

---

{% include-markdown "signature-core.md" %}
