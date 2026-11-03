## 📘 Documentazione Concettuale – Funzione `vendite.fn_conferma_reso`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.resi](/dbzero/vendite/tabelle/resi) ·
> [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) (simmetrica, storno) ·
> [vendite.fn_ordine_ha_residuo_evasione](/dbzero/vendite/funzioni/fn_ordine_ha_residuo_evasione) ·
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Funzione madre atomica** (`SECURITY DEFINER`, `search_path` stretto) che conferma un reso e ne applica gli effetti in
un'unica transazione. Gli effetti valgono **solo** per i resi CONFERMATI: la conferma è il punto in
cui il reso «diventa reale».

### Effetti (in ordine)

1. **Transizione** `DRAFT → CONFERMATO` (attraversa `trgfn_resi_guard_transizione`; assegna il
   `numero` via `trgfn_resi_gen_numero`). Guard: reso esistente, in DRAFT, con almeno una riga
   (`E_RESO_NOT_FOUND` / `E_RESO_STATO_NON_CONFERMABILE` / `E_RESO_SENZA_RIGHE`).
2. **Proiezione stato ordine** per ogni ordine coinvolto dalle righe *per ri-consegna*: il residuo
   ora reso-aware si riapre → `PARZIALMENTE_EVASO` (o `EVASO` se ancora chiuso). Le transizioni di
   rientro sono già seedate.
3. **Flip DDT origine** `CONSEGNATO → RESO` **solo se reso totale** (tutte le quantità consegnate
   del DDT rese, resi non-ANNULLATI, qualunque tipo). Su parziale il DDT resta CONSEGNATO.

### Il reso totale e' della merce

(rev 3-11-2026, `20261103-32`, brief `brief-db-addebito-trasporto-ordine` §8.1)

Il flip `CONSEGNATO → RESO` conta solo le righe di **merce** della bolla
([`script.fn_natura_e_merce`](/dbzero/script/funzioni/fn_natura_e_merce) sulla
natura congelata): un onere (trasporto, spese) non si rende, e senza il filtro
una bolla con un onere non andrebbe mai a RESO. Il gemello e'
[`fn_annulla_reso`](fn_annulla_reso.md), che cambia insieme.

La riapertura del residuo è **implicita** (l'helper `fn_ordine_riga_qta_riconsegna` conta i resi
CONFERMATI): la madre non scala `qta_evasa` (append-only), aggiorna solo lo **stato** proiettato.
