## 📘 Documentazione Concettuale – Funzione `script.fn_check_rinuncia_reversibile`

> 👀 **Vedi anche**
>
**Consumatore (madre, solleva il primo motivo):**
>
• [vendite.fn_riapri_riconsegna_reso](/dbzero/vendite/funzioni/fn_riapri_riconsegna_reso)
>
**Contesto:**
>
• [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce)
> • [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare)
> • pattern gemello: [script.fn_check_ddt_emittibile](/dbzero/script/funzioni/fn_check_ddt_emittibile)

### 🎯 Scopo Principale

(creata 2026-07-26 — brief-db-chiusura-riconsegna-reso-definitivo §5.1)

**Single source dei motivi che impediscono di RIAPRIRE una rinuncia di ri-consegna**,
cioè di annullare la dichiarazione «questa merce non tornerà al cliente».
Ritorna `[]` se reversibile, altrimenti l'array ordinato dei motivi ostativi:
`[{codice, reason, reason_key, dettaglio}, ...]`.

### ⚠️ È un gate DORMIENTE — e non è incompleto

Oggi l'unico motivo che produce è la **riga inesistente**. Il gate *vero* sarebbe:

> reversibile **finché la nota di credito non è stata emessa** sulla quota

perché riaprire una rinuncia già coperta da una NC sfalserebbe un documento fiscale. Ma
**il ramo NC non esiste ancora** nel progetto: la coda accrediti
(`vw_resi_da_accreditare`) oggi la alimenta e nessuno emette note di credito. Vietare
qualcosa che non può accadere sarebbe finto rigore.

### Perché allora esiste

Perché il **punto di innesto** deve esistere *prima* del bisogno. L'alternativa scartata
era lasciare la conseguenza in un commento dentro la funzione madre: un commento non è un
punto di innesto — la slice NC dovrebbe *cercare* dove intervenire, e nel frattempo una
riapertura potrebbe sfalsare una NC già emessa senza che nulla lo segnali.

Così invece: **quando la slice NC arriverà, riempirà questa funzione** aggiungendo il
motivo, e il divieto si attiverà da sé — `fn_riapri_riconsegna_reso` solleva già il primo
motivo prodotto. Nessuna modifica alla madre, nessuna conseguenza da ricordare.

È lo stesso principio dei `fn_check_*` esistenti: il guard si **progetta** per
l'espansione, non si rinvia.

### 🚫 Non rimuovere «perché ritorna sempre vuoto»

È la trappola prevedibile: una funzione che non vieta nulla sembra codice morto.
Rimuoverla riporta la conseguenza a essere una nota in un commento che nessuno cercherà —
esattamente il problema che risolve.

### Regole chiave

- Funzione **pura** (`fn_check_*`): non solleva per condizioni di dominio, non scrive. È
  la madre a decidere se sollevare. L'unico raise è il guard di parametro.
- La riga inesistente è segnalata come **motivo** (riusando `E_RESO_NOT_FOUND`, già a
  catalogo) e non come eccezione, per restare coerenti col contratto della famiglia.
- `STABLE`, sola lettura.
