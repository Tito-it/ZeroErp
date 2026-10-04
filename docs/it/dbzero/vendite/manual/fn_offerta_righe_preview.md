## 📘 Documentazione Concettuale – Funzione `vendite.fn_offerta_righe_preview`

> 👀 **Vedi anche**
>
> **Il corpo:** [vendite.fn_documento_righe_preview](/dbzero/vendite/funzioni/fn_documento_righe_preview)
>
> **Il gemello del contratto:** [vendite.fn_contratto_righe_preview](/dbzero/vendite/funzioni/fn_contratto_righe_preview)
>
> **Da non confondere con:** [vendite.fn_offerta_righe_espanse](/dbzero/vendite/funzioni/fn_offerta_righe_espanse) — le righe pronte per l'ordine
>
> **Verifica:** `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-72`)

**Le righe di un'offerta come le vede il drawer, coi verbi che il database
ammette.** Sono le stesse colonne e gli stessi verbi della lista del contratto:
righe del listino con sopra prezzi forzati ed esclusioni, poi le aggiunte.
Un'esclusione ha il solo verbo «ripristina l'articolo», come sul contratto.

Prima il drawer dell'offerta leggeva la tabella delle eccezioni così com'era e
i verbi li deduceva da solo: una seconda sede della regola. Da oggi li riceve
dal database.

È un ingresso di una riga: il corpo è
[`fn_documento_righe_preview`](/dbzero/vendite/funzioni/fn_documento_righe_preview)
con il documento `OFFERTA`. Non sostituisce
[`fn_offerta_righe_espanse`](/dbzero/vendite/funzioni/fn_offerta_righe_espanse),
che risponde a un'altra domanda: le righe da portare in un ordine, con le
esclusioni tolte.

---

{% include-markdown "signature-core.md" %}
