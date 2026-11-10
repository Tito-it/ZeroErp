## 📘 Documentazione Concettuale – Funzione `vendite.fn_listino_versione_riga_uom_non_convertibile`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_listini_versioni_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_uom_periodo) — il guard del periodo, che la legge
> * [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile) — l'attivazione, che la legge

---

### 🎯 Scopo Principale

Dice la prima riga attiva di una versione di listino con un'unità che, in un giorno del periodo
della versione, non si converte per l'articolo: la riga, l'articolo, i codici, il primo giorno
scoperto. Nessuna riga se la versione è coperta.

---

### Due lettori

Il periodo che si allunga e l'attivazione di una bozza chiedono la stessa cosa. Una bozza scritta
bene si può rompere sotto, quando il catalogo chiude una conversione: il terzo lato conta solo le
versioni attive, e la bozza la ferma l'attivazione.

---

### Test

* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — il periodo allungato, la bozza rotta dal catalogo.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
