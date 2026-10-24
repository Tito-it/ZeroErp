## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_smistamento`

> 👀 **Vedi anche**
>
[vw_preventivi_smistamento_righe](vw_preventivi_smistamento_righe.md) (dettaglio per riga)
> [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine)
> [vendite.fn_preventivo_ha_residuo_commessa](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_commessa)

---
### 🎯 Scopo Principale
Aggregata per preventivo della vista righe smistamento: **contatori per ramo**
per badge e progress della UI. Sostituisce `vw_preventivi_stato_fatturazione`
(rename + rework natura-aware, 2026-06-12).

---

### Contatori

| Campo | Descrizione |
|-------|-------------|
| `righe_totali` | Righe attive del preventivo |
| `righe_merce` | Righe con destinazione effettiva `ORDINE` |
| `righe_servizi` | Righe con destinazione effettiva `COMMESSA` (incluse le pregresse a natura NULL) |
| `righe_a_ordine` | Righe smistate al ramo ordine |
| `righe_in_commessa` | Righe emesse in commessa (progressivo: include emesse AF e fatturate) |
| `righe_emesse_af` | Righe emesse come attivita' fatturabili (progressivo: include fatturate) |
| `righe_fatturate` | Righe con fattura generata |
| `righe_residue` | Righe non smistate su **alcun ramo** — alimenta il progress "X/Y smistate → EVASO" del pannello (gate D6) |

I contatori del ramo commessa mantengono la semantica progressiva dei vecchi
flag (fatturata ⊂ emessa ⊂ in commessa).

---

### Esempio d'uso

```sql
-- Badge "X/Y smistate" per il pannello
SELECT preventivo_numero,
       righe_totali - righe_residue AS smistate,
       righe_totali
  FROM vendite.vw_preventivi_smistamento
 WHERE preventivo_id = 42;
```

---

### Note operative

* `security_invoker = on` (policy RLS).
* `righe_residue = 0` e' la condizione "tutte le righe smistate", coerente con
  il passaggio a `EVASO` del DB (`vendite.fn_preventivo_proietta_stato_smistamento`,
  che usa le due fn `fn_preventivo_ha_residuo_*`; fino al 2026-10-12 lo faceva il
  backend dopo l'invio in commessa).
* Test: `db/pgtap/vendite/test-vw-preventivi-smistamento-v1.sql`.
