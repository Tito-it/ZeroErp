## 📘 Documentazione Concettuale – `script.fn_doc_terminali_con_uscita_manuale` e il suo trigger

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) — dove stanno vocabolario e matrice di una testata
> [config.stati_doc_offerte](/dbzero/config/manual/stati_doc_offerte) · [config.stati_doc_reso](/dbzero/config/manual/stati_doc_reso) · [config.stati_doc_ddt](/dbzero/config/manual/stati_doc_ddt) — i vocabolari che dichiarano `terminale`

---

### 🎯 Che cosa vuol dire `terminale`

Uno stato è **terminale** quando da lì non esce nessun passaggio **a mano**: l'operatore non ha più
niente da fare sul documento. Il sistema può ancora spostarlo con un passaggio di processo, come la
revisione annullata che riporta emessa l'offerta precedente. Per questo chi legge `terminale` lo
rilegge ogni volta, e non lo copia.

È un'implicazione, non un'equivalenza. Uno stato senza uscite a mano può non essere terminale:
l'ordine parzialmente evaso, per esempio, non ha bottoni di stato, ma restano le bolle da fare.

### ⚙️ I due pezzi

* **`script.fn_doc_terminali_con_uscita_manuale(testata)`** risponde con le coppie *(stato terminale,
  destinazione)* per cui la matrice della testata ha un passaggio a mano attivo che esce da uno
  stato terminale. Nessuna riga vuol dire che la configurazione è giusta. Un passaggio spento non
  conta. Una testata il cui vocabolario non ha `terminale` (la fattura, la commessa) è una chiamata
  sbagliata.
* **`script.trgfn_doc_terminale_senza_uscita_manuale`** è il trigger che fa rispettare la regola. È
  montato sui sette vocabolari che hanno `terminale` (preventivo, offerta, contratto, ordine, bolla,
  reso, versione di listino) e sulle loro matrici, e ha un solo argomento: la testata. Se trova una
  coppia solleva `E_DOC_TERMINALE_CON_USCITA_MANUALE`.

### ⚠️ Perché è un trigger differito

Vocabolario e matrice sono due metà della stessa regola, e si scrivono in istruzioni diverse: si può
spegnere un passaggio e poi dichiarare lo stato terminale, o fare il contrario. Il trigger è
**differito** (`DEFERRABLE INITIALLY DEFERRED`) e giudica la configurazione a transazione finita,
quindi l'ordine delle scritture non conta. Nei pgTAP, che girano con `SET CONSTRAINTS ALL IMMEDIATE`,
scatta a fine istruzione.

L'errore lo incontra solo chi scrive la configurazione, cioè le migrazioni e i seed: non è un errore
dell'operatore.

### 🧪 Verifica

`db/pgtap/config/test-terminale-senza-uscita-manuale-v1.sql`. Costruisce i casi sulla matrice vera del
reso: un passaggio a mano da uno stato terminale, poi lo stesso di processo, spento e riacceso; uno
stato con l'annullo a mano dichiarato terminale. Controlla anche che la configurazione dei sette
documenti rispetti la regola, la forma dei montaggi, e il lettore: un'offerta superata è terminale, e
torna emessa quando la sua revisione si annulla.
