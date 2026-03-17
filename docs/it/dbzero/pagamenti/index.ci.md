# Schema `pagamenti`

## 📚 Tabelle (manuale)
- [centri_riscossione](manual/centri_riscossione.md)
- [compensazioni](manual/compensazioni.md)
- [enti_incasso](manual/enti_incasso.md) — La tabella `pagamenti.enti_incasso` rappresenta i canali di provenienza dei flussi di incasso (banca, poste, PSP, altro), collegando il canale ai riferimenti anagrafici e operativi necessari all'import e riconciliazione.
- [vendite_contabili](manual/vendite_contabili.md)
- [vendite_contabili_lotti](manual/vendite_contabili_lotti.md) — Tabella ponte che collega i lotti di fatturazione (`vendite.fatturazione_lotti`) alle testate contabili vendite (`pagamenti.vendite_contabili`).
- [vendite_contabili_righe](manual/vendite_contabili_righe.md)
- [vendite_contabili_righe_stati](manual/vendite_contabili_righe_stati.md)
- [vendite_contabili_stati](manual/vendite_contabili_stati.md)
- [vendite_movimenti](manual/vendite_movimenti.md)

## ⚙️ Funzioni (manuale)
- [fn_get_or_create_vendite_contabile](manual/fn_get_or_create_vendite_contabile.md) — Recuperare una testata contabile vendite esistente oppure crearne una nuova, con possibilita` di collegarla al lotto fatturazione tramite tabella ponte.
- [fn_get_saldo_fattura](manual/fn_get_saldo_fattura.md)
- [fn_get_saldo_fattura_contabili](manual/fn_get_saldo_fattura_contabili.md)
- [trgfn_enti_incasso_guard_psp](manual/trgfn_enti_incasso_guard_psp.md) — Garantire la coerenza applicativa dei record `pagamenti.enti_incasso` quando il canale e` di tipo `PSP`.
- [trgfn_vendite_contabili_guard_ente_centro](manual/trgfn_vendite_contabili_guard_ente_centro.md) — Validare la coerenza tra `centro_riscossione_id` della testata e `ente_incasso_id` quando presente, e applicare i vincoli della compensazione.
- [trgfn_vendite_contabili_lotti_guard_compensazione](manual/trgfn_vendite_contabili_lotti_guard_compensazione.md) — Impedire l'associazione di testate contabili di compensazione alla tabella ponte dei lotti (`pagamenti.vendite_contabili_lotti`).
- [trgfn_vendite_movimenti_sync_contabile_from_riga](manual/trgfn_vendite_movimenti_sync_contabile_from_riga.md) — Mantenere coerenti `contabile_id`, `fattura_id` e `billing_account_id` su `pagamenti.vendite_movimenti` quando viene usato il riferimento a riga (`contabile_riga_id`).
