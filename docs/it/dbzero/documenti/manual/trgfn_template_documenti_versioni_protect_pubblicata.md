## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_documenti_versioni_protect_pubblicata`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la tabella protetta
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — le stampe che rileggono la versione
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — anche un'obsoleta stampa, fino alla sua fine
>
> Approfondimento funzioni:
>
> * [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione) — l'unica che chiude una versione pubblicata
> * [documenti.trgfn_template_documenti_versioni_block_delete](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_block_delete) — quali versioni si cancellano
> * [documenti.trgfn_template_documenti_versioni_guard_derivata_da](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_guard_derivata_da) — l'origine di una copia, che ha il suo guard
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni e stati

---

### 🎯 Scopo Principale

Rende **immutabile una versione fuori bozza**, pubblicata o obsoleta: il contenuto, la pagina, le
date, la forma dei dati, il modello, il numero e lo stato restano quelli della pubblicazione. È
montata `BEFORE UPDATE OF` quelle colonne su `documenti.template_documenti_versioni`.

---

### ⛔ Fuori bozza non cambia niente, nemmeno lo stato

Una versione fuori bozza è il contenuto con cui si è stampato. Se cambiasse, le stampe che la citano
avrebbero un'impronta del template non più verificabile, e la ristampa fedele produrrebbe un
documento diverso. Vale anche per una versione superata: un'obsoleta stampa fino all'ultimo giorno
della sua validità, e la ristampa la rilegge.

Lo stato fa parte dell'elenco: fuori bozza non torna indietro. Senza questa regola, riportare una
versione pubblicata in bozza la renderebbe di nuovo modificabile in tutto. La forma dei dati ne fa
parte perché la controlla la pubblicazione: cambiarla dopo aggirerebbe il controllo.

Fuori dall'elenco: `titolo`, `meta`, `attivo`, l'origine della copia (ha il suo guard) e le colonne
d'audit. Per cambiare il layout si crea una bozza nuova e la si pubblica.

Il trigger scatta anche quando la colonna è riscritta con lo stesso valore: un salvataggio che
riscrive tutta la riga di una versione fuori bozza è rifiutato. Nessun altro trigger `BEFORE` della
tabella scrive queste colonne, quindi la forma `UPDATE OF` è sicura.

---

### Un'eccezione sola: la chiusura fatta dalla pubblicazione

Quando [fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione)
pubblica una versione, chiude quelle che la nuova supera. È l'unica scrittura ammessa su una versione
fuori bozza, e passa solo se valgono tutte insieme:

* la porta `zeroerp.allow_template_versione_chiusura_override` è aperta;
* lo stato va da `PUBBLICATA` a `OBSOLETA`;
* la data di fine diventa una data, uguale o precedente a quella di prima: la validità si accorcia;
* ogni altra colonna protetta resta com'era.

La funzione apre la porta solo per la scrittura di chiusura, nella transazione, e la richiude subito.
Anche aperta, la porta ammette solo quella forma: un UPDATE che a porta aperta cambia anche il
corpo è rifiutato. Una versione già obsoleta non si chiude di nuovo.

⚠️ La porta protegge da un backend che sbaglia, non da uno manomesso: chi apre la porta a mano può
accorciare una versione pubblicata, ma non modificarla.

---

### Codici errore

* `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` — ogni modifica di una colonna protetta su una
  versione fuori bozza, fuori dalla forma della chiusura. Il contesto porta modello, numero, lo stato
  di prima e quello chiesto.

---

### Test

* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — un'obsoleta non si
  modifica e non torna in bozza; una pubblicata non torna in bozza; la porta è richiusa dopo la
  pubblicazione; senza porta una pubblicata non si chiude a mano; a porta aperta passa solo la
  chiusura; la pubblicazione chiude come deve.
* `db/pgtap/documenti/test-documenti-template-versioni.sql` — corpo, data di inizio e forma dei dati
  di una pubblicata non cambiano; `meta` sì.

---

### Note di migrazione

* 2026-05-01 — nasce il guard, sulle sole versioni pubblicate.
* 2026-09-30 — la forma dei dati entra fra le colonne protette.
* 2026-11-14 — protegge anche le obsolete, e lo stato entra nell'elenco: fino ad allora un UPDATE
  del solo stato riportava una pubblicata in bozza. La chiusura della pubblicazione diventa una
  scrittura sola, a porta aperta.

---

{% include-markdown "signature-core.md" %}
