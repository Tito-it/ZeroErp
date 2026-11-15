## 📘 Documentazione Concettuale – Funzione `documenti.fn_personalizza_template_standard`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — lo standard e il modello nuovo
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la bozza copiata e la sua origine
>
> Approfondimento viste:
>
> * [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto) — quanto la copia resta indietro nel tempo
>
> Approfondimento funzioni:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la versione con cui lo standard stampa oggi
> * [documenti.fn_crea_bozza_da_versione](/dbzero/documenti/funzioni/fn_crea_bozza_da_versione) — la copia della versione
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — il modello standard e «personalizza»

---

### 🎯 Scopo Principale

**«Personalizza»**: crea il modello di un'azienda a partire da uno standard, con una bozza copiata
dalla versione con cui lo standard stampa oggi, in un'operazione sola. Restituisce l'id del modello
nuovo.

---

### Che cosa fa

1. Controlla che il modello indicato esista e sia uno standard.
2. Chiede alla porta unica della risoluzione, col modello indicato, la **versione con cui lo standard
   stampa oggi**. Uno standard spento, o senza una versione che stampa oggi, non si personalizza.
3. Crea il modello dell'azienda con tipo, sorgente, builder e nome del file dello standard; codice,
   codice interno e descrizione dello standard, se non indicati.
4. Crea la bozza 1, copiata da quella versione, con l'origine dichiarata.

È una funzione madre: tutto o niente. Dopo un rifiuto non resta il modello senza bozza.

Finché la copia è in bozza non stampa, e l'azienda continua con lo standard.

---

### Il flag predefinito

La copia nasce predefinita se l'azienda non ha già un suo predefinito attivo per quel documento;
altrimenti no, e scegliere fra i due resta all'operatore. Chi chiama può imporlo: imposto vero
accanto a un predefinito già attivo, risponde l'unicità del predefinito.

---

### Il perimetro dell'azienda lo controlla chi chiama

La funzione non verifica che chi chiama possa lavorare per quell'azienda: lo fa il backend, come per
ogni modello d'azienda, perché le tabelle dei modelli non hanno sicurezza di riga. L'azienda deve
essere attiva.

---

### Codici errore

* `E_DOCUMENTI_PERSONALIZZA_NON_STANDARD` — il modello indicato è già di un'azienda.
* `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE` — lo standard oggi non stampa (spento, nessuna versione che
  stampa oggi); lo solleva la risoluzione.
* `E_PARAMETRO_INVALIDO` — modello o azienda non indicati o non positivi, modello inesistente.
* Un codice già dell'azienda per la sorgente, o un secondo predefinito imposto, arrivano come
  violazione di unicità.

---

### Test

* `db/pgtap/documenti/test-documenti-personalizza-v1.sql` — la copia è dell'azienda e nasce
  predefinita; la bozza deriva dalla versione che stampa oggi, non da una pubblicata futura; con la
  sola bozza si stampa ancora con lo standard, pubblicata si stampa con la copia; accanto a un
  predefinito nasce non predefinita; da un modello non standard, da uno standard spento, con un codice
  già usato è rifiutata, e il rifiuto non lascia la testata.

---

### Note di migrazione

* 2026-10-21 — nasce: prima lo faceva il backend, scegliendo come origine la pubblicata col numero
  più alto, che non sempre è quella che stampa oggi.

---

{% include-markdown "signature-core.md" %}
