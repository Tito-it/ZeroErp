# Schema `pagamenti`

## 📚 Tabelle (manuale)
- [centri_riscossione](manual/centri_riscossione.md) — La tabella **`pagamenti.centri_riscossione`** definisce le **origini di incasso** per i movimenti vendite (banca, posta, cassa, compensazioni, ecc.).
- [vendite_contabili](manual/vendite_contabili.md) — La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile** per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per centro riscossione e data contabile.
- [vendite_movimenti](manual/vendite_movimenti.md) — La tabella **`pagamenti.vendite_movimenti`** registra i movimenti di incasso/rimborso collegati alle fatture, con indicazione della **provenienza** (centro riscossione)  e dei parametri utili al calcolo interessi e alla contabilizzazione.

## ⚙️ Funzioni (manuale)
- [fn_get_saldo_fattura](manual/fn_get_saldo_fattura.md) — (latest review 11-02-2026)   La funzione **`pagamenti.fn_get_saldo_fattura()`** restituisce il **saldo** movimenti di una fattura e un flag che indica se esistono movimenti.
