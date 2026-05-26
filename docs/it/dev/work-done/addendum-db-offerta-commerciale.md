# Addendum brief DB — Offerta Commerciale

> **Stato**: addendum al brief
> [analisi-offerta-commerciale-db.md](analisi-offerta-commerciale-db.md) (già
> accettato, rev. 2026-05-24). Tre rifiniture emerse dalla verifica del piano
> applicativo BE+FE rev. c.
>
> **Sorgente di contesto**:
> [analisi-offerta-commerciale-be-fe.md](analisi-offerta-commerciale-be-fe.md)
> §0.3 e §0.4.
>
> **Branch**: `dev/db-tid` come da prassi.

---

## Cosa serve

### 1. Colonna `motivazione_rifiuto` sulla testata

Aggiungere alla testata `vendite.offerte_commerciali` una colonna testo
libera, nullable, per registrare il motivo quando l'offerta termina in stato
negativo (RIFIUTATA o ANNULLATA). Valorizzata dal trigger di transizione
insieme alle altre `data_*` già previste. Non serve struttura: è un testo
libero che l'operatore scrive nel dialog di chiusura.

**Perché**: senza questa colonna la motivazione finirebbe in `meta` JSONB, ma
è un dato di processo di prima cittadinanza (visibile in lista, esportabile,
filtrabile). Allinea il dominio offerta al pattern già usato altrove per le
note di chiusura.

### 2. Sesto stato `ANNULLATA` + revisione transizioni

Il brief originale prevede 5 stati e una transizione `BOZZA → RIFIUTATA`
("annullamento bozza"). Va sostituita con uno stato dedicato e una state
machine asimmetrica:

- **Aggiungere lo stato `ANNULLATA`** in `config.stati_doc_offerte` (terminale,
  nessuna uscita).
- **Transizioni ammesse nella forma finale**:
  - `BOZZA → EMESSA`
  - `BOZZA → ANNULLATA` (annullamento da noi, **unica via negativa dalla bozza**)
  - `EMESSA → ACCETTATA`
  - `EMESSA → RIFIUTATA` (no del cliente, **unica via negativa post-emissione**)
  - `EMESSA → SUPERATA` (via trigger revisione, già previsto)
- **Transizioni da NON ammettere** (sono incongrue col modello concordato col
  team applicativo):
  - `BOZZA → RIFIUTATA` — RIFIUTATA è semanticamente "no del cliente", e dal
    cliente non si arriva mai con un'offerta ancora in bozza. Va **rimossa**
    dal seed transizioni del brief originale.
  - `EMESSA → ANNULLATA` — una volta emessa, o accetta o rifiuta il cliente;
    eventuali correzioni nostre passano dalla revisione (che genera SUPERATA).

Il guard di transizione e i codici errore esistenti (`E_OFFERTA_TRANSIZIONE_NON_AMMESSA`)
restano invariati: cambia solo il contenuto della tabella transizioni.

**Perché**: rende la state machine offerta simmetrica a quella contratto
(`DRAFT → ANNULLATO` solo da DRAFT, mai da ATTIVO), e separa pulitamente
"ritiro da parte nostra" (ANNULLATA) da "no del cliente" (RIFIUTATA) nei
report e nei filtri di lista.

### 3. Conferma sui campi business della utility

Il brief originale (§3 step 3) descrive `offerte_commerciali_utilities` come
"mirror fedele" di `vendite.contratti_utilities`. È sufficiente una **conferma
esplicita** che la fedeltà include tutti i campi business (tipo utenza, classe
utenza, parametri, istanza dati precontrattuali, ecc.), non solo le FK
strutturali. Lo stesso vale per `fn_push_offerta_a_contratto`: la copia 1:1
deve trasportare anche questi campi.

**Perché**: il `ContrattoDrawer` lato applicativo li espone come editabili in
testata, quindi se mancassero nell'offerta il push genererebbe un contratto
con utility "spoglia". È quasi certo che il mirror fedele li copra già; serve
solo dirlo ad alta voce per chiudere il punto.

---

## Cosa NON cambia

- Idempotenza push pattern A (UNIQUE su `contratti(offerta_id)`).
- Naming `stati_doc_*` (offerta è documento commerciale, segue il pattern).
- Codici errore esistenti (nessuno nuovo necessario).
- Direzione FK `contratti.offerta_id` (resta come da §5.1-bis).
- Causale recesso/cessazione: rinviata a brief separato come da originale
  (la `motivazione_rifiuto` è cosa distinta — è testo libero di chiusura
  offerta, non causale strutturata di cessazione contratto).

---

## Sequenza

I tre punti sono indipendenti tra loro e indipendenti dagli step 1-9 del
brief originale (toccano colonne aggiuntive e contenuto seed, non strutture
nuove). Possono essere inseriti nell'ordine che il team preferisce, sia
accorpati a uno degli step esistenti sia come step a sé.

L'unico vincolo operativo è che il piano BE non parte finché l'addendum non
è applicato: il `TypedDict` lato Django porta già la colonna
`motivazione_rifiuto` e lo stato `ANNULLATA`.

---

*Addendum DB Offerta Commerciale — ZeroErp, 2026-05-24. Si applica al brief
[analisi-offerta-commerciale-db.md](analisi-offerta-commerciale-db.md) già
accettato. Pronto per applicazione su `dev/db-tid` dopo OK del team DB.*
