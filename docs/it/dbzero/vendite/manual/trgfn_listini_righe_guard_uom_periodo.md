## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_righe_guard_uom_periodo`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — le righe che guarda
>
> Approfondimento funzioni:
>
> * [catalogo.fn_uom_primo_giorno_non_convertibile](/dbzero/catalogo/funzioni/fn_uom_primo_giorno_non_convertibile) — la regola del periodo
> * [vendite.trgfn_listini_versioni_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_uom_periodo) — il secondo lato
> * [catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi) — il terzo lato

---

### 🎯 Scopo Principale

L'unità di un prezzo di listino si converte per l'articolo in **ogni giorno** del periodo della
versione. Lo guarda su un prezzo nuovo (in bozza, o in una versione attiva come rettifica) e su un
prezzo riacceso.

---

### Prima

La regola stava solo nel backend, e guardava il solo giorno di decorrenza della versione: una
mappatura che finiva a metà versione passava, e da quel giorno il listino offriva un prezzo in
un'unità che per l'articolo non si converte. Articolo, unità e versione di una riga non cambiano,
quindi bastano l'inserimento e la riaccensione.

---

### Test

* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — riga in bozza, rettifica in una versione attiva, riaccensione.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
