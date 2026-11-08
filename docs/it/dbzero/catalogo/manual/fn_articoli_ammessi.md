## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articoli_ammessi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — gli articoli fra cui si cerca
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_dettaglio](/dbzero/catalogo/views/vw_articoli_dettaglio) — le colonne dell'articolo che il chiamante unisce al risultato
>
> Approfondimento funzioni:
>
> * [script.fn_articolo_riga_contesto](/dbzero/script/funzioni/fn_articolo_riga_contesto) — il lato documento della regola, letto una volta
> * [script.fn_check_articolo_riga_su_contesto](/dbzero/script/funzioni/fn_check_articolo_riga_su_contesto) — il giudizio di ogni articolo su quel contesto
> * [script.fn_check_articolo_riga](/dbzero/script/funzioni/fn_check_articolo_riga) — la stessa regola, come la chiama il guard
> * [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/funzioni/trgfn_righe_guard_articolo_ammesso) — il guard che rifiuta con lo stesso motivo
> * [vendite.fn_listini_selezionabili](/dbzero/vendite/funzioni/fn_listini_selezionabili) — il picker gemello, per il listino del documento
>
> Guide:
>
> * [Uso di obsoleto](/guide/uso-di-obsoleto) — l'articolo ritirato fra gli esclusi

---

### 🎯 Scopo Principale

Il picker degli articoli di una riga: dato il documento e il testo cercato, restituisce gli
articoli trovati, ciascuno col primo motivo per cui il documento non lo ammette. Un motivo vuoto
vuol dire ammesso; prima vengono gli ammessi, poi gli esclusi, ciascun gruppo per codice.

⭐ Il motivo viene dalla stessa regola che il guard di riga applica quando la riga si salva.
Il picker non propone un articolo che poi viene rifiutato, e non nasconde un articolo che il
database accetterebbe.

---

### Un articolo escluso resta nell'elenco

Un articolo escluso esce col suo motivo: chi cerca un codice preciso e non lo vede fra gli
ammessi sa perché. Come mostrarlo (grigio con la spiegazione, oppure solo quando non ci sono
ammessi) lo decide l'interfaccia.

Il picker propone una scelta nuova: un articolo ritirato (`obsoleto_dal` di oggi o passato) esce fra gli
esclusi col motivo `E_ARTICOLO_OBSOLETO`, lo stesso che il guard solleva su una riga nuova.

---

### I documenti

| Documento | Le righe | Che cosa serve |
| --- | --- | --- |
| `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA` | le righe del documento | l'id della testata |
| `OFFERTA_COMMERCIALE`, `CONTRATTO` | le eccezioni al listino | l'id e il tipo d'eccezione (`AGGIUNTA`, `OVERRIDE`, `ESCLUSIONE`) |
| `LISTINO_VERSIONE` | le righe di una versione di listino | l'id della versione |
| `ARTICOLO` | i componenti di una distinta | l'articolo padre |
| `PROMO_ARTICOLO` | l'articolo di una promo | niente: la regola dipende solo dall'articolo |

Le righe ricevono l'id del documento salvato, non i valori del form: il guard giudica la riga
contro la testata salvata, e il picker deve fare la stessa domanda. La testata nasce sempre
prima delle righe, quindi l'id c'è.

---

### Che cosa propone

* Solo articoli attivi: ogni riga pretende un articolo attivo.
* La ricerca è un «contiene» sul codice o sulla descrizione, senza distinzione fra maiuscole e
  minuscole. Il testo è letterale: `%` e `_` non fanno da jolly. Un testo vuoto trova tutti.
* Il tetto lo sceglie il chiamante, e vuoto vuol dire nessun tetto. Si applica dopo aver
  giudicato tutti gli articoli trovati, perché «prima gli ammessi» non si decide sui soli
  primi.
* `ordine` è la posizione nell'elenco: chi unisce altre colonne dell'articolo ordina su questa.
* Nella versione di listino un composito esce col motivo `COMPOSITO_COME_BUNDLE`: come riga
  semplice è rifiutato, ma nella versione entra come bundle, coi prezzi dei componenti.
  L'interfaccia lo propone per quella strada.

---

### Come lavora

La regola è divisa in due metà:

1. `script.fn_articolo_riga_contesto` legge una volta il lato documento (il listino in vigore e
   la sua versione espansa, la tipologia del listino, il padre della distinta) e valida i
   parametri;
2. `script.fn_check_articolo_riga_su_contesto` giudica ogni articolo trovato su quel contesto.

Il guard usa le stesse due metà attraverso `script.fn_check_articolo_riga`. Leggere il documento
una volta sola rende il picker abbastanza veloce da girare a ogni tasto premuto.

Il picker giudica l'articolo. I motivi che dipendono da altri valori della riga, come
l'erogazione e la fonte della quantità di un'offerta, si giudicano quando la riga si salva.

La funzione è SECURITY INVOKER: il documento si legge con i permessi dell'operatore, come lo
legge il guard.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — manca l'id per un documento con testata; il tetto è minore di uno;
  manca il tipo d'eccezione per offerta e contratto; manca il padre per la distinta.
* `E_DOC_TIPO_NON_GESTITO` — il documento non è fra quelli della tabella sopra.

Il motivo di un articolo escluso non è un errore: è un oggetto con il codice, la ragione, la
chiave di traduzione, il dettaglio e i valori del messaggio.

---

### Test

* `db/pgtap/catalogo/test-articoli-ammessi-picker-v1.sql` — su documenti e articoli costruiti, il
  picker e il guard danno lo stesso motivo; gli ammessi vengono prima; il composito nella
  versione di listino, il kit senza componenti, il solo componente, l'articolo spento e la promo.
* `db/pgtap/script/test-ammissione-articoli-onere-righe-v1.sql` — sull'ordine il picker ammette
  la merce e l'onere, non il servizio.

---

### Note di migrazione

* 2026-10-14 — nasce (brief-db-articoli-ammessi-per-documento).
* 2026-11-06 — l'articolo ritirato esce fra gli esclusi (brief-db-articoli-obsoleto-dal).

---

{% include-markdown "signature-core.md" %}
