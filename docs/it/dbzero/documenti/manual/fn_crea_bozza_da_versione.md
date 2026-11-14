## 📘 Documentazione Concettuale – Funzione `documenti.fn_crea_bozza_da_versione`

> **Ultimo aggiornamento**: 14 novembre 2026
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

* Il numero è il massimo del modello di destinazione più uno. Due chiamate concorrenti sullo stesso
  modello calcolano lo stesso numero, e la seconda viola l'unicità di (modello, numero).
* I guard della tabella restano in servizio sulla copia: sola lettura dello standard, origine
  coerente, ordine delle date.
* La funzione non verifica che origine e destinazione siano dello stesso tipo di documento e della
  stessa sorgente: lo fa il guard dell'origine solo quando l'origine è dichiarata. Il perimetro
  dell'azienda lo controlla chi chiama.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — versione d'origine o modello non indicati o non positivi, versione
  d'origine inesistente. Un modello di destinazione inesistente arriva come violazione della FK.

---

### Test

* `db/pgtap/documenti/test-documenti-personalizza-v1.sql` — la copia di uno standard riprende corpo
  e forma dei dati senza date; la copia nello stesso modello prende il numero successivo, il titolo
  sostituito e nessuna origine.

---

### Note di migrazione

* 2026-10-21 — nasce: l'elenco dei campi copiati e il numero della copia passano dal backend al
  database, perché «personalizza» ne aveva bisogno nel database.

---

{% include-markdown "signature-core.md" %}
