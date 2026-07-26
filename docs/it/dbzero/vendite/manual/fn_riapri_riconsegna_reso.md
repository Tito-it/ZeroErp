## 📘 Documentazione Concettuale – Funzione `vendite.fn_riapri_riconsegna_reso(...)`

> 👀 **Vedi anche**
>
> Inversa:
> [vendite.fn_chiudi_riconsegna_reso](/dbzero/vendite/funzioni/fn_chiudi_riconsegna_reso)
> · precedente d'analogia:
> [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso)
>
> Tabelle:
> [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce) (cancellata/ridotta)
>
> Gate:
> [script.fn_check_rinuncia_reversibile](/dbzero/script/funzioni/fn_check_rinuncia_reversibile)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

Annulla una **chiusura di ri-consegna**: la quota torna ri-spedibile, l'ordine torna
`PARZIALMENTE_EVASO`, l'accredito torna *facoltativo*. Round-trip
chiudi → riapri = **stato iniziale**.

Esiste per la stessa ragione per cui `fn_annulla_reso` esiste accanto alla conferma: un
errore di digitazione su un reso confermato deve avere rimedio. Senza reversibilità una
chiusura sbagliata sarebbe irreparabile, perché le rinunce non hanno una UI di modifica.

### Cancella, non disattiva

La tabella non ha colonna `attivo`: la reversibilità **è** la cancellazione di una riga.
Non è una scorciatoia — è esattamente il motivo per cui il progetto ha scelto una tabella
invece di una colonna accumulatrice su `resi_righe`: con una colonna servirebbe
un'aritmetica all'indietro, qui basta togliere l'evento. Lo storico della cancellazione
resta comunque in `vendite.storico` via trigger.

### Regole chiave

- **Gate**: reso `CONFERMATO`, come le sorelle.
- **`p_righe = NULL`** → riapre **tutte** le rinunce delle righe ri-consegna del reso.
- **`[{resi_riga_id, qta}]`** → riapre fino a `qta`, scalando dalle rinunce **più
  recenti** (LIFO): si annulla *l'ultimo errore*, non il primo evento registrato.
  Omettere `qta` riapre tutta la riga.
- **Annullo parziale di una singola rinuncia**: la riga non viene cancellata ma **ridotta**
  di quantità, così resta la traccia della parte ancora definitiva.
- Se non c'è nulla da riaprire → `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`.
- Ritorna il numero di **righe reso** riaperte (non di rinunce cancellate).

### Il gate per la nota di credito — progettato, non ancora attivo

Il gate corretto sarebbe: *«reversibile finché la nota di credito non è stata emessa»*.
Riaprire una rinuncia già coperta da una NC sfalserebbe un documento fiscale.

Ma **il ramo NC non esiste ancora** nel progetto: oggi la coda accrediti
(`vw_resi_da_accreditare`) la alimenta e nessuno emette note di credito. Vietare qualcosa
che non può accadere sarebbe finto rigore.

La funzione consuma comunque `script.fn_check_rinuncia_reversibile`, che oggi non produce
motivi ostativi. **Quando la slice NC arriverà, il divieto si aggiungerà là e si attiverà
da sé**, senza toccare questa funzione. Il punto di innesto è cablato, non rinviato a una
nota in un commento che nessuno cercherà.
