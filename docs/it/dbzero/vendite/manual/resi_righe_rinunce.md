## 📘 Documentazione Concettuale – Tabella `vendite.resi_righe_rinunce`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) (gemella: il lato consegnato)
>
> Funzioni:
> [vendite.fn_chiudi_riconsegna_reso](/dbzero/vendite/funzioni/fn_chiudi_riconsegna_reso)
> [vendite.fn_riapri_riconsegna_reso](/dbzero/vendite/funzioni/fn_riapri_riconsegna_reso)
> [vendite.fn_resi_riga_residuo_riconsegna](/dbzero/vendite/funzioni/fn_resi_riga_residuo_riconsegna)
>
> Viste:
> [vendite.vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare)
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

Registra la quota di merce **resa per essere ri-consegnata** che l'operatore dichiara
**non tornerà più al cliente**. È la seconda uscita di una riga reso: la merce torna
indietro (ponte `resi_righe_riconsegne`) **oppure** si chiude qui.

Prima esisteva solo la prima: una ri-consegna mai eseguita lasciava l'ordine
`PARZIALMENTE_EVASO` per sempre, la riga in coda ri-spedizione indistinguibile da una
lavorabile, e l'accredito etichettato *facoltativo* — quindi invisibile a chi lavora
le partite dovute.

### La cosa più importante da capire

**Scrivere qui non muove nessun numero.** Non crea documenti, non tocca `tenuti`, non
cambia l'importo dell'accredito. È una **dichiarazione**, non un calcolo: cambia la
*natura* di una quota pendente, da «tornerà indietro» a «definitiva». Tutto il resto è
conseguenza automatica di quel cambio di natura:

| Conseguenza | Dove avviene |
| --- | --- |
| il residuo dell'ordine si chiude → **EVASO** | `fn_ordine_riga_qta_riconsegna` sottrae le rinunce |
| la riga esce dall'elenco ri-spedizione | `vw_resi_da_riconsegnare` (residuo 0) |
| l'accredito passa da FACOLTATIVA a **DOVUTA** | `vw_resi_da_accreditare`, con **importo invariato** |

Se dopo una rinuncia l'importo dell'accredito cambiasse, sarebbe il sintomo che la
sottrazione è finita nel posto sbagliato (dev'essere in `fn_ordine_riga_qta_riconsegna`,
**mai** in `vw_resi_righe_effettive`, che alimenta anche il contatore merce).

### Regole chiave

- Ogni riga = una quota dichiarata definitiva: `resi_riga_id` + `qta` (unità **base**,
  come la gemella) + `note` facoltative. `CHECK qta > 0`.
- **Nessuna UNIQUE, e non è una dimenticanza.** La gemella ha
  `UNIQUE(resi_riga_id, ddt_riga_id)` perché ogni ri-consegna punta a una riga DDT. La
  rinuncia non ha un secondo termine: una UNIQUE sul solo `resi_riga_id` vieterebbe le
  **rinunce ripetute** (rinuncio a 3 oggi, ad altri 2 la settimana prossima), che sono
  il caso d'uso. L'invariante lo tiene il guard, non l'unicità.
- **Perché una tabella e non una colonna** su `resi_righe`: una colonna accumulerebbe il
  totale e perderebbe chi/quando/perché di ogni evento; la tabella rende la
  reversibilità la **cancellazione di una riga** invece di un'aritmetica all'indietro, e
  la formula del residuo perfettamente simmetrica:
  `residuo = quantita − Σ riconsegnate − Σ rinunciate`.
- **Guard** `trgfn_resi_rinunce_guard`: la riga reso deve essere di tipo
  `riapre_residuo = true` (`E_RESO_RICONSEGNA_TIPO_NON_VALIDO`); `Σ ric + Σ rin ≤`
  quantità resa (`E_RESO_RINUNCIA_SUPERA_RESO`, 560); lock `FOR UPDATE` su `resi_righe`
  e su **entrambi** i ponti.
- Popolata **solo** da `fn_chiudi_riconsegna_reso`; svuotata (o ridotta) da
  `fn_riapri_riconsegna_reso`.
- **Indice su `resi_riga_id` obbligatorio**, a differenza della gemella: là la UNIQUE lo
  copriva come prefisso, qui non c'è, e `fn_resi_riga_residuo_riconsegna` fa
  `SUM(qta) WHERE resi_riga_id = ?` per ogni riga di elenco e di coda.

### Merce fisica

La quota rinunciata resta **materialmente al fornitore**. Senza modulo magazzino non c'è
nulla da movimentare, ma quando il magazzino arriverà il movimento partirà da qui: è il
tipo di conseguenza che sparisce dalla memoria del progetto e riemerge come sorpresa.
