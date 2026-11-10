## 📘 Documentazione Concettuale – Funzione `vendite.fn_prezzi_legame_oltre_la_fine`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti) — i prezzi bundle
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami della distinta
>
> Approfondimento funzioni:
>
> * [catalogo.fn_chiudi_legame_distinta](/dbzero/catalogo/funzioni/fn_chiudi_legame_distinta) — il verbo che chiude legame e prezzi
> * [script.fn_check_legame_distinta_chiudibile](/dbzero/script/funzioni/fn_check_legame_distinta_chiudibile) — i motivi che vietano, letti da qui
> * [script.fn_scope_ef_whitelist_via_listino_versione](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_listino_versione) — il perimetro, la regola della policy delle righe

---

### 🎯 Scopo Principale

Dice **quali prezzi bundle di un legame di distinta vanno oltre una data di fine**, cioè quelli che una chiusura del
legame a quella data tocca, e che cosa ne fa la chiusura. Lo leggono la check e il guard della distinta, il verbo
di chiusura e la finestra di conferma.

Un prezzo bundle sta dentro il periodo del suo legame (chiave esterna temporale): chiudendo il legame, ogni prezzo
che resta aperto oltre la fine va chiuso o tolto.

---

### Le colonne

* Il prezzo: riga, versione, listino (id e codice), codice della versione, stato della versione, inizio, fine,
  prezzo, attivo. Escono anche i prezzi spenti: anche loro stanno dentro il legame.
* `importo_per_kit`: prezzo per il coefficiente del legame, cioè quanto il componente pesa sul prezzo di un kit in
  quella versione (il prezzo del kit è la somma dei suoi componenti).
* `esito`:
  * `CHIUDE` — il prezzo comincia entro la fine, e ne prende la stessa fine;
  * `TOGLIE` — comincia dopo la fine, in una versione in bozza: si cancella;
  * `BLOCCA` — comincia dopo la fine, in una versione non in bozza: non si accorcia (il periodo resterebbe vuoto) e
    non si cancella. La fine del legame deve arrivare almeno al suo inizio.
* `nel_perimetro`: il prezzo sta nel perimetro di chi chiama.

Con la data vuota non esce nessuna riga.

---

### ⭐ I prezzi che chi chiama non vede

La distinta è comune a tutte le aziende, i listini no: ogni listino ha la sua azienda, e la row level security
mostra a ciascuno solo i suoi. Chi chiude un legame deve però sapere che ci sono prezzi che non vede, perché la
chiusura li toccherebbe.

Per questo la funzione è `SECURITY DEFINER` e legge tutti i prezzi, ma di quelli fuori dal perimetro restituisce
solo che esistono e il loro esito: `nel_perimetro = false`, e tutte le altre colonne vuote. Il perimetro è la regola
della policy delle righe, `script.fn_scope_ef_whitelist_via_listino_versione`. L'ordine mette prima le righe nel
perimetro.

---

### Come legge

`LANGUAGE sql` con corpo `BEGIN ATOMIC`, `STABLE`, `search_path` bloccato, `EXECUTE` solo all'applicazione.

---

### Test

* `db/pgtap/catalogo/test-chiudi-legame-con-prezzi-v1.sql` — i tre esiti, il prezzo di un'altra azienda che esce
  senza dati.

---

### Note di migrazione

* 2026-11-09 — nasce con il verbo di chiusura del legame (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
