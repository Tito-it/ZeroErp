## 📘 Documentazione Concettuale – Funzione `vendite.fn_ordine_riga_qta_riconsegna`

> 👀 **Vedi anche**
>
> [vendite.fn_ordine_ha_residuo_evasione](/dbzero/vendite/funzioni/fn_ordine_ha_residuo_evasione) ·
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza) ·
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Helper unico** (`STABLE`, `SECURITY INVOKER`) dell'**addendo reso** del residuo evasione ordine:

```
fn_ordine_riga_qta_riconsegna(p_ordine_riga_id) =
    Σ resi_righe.quantita  (resi CONFERMATI, tipo_reso.riapre_residuo = true)
    per quella riga ordine
```

### Perché esiste (no logica duplicata)

La formula del residuo vive in **due** consumatori che devono restare coerenti:

- [`fn_ordine_ha_residuo_evasione`](/dbzero/vendite/funzioni/fn_ordine_ha_residuo_evasione) — il
  **gate** dello stato ordine;
- [`trgfn_ordini_ful_guard_consistenza`](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza)
  — l'**enforcement** del fulfillment.

Senza l'addendo nel guard, la ri-spedizione di un reso verrebbe bloccata da `E_QTA_SUPERA_RESIDUO`
(il residuo si è riaperto ma il guard non lo sa). Estraendo l'addendo qui, entrambi lo richiamano →
**una sola fonte della verità**. Toccando la logica residuo, aggiornare questo helper, non i due
consumatori.
