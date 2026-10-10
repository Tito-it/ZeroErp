## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_righe_eccezione`

> 👀 **Vedi anche**
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
>
> **Chi la legge:** [vendite.fn_documento_righe_preview](/dbzero/vendite/funzioni/fn_documento_righe_preview)

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-70`)

**Le righe eccezione di un contratto o di un'offerta, con le stesse colonne.**
Prezzi forzati, esclusioni e aggiunte stanno in due tabelle gemelle, una per
documento. Questa funzione le rende nella stessa forma, così la lista delle
righe sceglie la tabella in un punto solo invece che in tre.

- Primo argomento: il documento (`CONTRATTO`, `OFFERTA`); un altro valore è un
  errore di chi chiama (`E_DOC_TIPO_NON_GESTITO`).
- Tutte le righe, attive e spente: il filtro lo decide chi legge.
- `SECURITY INVOKER`: le due tabelle hanno la sicurezza per riga, e la lettura
  resta nel perimetro di chi chiede.
- Le colonne hanno i tipi di `contratti_righe`; l'offerta ha le stesse
  colonne con lo stesso tipo (cambia solo la precisione di prezzo e fonte, che
  una funzione non riporta).

---

{% include-markdown "signature-core.md" %}
