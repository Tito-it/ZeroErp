## 📘 Documentazione Concettuale – Funzione `script.fn_fattore_uom_alla_data`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore, che legge
> * [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa) — le righe dei documenti, che la chiamano
> * [vendite.trgfn_attivita_fattore_alla_data](/dbzero/vendite/funzioni/trgfn_attivita_fattore_alla_data) — le attività di commessa, che la chiamano

---

### 🎯 Scopo Principale

Dà il fattore di un'unità per un articolo a una data, o rifiuta: senza fattore la riga non passa
(`E_UOM_MISSING`), perché una quantità base inventata è peggio di nessuna.

---

### Chi la chiama

È la regola «senza fattore scritto, il fattore alla data» delle righe che portano un fattore: le
righe dei documenti di vendita e le attività di commessa. Il rifiuto nomina la porta che chiama, il
campo dell'unità e la tabella; i valori sono l'unità, l'unità base, l'articolo e la data.

---

### Test

* `db/pgtap/vendite/test-commesse-attivita-fattore-alla-data-v1.sql` — il rifiuto col campo dell'unità.
* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — il rifiuto sulle righe dei documenti.

---

### Note di migrazione

* 2026-11-10 — nasce (brief-db-revisione-catalogo, giro 2-bis).

---

{% include-markdown "signature-core.md" %}
