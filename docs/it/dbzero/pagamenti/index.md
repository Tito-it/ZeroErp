# Schema `pagamenti`

## 📚 Tabelle
- [centri_riscossione](tabelle/centri_riscossione.md) — La tabella **`pagamenti.centri_riscossione`** definisce le **origini di incasso** per i movimenti vendite (banca, posta, cassa, compensazioni, fondo fattura, ecc.).
- [compensazioni](tabelle/compensazioni.md) — La tabella **`pagamenti.compensazioni`** rappresenta la testata del processo che genera movimenti di compensazione tra documenti del cliente.
- [enti_incasso](tabelle/enti_incasso.md) — La tabella `pagamenti.enti_incasso` rappresenta i canali di provenienza dei flussi di incasso (banca, poste, PSP, altro), collegando il canale ai riferimenti anagrafici e operativi necessari all'import e riconciliazione.
- [sepa_mandati](tabelle/sepa_mandati.md)
- [vendite_contabili](tabelle/vendite_contabili.md) — La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile** per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per centro riscossione e data contabile, con eventuale dettaglio del canale (`ente_incasso`) e stato operativo della testata.
- [vendite_contabili_lotti](tabelle/vendite_contabili_lotti.md) — Tabella ponte che collega i lotti di fatturazione (`vendite.fatturazione_lotti`) alle testate contabili vendite (`pagamenti.vendite_contabili`).
- [vendite_contabili_righe](tabelle/vendite_contabili_righe.md) — La tabella **`pagamenti.vendite_contabili_righe`** contiene il dettaglio delle righe importate/gestite nella testata contabile vendite, con stato di lavorazione e riferimenti di abbinamento (fattura, billing account).
- [vendite_contabili_righe_stati](tabelle/vendite_contabili_righe_stati.md) — (latest review 13-02-2026)   La tabella **`pagamenti.vendite_contabili_righe_stati`** definisce il lookup degli stati delle **righe contabili** legate ai movimenti vendite.
- [vendite_contabili_stati](tabelle/vendite_contabili_stati.md) — (latest review 13-02-2026)   La tabella **`pagamenti.vendite_contabili_stati`** definisce il lookup degli stati della **testata contabile vendite**.
- [vendite_movimenti](tabelle/vendite_movimenti.md) — La tabella **`pagamenti.vendite_movimenti`** registra i movimenti di incasso/rimborso collegati alle fatture, con indicazione della **provenienza** (centro riscossione)  e dei parametri utili al calcolo interessi e alla contabilizzazione.

## ⚙️ Funzioni
- [fn_get_or_create_vendite_contabile](funzioni/fn_get_or_create_vendite_contabile.md) — Recuperare una testata contabile vendite esistente oppure crearne una nuova, con possibilita` di collegarla al lotto fatturazione tramite tabella ponte.
- [fn_get_saldo_fattura](funzioni/fn_get_saldo_fattura.md) — (latest review 13-02-2026)   La funzione **`pagamenti.fn_get_saldo_fattura()`** restituisce il **residuo** della fattura:
- [fn_get_saldo_fattura_contabili](funzioni/fn_get_saldo_fattura_contabili.md) — (latest review 13-02-2026)   La funzione **`pagamenti.fn_get_saldo_fattura_contabili()`** restituisce il saldo contabile di una fattura calcolato sulle sole righe in stato `is_postabile = true`.
- [trgfn_enti_incasso_guard_psp](funzioni/trgfn_enti_incasso_guard_psp.md) — Garantire la coerenza applicativa dei record `pagamenti.enti_incasso` quando il canale e` di tipo `PSP`.
- [trgfn_vendite_contabili_guard_ente_centro](funzioni/trgfn_vendite_contabili_guard_ente_centro.md) — Validare la coerenza tra `centro_riscossione_id` della testata e `ente_incasso_id` quando presente, e applicare i vincoli della compensazione.
- [trgfn_vendite_contabili_lotti_guard_compensazione](funzioni/trgfn_vendite_contabili_lotti_guard_compensazione.md) — Impedire l'associazione di testate contabili di compensazione alla tabella ponte dei lotti (`pagamenti.vendite_contabili_lotti`).
- [trgfn_vendite_movimenti_sync_contabile_from_riga](funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga.md) — Mantenere coerenti `contabile_id`, `fattura_id` e `billing_account_id` su `pagamenti.vendite_movimenti` quando viene usato il riferimento a riga (`contabile_riga_id`).

## 🔍 Views
