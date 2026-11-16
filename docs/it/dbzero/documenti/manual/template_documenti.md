## 📘 Documentazione Concettuale – Tabella `documenti.template_documenti`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — le versioni del modello, con il contenuto da stampare
> * [documenti.tipi_documento_output](/dbzero/documenti/tabelle/tipi_documento_output) — che cosa il modello produce
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il documento da cui si stampa
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'azienda a cui il modello appartiene
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — le stampe fatte con il modello
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda che può indicare un modello
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — quali modelli stampano oggi
> * [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto) — quanto una copia è rimasta indietro rispetto allo standard
>
> Approfondimento funzioni:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — con quale modello si stampa
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — la copia di uno standard per un'azienda
> * [documenti.trgfn_template_standard_guard_sola_lettura](/dbzero/documenti/funzioni/trgfn_template_standard_guard_sola_lettura) — lo standard in sola lettura per l'applicazione
> * [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — l'azienda presa dalla sessione
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — modelli, versioni, standard e personalizzazione

---

### 🎯 Scopo Principale

`documenti.template_documenti` è il **modello di stampa**: dice che cosa si produce (il tipo di
documento), da quale documento (la sorgente) e per quale azienda. Il contenuto da stampare non sta
qui, ma nelle sue versioni.

Il modello porta anche il contratto con il backend: `context_builder_code` nomina chi prepara i dati
per la stampa, `file_name_pattern` il nome del file prodotto.

---

### Un modello è di un'azienda, oppure è standard

* Il **modello di un'azienda** ha `emittente_fiscale_id` valorizzato e vale solo per i documenti di
  quell'azienda. Se chi lo crea non indica l'azienda, la prende dalla sessione.
* Il **modello standard** (`standard = true`) è del sistema: non ha azienda e vale per tutte.
  Lo standard, e solo lo standard, non ha azienda (`chk_template_documenti_standard_senza_emittente`).
* `standard` non cambia dopo la nascita (lock di colonna, `E_COLONNA_NON_MODIFICABILE`): un modello
  d'azienda non diventa standard, e viceversa.

Lo standard fa da ripiego: un'azienda che non ha nessun modello suo capace di stampare per quel
documento stampa con lo standard. Se ne ha, vale il suo predefinito, e senza predefinito la stampa
si ferma invece di ripiegare. La regola sta tutta in
[fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile).

---

### ⛔ Lo standard non si scrive dall'applicazione

Uno standard e le sue versioni li scrivono solo il seed e i changeSet, cioè il proprietario della
tabella. L'applicazione li legge: un INSERT, un UPDATE o un DELETE su uno standard, o su una sua
versione, è rifiutato con `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`. Chi vuole un modello diverso
lo **personalizza**: crea il modello della sua azienda partendo dalla versione con cui lo standard
stampa oggi ([fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard)).

Per la stessa ragione un'evoluzione del modello ha una sede sola: i changeSet scrivono sullo
standard, trovato per tipo, sorgente e codice interno, e non sulle copie delle aziende. Quanto una
copia è rimasta indietro lo dice
[vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto).

---

### Le chiavi: codice e codice interno, per azienda e sorgente

* `codice_interno` è l'identità tecnica stabile e non si modifica; `codice` è quello leggibile.
  Tutti e due si scrivono in maiuscolo.
* Codice e codice interno sono unici per azienda e sorgente. L'unicità tratta l'azienda vuota come
  un valore: fra gli standard, codice e codice interno sono unici per sorgente. Uno standard e la
  copia di un'azienda possono avere lo stesso codice interno.
* Per ogni azienda, tipo di documento e sorgente c'è **al più un predefinito attivo**, e uno solo
  anche fra gli standard.
* `uq_template_documenti_id_tipo_sorgente` non restringe niente (contiene la chiave primaria): è il
  bersaglio della FK con cui la coda di stampa delle fatture lega il modello indicato al tipo e alla
  sorgente della sua riga.

---

### Attivo e spento

Un modello spento non stampa e non conta nella risoluzione: spegnere i propri modelli di un tipo
riporta l'azienda allo standard. Un modello si spegne solo se non ha versioni attive (i trigger
generati del framework ATTIVO). Le stampe non lo tengono acceso: sono storia, e la loro chiave verso
il modello è un'eccezione della regola (`dbops.automazione_attivo_eccezioni`). Per accendere un
modello servono attivi il suo tipo di documento, la sua sorgente e la sua azienda.

---

### Codici errore

* `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA` — scrittura dall'applicazione su uno standard.
* `E_COLONNA_NON_MODIFICABILE` — cambio di `standard`; `E_CODICE_NON_MODIFICABILE` — cambio di
  `codice_interno`.
* Le unicità (codice, codice interno, predefinito) arrivano come violazione di vincolo, e il backend
  le traduce per nome.

---

### Test

* `db/pgtap/documenti/test-documenti-template-documenti.sql` — le unicità, il predefinito unico, il
  lock.
* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — forma dello standard, unicità fra
  gli standard, lock di `standard`, risoluzione.
* `db/pgtap/documenti/test-documenti-template-standard-app-v1.sql` — lo standard in sola lettura
  per l'applicazione.

---

### Note di migrazione

* 2026-04-29 — nasce la tabella.
* 2026-10-20 — nasce il modello standard: la colonna `standard`, il CHECK con l'azienda, le unicità
  che trattano l'azienda vuota come un valore, il guard di sola lettura.

---

{% include-markdown "signature-core.md" %}
