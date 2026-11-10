## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fattore_alla_data`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le attività di commessa, una delle due tabelle
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività fatturabili, l'altra
>
> Approfondimento funzioni:
>
> * [script.fn_fattore_uom_alla_data](/dbzero/script/funzioni/fn_fattore_uom_alla_data) — il fattore alla data, o il rifiuto
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — la stessa regola sulle righe dei documenti

---

### 🎯 Scopo Principale

Un'attività senza fattore, di commessa o fatturabile, prende quello **alla data dell'attività**,
non 1. Il fattore scritto è la fotografia (copiato da un documento sorgente, dalla riga che si
rettifica, dall'attività di commessa che si emette) e si rispetta.

---

### La regola

L'unità è quella operativa, o quella della riga se l'operativa manca, o l'unità base dell'articolo
se mancano tutte e due. Per l'unità base il fattore è 1;
per le altre è la mappatura o la conversione generale in vigore quel giorno; senza nessuna delle due
la riga si rifiuta (`E_UOM_MISSING`). Un aggiornamento che cambia l'unità e non il fattore rilegge il
fattore. La quantità base la porta chi scrive.

---

### Prima

Il fattore mancante valeva 1 in cinque posti: il default della colonna, il default del parametro
della madre `fn_upsert_commessa_attivita` e il suo `COALESCE`, l'onere, l'accredito. Tre cartoni
passavano come tre pezzi. Ora il default non c'è più, nemmeno sulle attività fatturabili, e la regola
è qui, sulle due tabelle.

---

### Test

* `db/pgtap/vendite/test-commesse-attivita-fattore-alla-data-v1.sql` — unità base, unità mappata, unità senza conversione, fattore scritto.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
