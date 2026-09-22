## 📘 Documentazione Concettuale – Funzione `vendite.fn_ordine_riga_qta_riconsegna`

> 👀 **Vedi anche**
>
> [vendite.fn_ordine_ha_residuo_evasione](/dbzero/vendite/funzioni/fn_ordine_ha_residuo_evasione) ·
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza) ·
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

**Helper unico** (`STABLE`, `SECURITY INVOKER`) dell'**addendo reso** del residuo evasione ordine:

```text
fn_ordine_riga_qta_riconsegna(p_ordine_riga_id) =
    Σ (resi_righe.quantita − Σ rinunciate)   (resi CONFERMATI, tipo_reso.riapre_residuo = true)
    per quella riga ordine
```

### La quota rinunciata non pesa più sul residuo (rev 2026-07-26)

Dal 2026-07-26 l'addendo scende della quota dichiarata **definitiva**
([`resi_righe_rinunce`](/dbzero/vendite/tabelle/resi_righe_rinunce)). La ragione: merce che
**non tornerà al cliente** non è più merce «da evadere», quindi non deve tenere l'ordine
`PARZIALMENTE_EVASO` a vita. Togliendola qui, il residuo si chiude e l'ordine passa a
`EVASO` — ed è **questo** il punto che rende utile tutta la chiusura ri-consegna.

⚠️ **Si sottraggono solo le rinunce, NON le ri-consegne**: quelle sono già contate come
`evaso` dal fulfillment, e sottrarle di nuovo le conterebbe due volte.

### ⚠️ Perché la sottrazione sta QUI e non nella vista

`vw_resi_righe_effettive` avrebbe potuto esporre la quota già netta, ma **ha sei
consumatori** — fra cui la partita di merce
([`fn_partite_merce`](/dbzero/vendite/funzioni/fn_partite_merce)), che la somma
**senza filtro sul tipo**:

```text
tenuti = evaso − reso        differenza = tenuti − fatturati
coda accrediti = differenza < 0
```

Sottraendo le rinunce là, `reso` scenderebbe → `tenuti` salirebbe → `differenza` tenderebbe
a 0 → **la riga uscirebbe dalla coda accrediti**, cioè l'accredito dovuto al cliente
sparirebbe in silenzio. Questa funzione invece filtra `riapre_residuo` ed è letta **solo**
dal residuo ordine e dal guard fulfillment: sottrarre qui chiude l'ordine e lascia
l'accredito **intatto**.

**Non spostare questa sottrazione nella vista.**

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
