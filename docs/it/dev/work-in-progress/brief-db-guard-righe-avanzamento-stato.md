# Brief DB — Documento "vuoto" non avanza di stato + capability righe-aware

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-16
> · **Rev**: 2026-07-19 — aggiunto il caso **causale DDT** (§1a-bis): stesso rilievo,
> stessa famiglia, emerso alla validazione in-app della slice DDT-resi-dashboard.
> · **Owner**: Tid
> **Stato**: ☐ DA REALIZZARE
> **Origine**: rilievo in-app di Tid — su un preventivo VUOTO il pulsante "Emetti"
> è visibile e cliccabile; il guard DB (`PREV_NESSUNA_RIGA_ATTIVA`) rifiuta
> correttamente al click, ma l'azione non dovrebbe proprio essere offerta.
> L'audit sui 6 domini vendite ha mostrato guard non uniformi e capability
> cieche sul conteggio righe.

## 1. Cosa serve (NON come)

### 1a. Capability "righe-aware" — tutti i domini

Le `script.fn_available_actions_{preventivo,offerta,ordine,contratto,ddt,reso}`
oggi costruiscono le azioni **solo dallo stato** (matrice transizioni): l'azione
di avanzamento iniziale (emetti/conferma/attiva) è esposta anche a documento
vuoto, e il FE — data-driven — mostra il pulsante.

**✅ DECISO (Tid, 2026-07-19) — forma: DISABLED con `reason`, MAI omessa.**
L'azione resta visibile ma disabilitata, con la ragione esposta (tooltip FE):
un pulsante nascosto confonde — l'utente non sa che l'azione esiste né cosa
manca per sbloccarla; disabilitato+motivo insegna cosa completare. Esiste già
il pattern `reason` su push_commessa/genera_ordine dei preventivi: usare la
stessa forma, uniforme sui 6 domini. L'azione va esposta disabled quando il
documento è "vuoto" nel senso del suo modello:

| Dominio | "Vuoto" significa | Guard bloccante oggi |
|---|---|---|
| Preventivi | 0 righe attive | ✅ DB (`PREV_NESSUNA_RIGA_ATTIVA` + totale>0) |
| Resi | 0 righe | ✅ DB (`E_RESO_SENZA_RIGHE`) |
| Ordini | 0 righe | ⚠️ solo BE (`E_ORD_NESSUNA_RIGA`) |
| Contratti | forma *senza_listino* con 0 righe AGGIUNTA | ✅ DB (`E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`); forma *con_listino* mai "vuota" di sostanza |
| DDT | 0 righe **oppure** causale mancante **oppure** riga senza prezzo risolvibile su causale fatturabile (§1a-bis) | 0 righe: ❌ nessuno (vedi 1b) · causale/prezzi: ✅ DB (544/545, DL-28) |
| Offerte | `listino_versione_id` mancante/non ATTIVA (le righe sono espanse dal listino) | ✅ trigger (`E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`) |

FE: con la forma disabled+reason decisa, il render disabled + tooltip sulla
`reason` è a carico nostro (piccolo adeguamento in
`mapAvailableActionsToDrawerActions`/`DrawerActionsBar`, lo facciamo noi
appena la capability espone i campi — comunicateci nome e formato, §3).

### 1a-bis. DDT: la capability "emetti" copre ANCHE causale e prezzi (DL-28)

Rilievo in-app di Tid (2026-07-19, validazione slice DDT-resi-dashboard): la regola
UX del progetto è che un'azione non pronta non venga offerta — invece «Emetti» su un
DDT **senza causale di trasporto** è visibile e cliccabile, e l'utente scopre il
vincolo solo dal banner 409.

I guard bloccanti **esistono già** (slice DDT-resi,
[brief in work-done](../work-done/brief-db-fatturazione-ddt-resi.md) §4a DL-28,
`trgfn_ddt_guard_causale_emissione` applicato `20260718-04`): R1 causale
obbligatoria all'emissione (544) · R2 prezzo **risolvibile** su ogni riga attiva se
la causale è fatturabile (545, proprio o ereditato dall'ordine via fulfillment).
⚠️ La causale resta **legittimamente NULL in bozza** (decisione DL-28 — i DDT da
evasione nascono senza) → il vincolo NON va sul salvataggio né sulla creazione:
va **solo sulla capability dell'azione di emissione**, come per le righe.

Quindi per il DDT la capability "emetti" di `fn_available_actions_ddt` deve
considerare **tre** condizioni, non una:

1. `≥ 1 riga attiva` (il guard è da creare — §1b);
2. `causale_trasporto_id IS NOT NULL` (guard 544 già a DB);
3. se la causale è `fatturabile`: ogni riga attiva con prezzo risolvibile
   (guard 545 già a DB — stessa `COALESCE` riga/ordine del guard, non
   ricopiarla: single source col trigger).

Stessa forma decisa del §1a: **disabled + `reason`** (es. «manca la causale di
trasporto», «riga N senza prezzo»). Il FE ha già l'asterisco informativo sulla
causale in bozza (tooltip "obbligatoria per emettere"): col pulsante
disabilitato-e-motivato il percorso diventa coerente end-to-end.

### 1b. Guard mancante: DDT vuoto non deve emettersi

`DRAFT→EMESSO` di un DDT con 0 righe oggi **passa** (nessun guard DB né BE).
Decisione Tid 2026-07-16: **zero righe = niente da trasportare → guard**.
Il caso legittimo "DDT solo trasporto" resta possibile: è *righe senza prezzo*
(`prezzo_unitario NULL`), non *zero righe*. Serve il guard `≥1 riga attiva`
sulla transizione di emissione (stesso principio di preventivi/resi).

### 1c. Simmetria ordini: guard a DB

Il guard ordini vive **solo nel BE service**: unico dominio in cui il DB
accetterebbe la conferma di un ordine vuoto (es. scrittura diretta, batch,
futuro secondo chiamante). Per pari livello con preventivi/resi (e col principio
"guard restrittivi da subito"), serve il guard `≥1 riga` anche a DB sulla
transizione DRAFT→CONFERMATO. Il guard BE può restare come fail-fast.

## 2. Fuori perimetro (già coperti, nessuna azione)

- Preventivi/Resi: guard DB già corretti (verificati).
- Contratti: coperto nella sostanza per entrambe le forme.
- Offerte: il vincolo giusto è sul listino, non sulle righe (modello espanso).

## 3. Cosa comunicare indietro a BE/FE

- ~~La forma scelta per la capability~~ **decisa (Tid 2026-07-19): disabled +
  `reason`, mai omessa**. Da comunicare: **nome e formato** dei campi (es.
  `enabled`/`disabled_reason`/`disabled_reason_key` per azione — se c'è una
  `reason_key` i18n il FE traduce, altrimenti mostra il testo), così adeguiamo
  `mapAvailableActionsToDrawerActions`/`DrawerActionsBar`.
- Codici errore dei nuovi guard (DDT, ordini) per il mapping messaggi FE.

## 4. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Capability righe-aware nelle 6 `fn_available_actions_*` — per il DDT include causale + prezzi risolvibili (§1a-bis) | ☐ |
| 2 | Guard DDT: emissione con 0 righe → errore | ☐ |
| 3 | Guard ordini a DB (simmetria) | ☐ |
| 4 | Apply dev + comunicazione forma capability/codici a BE/FE | ☐ |
