# Schema `pagamenti`

## 📚 Tabelle
- [sepa_mandati](tabelle/sepa_mandati.md)
- [vendite_movimenti](tabelle/vendite_movimenti.md) — (latest review 10-02-2026)   `pagamenti.vendite_movimenti` registra i **movimenti di incasso/rimborso** associati alle fatture di vendita. Supporta piu` movimenti per fattura ed e` la base per determinare lo stato di pagamento.

## ⚙️ Funzioni
- [fn_get_saldo_fattura](funzioni/fn_get_saldo_fattura.md) — (latest review 11-02-2026)   La funzione **`pagamenti.fn_get_saldo_fattura()`** restituisce il **saldo** movimenti di una fattura e un flag che indica se esistono movimenti.

## 🔍 Views
