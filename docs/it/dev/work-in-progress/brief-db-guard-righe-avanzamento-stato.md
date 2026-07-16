# Brief DB — Documento "vuoto" non avanza di stato + capability righe-aware

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-16 · **Owner**: Tid
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
vuoto, e il FE — data-driven — mostra il pulsante. Serve che l'azione di
avanzamento **non venga offerta** (omessa, o esposta disabled con `reason` —
scelta del team: esiste già il pattern `reason` su push_commessa/genera_ordine
dei preventivi) quando il documento è "vuoto" nel senso del suo modello:

| Dominio | "Vuoto" significa | Guard bloccante oggi |
|---|---|---|
| Preventivi | 0 righe attive | ✅ DB (`PREV_NESSUNA_RIGA_ATTIVA` + totale>0) |
| Resi | 0 righe | ✅ DB (`E_RESO_SENZA_RIGHE`) |
| Ordini | 0 righe | ⚠️ solo BE (`E_ORD_NESSUNA_RIGA`) |
| Contratti | forma *senza_listino* con 0 righe AGGIUNTA | ✅ DB (`E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`); forma *con_listino* mai "vuota" di sostanza |
| DDT | 0 righe | ❌ nessuno (vedi 1b) |
| Offerte | `listino_versione_id` mancante/non ATTIVA (le righe sono espanse dal listino) | ✅ trigger (`E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`) |

FE: se l'azione viene **omessa** il FE è zero-touch (il pulsante sparisce da solo);
se viene esposta **disabled+reason** il FE aggiunge il render disabled (piccolo
adeguamento, lo facciamo noi). Ci va bene entrambe — decidete voi la forma,
purché uniforme sui 6 domini.

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

- La forma scelta per la capability (azione omessa vs disabled+reason) e il
  nome dell'eventuale campo reason, così adeguiamo il FE se serve.
- Codici errore dei nuovi guard (DDT, ordini) per il mapping messaggi FE.

## 4. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Capability righe-aware nelle 6 `fn_available_actions_*` | ☐ |
| 2 | Guard DDT: emissione con 0 righe → errore | ☐ |
| 3 | Guard ordini a DB (simmetria) | ☐ |
| 4 | Apply dev + comunicazione forma capability/codici a BE/FE | ☐ |
