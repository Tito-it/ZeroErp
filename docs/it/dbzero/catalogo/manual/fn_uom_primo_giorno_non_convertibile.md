## 📘 Documentazione Concettuale – Funzione `catalogo.fn_uom_primo_giorno_non_convertibile`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_fonti_conversione](/dbzero/catalogo/funzioni/fn_uom_fonti_conversione) — le fonti, coi loro periodi
> * [vendite.trgfn_listini_righe_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_uom_periodo) — il guard della riga di listino, che la legge
> * [vendite.fn_listino_versione_riga_uom_non_convertibile](/dbzero/vendite/funzioni/fn_listino_versione_riga_uom_non_convertibile) — la prima riga scoperta di una versione
> * [vendite.fn_listini_attivi_uom_non_convertibili](/dbzero/vendite/funzioni/fn_listini_attivi_uom_non_convertibili) — i prezzi attivi scoperti dal catalogo

---

### 🎯 Scopo Principale

Dice il **primo giorno** di un periodo in cui un'unità non si converte per un articolo. Se si
converte in ogni giorno del periodo risponde vuoto.

---

### La regola

È la regola di Q24 sui listini: l'unità di un prezzo vale per tutto il periodo della versione, non
solo il primo giorno. I giorni scoperti sono il periodo meno l'unione dei periodi delle fonti
(`fn_uom_fonti_conversione`): la base, le mappature, le conversioni generali. Una fonte che finisce
e un'altra che comincia il giorno dopo coprono il periodo senza buchi.

---

### Come è fatta

`LANGUAGE sql`, `STABLE`, sui multirange di date. Un buco senza inizio esce come `-infinity`; un
periodo vuoto o assente risponde vuoto.

---

### Test

* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — i tre lati della regola, una mappatura che finisce durante la versione.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
