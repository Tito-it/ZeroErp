---
search:
  exclude: true
---

# Schema `pagamenti`

## 📚 Tabelle (manuale)
- [centri_riscossione](manual/centri_riscossione.md) — La tabella **`pagamenti.centri_riscossione`** definisce le **origini di incasso** per i movimenti vendite (banca, posta, cassa, compensazioni, fondo fattura, ecc.).
- [enti_incasso](manual/enti_incasso.md) — La tabella `pagamenti.enti_incasso` rappresenta i canali di provenienza dei flussi di incasso (banca, poste, PSP, altro), collegando il canale ai riferimenti anagrafici e operativi necessari all'import e riconciliazione.
- [sepa_mandati](manual/sepa_mandati.md) — (rev 2026-08-21)
- [sistemazioni](manual/sistemazioni.md) — (rev 2026-08-22 — nasce rinominando `pagamenti.compensazioni`)
- [transizioni_stati_contabile](manual/transizioni_stati_contabile.md) — (rev 2026-08-21)
- [transizioni_stati_contabile_riga](manual/transizioni_stati_contabile_riga.md) — (rev 2026-08-21)
- [vendite_contabili](manual/vendite_contabili.md) — La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile** per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per centro riscossione e data contabile, con eventuale dettaglio del canale (`ente_incasso`) e stato operativo della testata.
- [vendite_contabili_lotti](manual/vendite_contabili_lotti.md) — Tabella ponte che collega i lotti di fatturazione (`vendite.fatturazione_lotti`) alle testate contabili vendite (`pagamenti.vendite_contabili`).
- [vendite_contabili_righe](manual/vendite_contabili_righe.md) — La tabella **`pagamenti.vendite_contabili_righe`** contiene il dettaglio delle righe importate/gestite nella testata contabile vendite, con stato di lavorazione e riferimenti di abbinamento (fattura, billing account).
- [vendite_contabili_righe_stati](manual/vendite_contabili_righe_stati.md) — (latest review 13-02-2026)   La tabella **`pagamenti.vendite_contabili_righe_stati`** definisce il lookup degli stati delle **righe contabili** legate ai movimenti vendite.
- [vendite_contabili_stati](manual/vendite_contabili_stati.md) — (latest review 13-02-2026)   La tabella **`pagamenti.vendite_contabili_stati`** definisce il lookup degli stati della **testata contabile vendite**.
- [vendite_movimenti](manual/vendite_movimenti.md) — La tabella **`pagamenti.vendite_movimenti`** registra i movimenti di incasso/rimborso collegati alle fatture, con indicazione della **provenienza** (centro riscossione)  e dei parametri utili al calcolo interessi e alla contabilizzazione.

## ⚙️ Funzioni (manuale)
- [fn_annulla_sistemazione](manual/fn_annulla_sistemazione.md) — (rev 2026-08-22)
- [fn_conferma_sistemazione](manual/fn_conferma_sistemazione.md) — (rev 2026-08-22)
- [fn_get_or_create_vendite_contabile](manual/fn_get_or_create_vendite_contabile.md) — Recuperare una testata contabile vendite esistente oppure crearne una nuova, con possibilita` di collegarla al lotto fatturazione tramite tabella ponte.
- [fn_get_saldi_rate](manual/fn_get_saldi_rate.md) — (rev 2026-09-17)
- [fn_get_saldo_fattura](manual/fn_get_saldo_fattura.md) — (latest review 18-09-2026)   La funzione **`pagamenti.fn_get_saldo_fattura()`** risponde a **tre domande diverse su un documento**, e tenerle separate è il motivo per cui esiste:
- [fn_get_saldo_fattura_contabili](manual/fn_get_saldo_fattura_contabili.md) — (latest review 18-09-2026)   La funzione **`pagamenti.fn_get_saldo_fattura_contabili()`** restituisce il saldo contabile di una fattura calcolato sulle sole righe in stato `is_postabile = true`.
- [fn_get_saldo_rata](manual/fn_get_saldo_rata.md) — (rev 2026-09-17)
- [fn_posta_contabile](manual/fn_posta_contabile.md) — (rev 2026-08-22)
- [fn_posta_riga_tardiva](manual/fn_posta_riga_tardiva.md) — (scritta il 18-09-2026)
- [trgfn_enti_incasso_guard_conto_incasso](manual/trgfn_enti_incasso_guard_conto_incasso.md) — (rev 2026-08-22)
- [trgfn_enti_incasso_guard_psp](manual/trgfn_enti_incasso_guard_psp.md) — Garantire la coerenza applicativa dei record `pagamenti.enti_incasso` quando il canale e` di tipo `PSP`.
- [trgfn_sistemazioni_guard_dati](manual/trgfn_sistemazioni_guard_dati.md) — (rev 2026-08-22)
- [trgfn_sistemazioni_guard_transizione](manual/trgfn_sistemazioni_guard_transizione.md) — (rev 2026-08-22)
- [trgfn_vendite_contabili_guard_chiusura](manual/trgfn_vendite_contabili_guard_chiusura.md) — (rev 2026-08-21)
- [trgfn_vendite_contabili_guard_ente_centro](manual/trgfn_vendite_contabili_guard_ente_centro.md) — Validare la coerenza tra `centro_riscossione_id` della testata e `ente_incasso_id` quando presente.
- [trgfn_vendite_contabili_guard_transizione](manual/trgfn_vendite_contabili_guard_transizione.md) — (rev 2026-08-21)
- [trgfn_vendite_contabili_guard_validazione](manual/trgfn_vendite_contabili_guard_validazione.md) — (rev 2026-09-30)
- [trgfn_vendite_contabili_lotti_guard_sistemazione](manual/trgfn_vendite_contabili_lotti_guard_sistemazione.md) — (rev 2026-08-22 — sostituisce `trgfn_vendite_contabili_lotti_guard_compensazione`)
- [trgfn_vendite_contabili_righe_guard_contenuto](manual/trgfn_vendite_contabili_righe_guard_contenuto.md) — (scritto il 14-09-2026)
- [trgfn_vendite_contabili_righe_guard_distinta_finale](manual/trgfn_vendite_contabili_righe_guard_distinta_finale.md) — (rev 2026-09-30)
- [trgfn_vendite_contabili_righe_guard_rata](manual/trgfn_vendite_contabili_righe_guard_rata.md) — (rev 2026-08-22)
- [trgfn_vendite_contabili_righe_guard_stato_dati](manual/trgfn_vendite_contabili_righe_guard_stato_dati.md) — (rev 2026-08-21)
- [trgfn_vendite_contabili_righe_guard_transizione](manual/trgfn_vendite_contabili_righe_guard_transizione.md) — (rev 2026-08-21)
- [trgfn_vendite_contabili_righe_marca_fondo_eseguito](manual/trgfn_vendite_contabili_righe_marca_fondo_eseguito.md) — (rev 2026-08-22)
- [trgfn_vendite_movimenti_sync_contabile_from_riga](manual/trgfn_vendite_movimenti_sync_contabile_from_riga.md) — Mantenere coerenti `contabile_id`, `fattura_id` e `billing_account_id` su `pagamenti.vendite_movimenti` quando viene usato il riferimento a riga (`contabile_riga_id`).

## 🔍 Views (manuale)
- [vw_eccedenze_da_sistemare](manual/vw_eccedenze_da_sistemare.md) — (rev 2026-08-22)
- [vw_rate_fuori_capienza](manual/vw_rate_fuori_capienza.md) — (rev 2026-09-18)
- [vw_saldi_rate](manual/vw_saldi_rate.md) — (rev 2026-09-17)
