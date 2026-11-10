## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_versioni_guard_uom_periodo`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — le versioni che guarda
>
> Approfondimento funzioni:
>
> * [vendite.fn_listino_versione_riga_uom_non_convertibile](/dbzero/vendite/funzioni/fn_listino_versione_riga_uom_non_convertibile) — la prima riga scoperta
> * [vendite.trgfn_listini_righe_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_uom_periodo) — il primo lato

---

### 🎯 Scopo Principale

Il periodo di una versione di listino **non si allunga** su giorni in cui l'unità di un suo prezzo
non si converte per l'articolo.

---

### Come è fatta

`AFTER UPDATE OF valido_dal, valido_al`, quando il periodo nuovo non sta dentro il vecchio:
accorciare non scopre niente. In una versione attiva la fine la cambiano solo i verbi, e il giudizio
vale anche per loro. Il campo dell'errore è la data cambiata.

---

### Test

* `db/pgtap/vendite/test-listino-uom-periodo-v1.sql` — bozza allungata oltre la mappatura, dentro la mappatura, accorciata.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
