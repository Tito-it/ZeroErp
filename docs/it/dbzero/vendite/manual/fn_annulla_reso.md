## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_reso`

> 👀 **Vedi anche**
>
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) (simmetrica) ·
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Funzione madre atomica** (`SECURITY INVOKER`) che annulla un reso e **storna** gli effetti,
simmetrica a `fn_conferma_reso`. Stati ammessi: `DRAFT` o `CONFERMATO`
(`E_RESO_STATO_NON_ANNULLABILE`).

### Logica

1. **Guard anti-storno complesso**: un reso già ri-spedito (righe nel ponte
   `resi_righe_riconsegne`) **non** è annullabile — lo storno di una ri-spedizione emessa è fuori
   perimetro (`E_RESO_ANNULLO_CON_RICONSEGNE`).
2. Transizione → `ANNULLATO`.
3. **Solo se era CONFERMATO** — storno: l'addendo reso decade (l'helper filtra i CONFERMATI) →
   **ri-proiezione stato ordine** (`PARZIALMENTE_EVASO`/`EVASO`); e **ri-flip DDT** `RESO →
   CONSEGNATO` se non è più reso totale (transizione seedata nella matrice DDT).

Un annullo in `DRAFT` non ha effetti (nulla era stato applicato).
