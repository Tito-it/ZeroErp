## 📘 Documentazione Concettuale – Tabella `acquisti.ordini`

> 👀 **Vedi anche**
>
> • [acquisti.ordini_righe](/dbzero/acquisti/tabelle/ordini_righe)
> • [acquisti.ddt](/dbzero/acquisti/tabelle/ddt)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Testata dell'ordine di acquisto**: l'impegno verso il fornitore.

Porta già i campi utili alla **ricezione** — indirizzo di consegna, riferimenti al DDT
fornitore — perché l'ordine e la sua evasione sono lo stesso processo visto in due momenti.

---

### ⚠️ L'indirizzo di consegna dev'essere di tipo consegna

`trgfn_acq_ordini_only_consegna_tipo_con` verifica che `indirizzo_consegna_id` punti a un
indirizzo con `codice_interno = 'CON'`. Altrimenti `E_TIPO_INDIRIZZO`.

Sembra ovvio, ed è il tipo di controllo che serve proprio perché è ovvio: gli indirizzi di un
soggetto stanno tutti nella stessa tabella, e nulla nella FK distingue una sede legale da un
magazzino di consegna.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
