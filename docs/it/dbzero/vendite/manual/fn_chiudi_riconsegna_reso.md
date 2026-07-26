## 📘 Documentazione Concettuale – Funzione `vendite.fn_chiudi_riconsegna_reso(...)`

> 👀 **Vedi anche**
>
> Gemella (l'altra uscita):
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)
> · inversa:
> [vendite.fn_riapri_riconsegna_reso](/dbzero/vendite/funzioni/fn_riapri_riconsegna_reso)
>
> Tabelle:
> [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce) (scritta) ·
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
>
> Dipendenze:
> [vendite.fn_resi_riga_residuo_riconsegna](/dbzero/vendite/funzioni/fn_resi_riga_residuo_riconsegna) ·
> [vendite.fn_ordine_ha_residuo_evasione](/dbzero/vendite/funzioni/fn_ordine_ha_residuo_evasione)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

Dichiara che una quota di merce **resa per essere ri-consegnata non tornerà al cliente**.
È l'uscita che mancava: `fn_genera_ddt_riconsegna` gestisce bene il parziale (ri-spedisci
3 su 10, gli altri 7 restano in coda), ma se quei 7 non torneranno mai indietro non
c'era modo in-app di chiudere la partita.

Le due funzioni sono le **due uscite della stessa attività**: la merce torna al cliente,
oppure no.

### Cosa fa, in concreto

Scrive una riga in `resi_righe_rinunce` per ogni riga reso lavorata, poi ri-proietta lo
stato dell'ordine. **Non crea documenti.** Ritorna il numero di righe reso chiuse.

Tutto il resto è conseguenza automatica del cambio di natura della quota:

| Effetto | Prodotto da |
| --- | --- |
| l'ordine passa a **EVASO** | `fn_ordine_riga_qta_riconsegna` non conta più la quota → nessun residuo → lo step finale di questa funzione aggiorna lo stato |
| la riga **esce** dall'elenco ri-spedizione | `vw_resi_da_riconsegnare` (residuo 0) |
| l'accredito diventa **DOVUTO** | `vw_resi_da_accreditare`, **con lo stesso importo di prima** |

### ⚠️ Non cambia nessun numero

Non tocca `tenuti`, non tocca l'importo dell'accredito, non genera DDT. Cambia solo la
*natura* di una quota pendente. Se dopo una chiusura l'importo dell'accredito cambiasse,
sarebbe il sintomo di un errore a monte (la sottrazione delle rinunce deve stare in
`fn_ordine_riga_qta_riconsegna`, **mai** in `vw_resi_righe_effettive`, che alimenta anche
il contatore merce).

### Regole chiave

- **Gate**: reso `CONFERMATO`, lo stesso della generazione — si chiude ciò che si potrebbe
  ri-spedire (`E_RESO_NON_CONFERMATO`).
- **`p_righe = NULL`** → chiude **tutta** la copertura residua del reso. Altrimenti
  `[{resi_riga_id, qta}]`, con la quantità **troncata al residuo** (`LEAST`): stessa
  disciplina race-proof della gemella.
- Il residuo viene da `fn_resi_riga_residuo_riconsegna`, quindi è **al netto delle
  ri-consegne e delle rinunce già registrate**: una riga già chiusa o già tutta
  ri-spedita viene saltata.
- Se non c'è nulla da chiudere → `E_RESO_NESSUNA_RICONSEGNA_PENDENTE` (riuso della
  gemella: la condizione è la stessa).
- `p_note` facoltative, propagate su tutte le righe della chiamata.
- **Nessun advisory lock**: la serializzazione è il `FOR UPDATE` del guard del ponte, che
  blocca la riga reso padre — rinuncia e ri-consegna concorrenti si incrociano lì.

### Reversibile

`fn_riapri_riconsegna_reso` annulla la dichiarazione: la quota torna ri-spedibile,
l'ordine torna `PARZIALMENTE_EVASO`, l'accredito torna facoltativo. Round-trip
chiudi → riapri = stato iniziale. Un errore di digitazione su un reso confermato deve
avere rimedio.

### Merce fisica

La quota rinunciata resta **materialmente al fornitore**. Senza modulo magazzino non c'è
nulla da movimentare, ma quando il magazzino arriverà **il movimento partirà da qui**.
