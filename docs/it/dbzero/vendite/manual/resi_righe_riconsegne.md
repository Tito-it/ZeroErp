## 📘 Documentazione Concettuale – Tabella `vendite.resi_righe_riconsegne`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) (pattern gemello)
>
> Funzioni:
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Tabella-ponte** che aggancia una riga reso *per ri-consegna* ai DDT che la ri-spediscono. Mirror
strutturale di `ordini_righe_fulfillment`: stesso problema (una quantità soddisfatta da **N DDT**
nel tempo), stessa forma → supporta la **ri-spedizione parziale/multipla**.

### Regole chiave

- Ogni riga = una quota ri-spedita: `resi_riga_id` + `ddt_riga_id` (riga del DDT di ri-spedizione)
  + `qta` (base). `UNIQUE(resi_riga_id, ddt_riga_id)`.
- **Lo stato ri-consegna è DERIVATO** dalla copertura, non memorizzato: `Σ qta` vs
  `resi_righe.quantita` → `DA_RICONSEGNARE / PARZIALE / COMPLETATA` (calcolato nella vista
  `vw_resi_da_riconsegnare`). Niente colonna di stato, niente lookup (single source = la copertura).
- **Guard** `trgfn_resi_riconsegne_guard`: la riga reso deve essere di tipo `riapre_residuo=true`
  (`E_RESO_RICONSEGNA_TIPO_NON_VALIDO`); Σ qta ≤ quantità resa (`E_RESO_RICONSEGNA_SUPERA_RESO`);
  lock `FOR UPDATE`.
- Popolata **solo** da `fn_genera_ddt_riconsegna`. Per i resi order-backed, la stessa azione crea
  anche il `ordini_righe_fulfillment` che chiude il residuo dell'ordine (doppio binario: attribuzione
  per-reso qui, stato ordine di là).
