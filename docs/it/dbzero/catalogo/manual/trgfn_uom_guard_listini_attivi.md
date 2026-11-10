## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_uom_guard_listini_attivi`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [vendite.fn_listini_attivi_uom_non_convertibili](/dbzero/vendite/funzioni/fn_listini_attivi_uom_non_convertibili) — i prezzi che resterebbero scoperti
> * [catalogo.trgfn_uom_guard_storia](/dbzero/catalogo/funzioni/trgfn_uom_guard_storia) — la storia della stessa riga
> * [vendite.trgfn_listini_righe_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_uom_periodo) — la stessa regola, dal lato della riga

---

### 🎯 Scopo Principale

Una mappatura o una conversione generale **non si chiude, non si spegne e non si toglie** se lascia
un prezzo di un listino attivo in un'unità che, in un giorno del periodo, non si converte più.

---

### Il terzo lato

La regola «l'unità vale per tutto il periodo della versione» si rompe da tre lati: la riga scritta,
il periodo allungato, il catalogo che cambia sotto. Questo è il terzo. Tid ha scelto il rifiuto: la
riga di listino non ha un periodo suo, e «sistemarla» vorrebbe dire chiudere la versione intera.
Il rimedio è chiudere prima quelle versioni.

---

### A fine transazione

È un constraint trigger differito: «chiudi e inserisci» chiude la riga vecchia e apre la nuova, e
un giudizio immediato rifiuterebbe la chiusura prima che la nuova esista. Contano solo le versioni
ATTIVE: una bozza la ferma l'attivazione.

---

### Le altre aziende

Il catalogo è di tutte le aziende, i listini no. I prezzi di listini che l'operatore non vede si
contano nel messaggio, non si nominano.

---

### Test

* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — chiusura di una mappatura e di una conversione, «chiudi e inserisci» differito, un listino di un'altra azienda, una mappatura usata solo da una bozza.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
