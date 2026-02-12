# Schema `pagamenti`

## 📚 Tabelle
- [sepa_mandati](tabelle/sepa_mandati.md)
- [vendite_movimenti](tabelle/vendite_movimenti.md) — (latest review 10-02-2026)   `pagamenti.vendite_movimenti` registra i **movimenti di incasso/rimborso** associati alle fatture di vendita. Supporta piu` movimenti per fattura ed e` la base per determinare lo stato di pagamento.
- [centri_riscossione](tabelle/centri_riscossione.md) — (latest review 11-02-2026)   `pagamenti.centri_riscossione` definisce l’origine degli incassi (banca/posta/cassa/compensazioni).
- [vendite_contabili](tabelle/vendite_contabili.md) — (latest review 11-02-2026)   `pagamenti.vendite_contabili` rappresenta la testata contabile per l’aggregazione dei movimenti vendite.

## ⚙️ Funzioni
- [fn_get_saldo_fattura](funzioni/fn_get_saldo_fattura.md) — (latest review 11-02-2026)   La funzione **`pagamenti.fn_get_saldo_fattura()`** restituisce il **saldo** movimenti di una fattura e un flag che indica se esistono movimenti.

## 🔍 Views
