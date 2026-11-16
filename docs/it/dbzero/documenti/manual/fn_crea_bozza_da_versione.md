## 📘 Documentazione Concettuale – Funzione `documenti.fn_crea_bozza_da_versione`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la versione d'origine e la bozza nuova
>
> Approfondimento funzioni:
>
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — chi la usa per la copia di uno standard
> * [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione) — dove la bozza prende le sue date
> * [documenti.fn_template_motivo_non_coerente](/dbzero/documenti/funzioni/fn_template_motivo_non_coerente) — la regola «stesso documento» della destinazione
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni e personalizzazione

---

### 🎯 Scopo Principale

Copia una versione, in qualunque stato, in una **bozza nuova** di un modello, col numero successivo di
quel modello, e restituisce l'id della bozza. È la sede unica dei campi che una copia riprende.

---

### Che cosa si copia

* **Si copia**: titolo, formato, HTML, CSS, markdown, motore, formato e orientamento della pagina,
  margini, forma dei dati, schema del contesto, meta.
* **Non si copia**: lo stato (la copia nasce bozza), le date (si fissano alla pubblicazione), l'origine
  (`derivata_da_versione_id`, la dichiara chi chiama).
* **Si può sostituire**: titolo, date, attivo, meta. Senza sostituzione vale l'origine, per le date
  «senza data», e la copia nasce attiva.

Le date di una bozza non decidono niente: la pubblicazione riscrive inizio e fine.

---

### Chi la usa

* [fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard),
  che copia la versione dello standard nel modello nuovo dell'azienda e ne dichiara l'origine;
* il «clona versione» del backend, che copia una versione nello stesso modello, senza origine.

---

### Regole

* **La destinazione è un modello dello stesso documento** dell'origine: stessa sorgente e stesso
  tipo. Il corpo di una versione legge i dati di un documento preciso, e copiato nel modello di un
  altro documento leggerebbe dati che non ci sono. La regola è quella di
  [fn_template_motivo_non_coerente](/dbzero/documenti/funzioni/fn_template_motivo_non_coerente),
  la stessa con cui si giudica se un modello va bene per una stampa; l'azienda non c'entra, e il
  perimetro dell'azienda lo controlla chi chiama. Con l'origine dichiarata vale in più il guard
  dell'origine, che chiede uno standard d'origine e una copia che non lo è.
* **Il numero** è il massimo del modello di destinazione più uno. Se una copia concorrente sullo
  stesso modello prende quel numero prima, la copia non nasce e si riprova: la funzione traduce la
  violazione dell'unicità di (modello, numero) nel suo codice. Ogni altra violazione passa com'è.
* I guard della tabella restano in servizio sulla copia: sola lettura dello standard, origine
  coerente, ordine delle date. La copia nasce in bozza, quindi passa dal guard dello stato.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — versione d'origine o modello non indicati o non positivi, versione
  d'origine o modello di destinazione inesistenti.
* `E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO` (`TECNICO`) — la destinazione è il modello di un altro
  documento. Il clone del backend copia nello stesso modello e «personalizza» nel modello nuovo dello
  stesso documento: se arriva, è rotto il chiamante.
* `E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE` (`CONFLITTO_STATO`) — il numero l'ha preso, nello stesso
  momento, un'altra versione dello stesso modello; si riprova.

---

### Test

* `db/pgtap/documenti/test-documenti-personalizza-v1.sql` — la copia di uno standard riprende corpo
  e forma dei dati senza date; la copia nello stesso modello prende il numero successivo, il titolo
  sostituito e nessuna origine.
* `db/pgtap/documenti/test-documenti-pubblicazione-e-copia-v1.sql` — la copia nel modello di un altro
  tipo o di un'altra sorgente rifiutata; il modello inesistente e i parametri mancanti; la copia nello
  stesso modello col numero successivo; il vincolo che il verbo traduce esiste col nome che cerca. La
  gara vera sul numero non si costruisce in una sessione sola.

---

### Note di migrazione

* 2026-10-21 — nasce: l'elenco dei campi copiati e il numero della copia passano dal backend al
  database, perché «personalizza» ne aveva bisogno nel database.
* 2026-11-16 — controlla che la destinazione sia dello stesso documento (prima lo garantiva solo il
  servizio del clone) e che esista; il numero conteso ha un codice suo, al posto del 23505 grezzo.

---

{% include-markdown "signature-core.md" %}
