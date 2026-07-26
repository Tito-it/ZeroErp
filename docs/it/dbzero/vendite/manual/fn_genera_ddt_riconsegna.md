## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_ddt_riconsegna`

> 👀 **Vedi anche**
>
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) (ponte) ·
> [vendite.vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare) (coda) ·
> [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) (pattern) ·
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

**Funzione madre atomica** (`SECURITY INVOKER`) che genera il **DDT di ri-spedizione** per un reso
CONFERMATO e chiude l'aggancio duro con la coda di ri-consegna.

Firma: `fn_genera_ddt_riconsegna(p_reso_id, p_righe jsonb DEFAULT NULL, p_data date)`.
`p_righe = [{resi_riga_id, qta}]` per ri-spedizione **parziale**; `NULL` = tutta la copertura residua.

### Logica

1. Guard: reso in stato CONFERMATO (`E_RESO_NON_CONFERMATO`).
2. Nuovo **DDT DRAFT** con denormalizzati dal DDT origine. Se il reso è **order-backed** (righe con
   `ordine_riga_id`) la sorgente è `ORDINE_VENDITA` (+ `uid` ordine); altrimenti **standalone**.
3. Per ogni riga *ri-consegna* con copertura residua — dal 2026-07-26 letta dall'helper unico
   [`fn_resi_riga_residuo_riconsegna`](/dbzero/vendite/funzioni/fn_resi_riga_residuo_riconsegna),
   cioè `quantità resa − Σ ri-spedito − Σ rinunciato`: crea la
   `ddt_righe` (copia articolo/UoM/qta) e inserisce la riga-ponte `resi_righe_riconsegne` → **chiude
   la voce di coda**.
4. Se la riga reso ha `ordine_riga_id`: inserisce anche `ordini_righe_fulfillment` → **richiude il
   residuo** dell'ordine (il guard fulfillment è reso-aware, non blocca).
5. **Ri-proietta lo stato ordine** (come `fn_genera_ddt_da_ordine`): dopo la ri-spedizione l'ordine
   torna `EVASO`/`PARZIALMENTE_EVASO` coerente.

Idempotenza per copertura (righe già coperte saltate); niente ri-consegna pendente →
`E_RESO_NESSUNA_RICONSEGNA_PENDENTE` (rollback della testata DDT orfana). Funziona anche per lo
standalone: la coda è agganciata al DDT, non all'ordine.

### Non ri-spedisce la quota dichiarata definitiva (rev 2026-07-26)

Da quando esiste la chiusura ri-consegna
([`fn_chiudi_riconsegna_reso`](/dbzero/vendite/funzioni/fn_chiudi_riconsegna_reso)), il
residuo che questa funzione legge è **al netto delle rinunce**. Su una riga da 10 con 7
dichiarati definitivi, una richiesta di 10 viene troncata a 3; se tutto è rinunciato la riga
viene saltata fino a `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`.

Il guard del ponte avrebbe comunque bloccato l'INSERT: la differenza è che ora la
**quantità è corretta in partenza**, invece di essere una proposta che il guard rifiuta a
valle di un DDT già creato. Difesa in profondità che resta, più correttezza a monte.

Le due funzioni sono le **due uscite della stessa attività**: la merce torna al cliente,
oppure no.
