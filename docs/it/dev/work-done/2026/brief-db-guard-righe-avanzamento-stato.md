# Brief DB — Documento "vuoto" non avanza di stato + capability righe-aware

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-16
> · **Rev 1**: 2026-07-19 — aggiunto il caso **causale DDT** (§1a-bis): stesso rilievo,
> stessa famiglia, emerso alla validazione in-app della slice DDT-resi-dashboard.
> · **Rev 2**: 2026-07-19 (analisi critica lato DB) — tre correzioni sostanziali:
> le condizioni bloccanti l'emissione DDT sono **cinque, non tre** (§1a-bis);
> il guard §1b **esiste già** (543, chiuso dalla slice DDT-resi); il principio
> «single source col trigger» ora ha un **meccanismo** (`fn_check_ddt_emittibile`).
> · **Owner**: Tid
> **Vedi anche**: [brief-db-push-commessa-gia-inviato.md](brief-db-push-commessa-gia-inviato.md)
> — stessa famiglia UX (azione non pertinente non va offerta), causa radice diversa:
> predicato delle `fn_list_*_da_pushare` cieco sull'allocazione (rilievo ORD0000227).
> **Stato**: **APPLICATO + TEST VERDI** (2026-07-19) — migrations `20260719-01..04`
> EXECUTED, pgTAP verdi (`test-fn-check-ddt-emittibile-v1` plan(10) nuovo +
> `test-fn-available-actions-offerta-v1` plan(18) esteso). Alla stesura Rev 2 è
> emerso che gli step 1 (5 domini su 6), 2 e 3 erano **già stati realizzati il
> 2026-07-16** senza che il brief venisse aggiornato: il lavoro odierno chiude i
> buchi residui (DDT multi-condizione, offerte senza enabled). **✅ COMPLETO**
> (2026-07-21): DB committato (`00eb20a48`), doc auto-gen rigenerata, verificato
> sul vivo che i 4 guard DDT + `fn_available_actions_ddt` delegano a
> `fn_check_ddt_emittibile`. Spostato in `work-done/` il 2026-07-21.
> · **BE/FE RECEPITO (2026-07-19, COMMITTATO)** — il formato §3 è stato
> implementato lato client: mapper azioni multi-motivo + tooltip multi-riga +
> 7 chiavi i18n `azione_reason`, con review critica (5 fix, incluso un bug
> reale del tooltip). Dettaglio nel §5. **Nessun lavoro BE**: le capability
> viaggiano in passthrough nel detail, i codici errore sono invariati.
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
| Ordini | 0 righe | ✅ DB (`E_ORDINE_CONFERMA_SENZA_RIGHE` 471, in `trgfn_ordini_guard_transizione` — **corretto in Rev 2**: era «solo BE», ma il guard è stato spostato a DB il 2026-07-16) |
| Contratti | forma *senza_listino* con 0 righe AGGIUNTA | ✅ DB (`E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`); forma *con_listino* mai "vuota" di sostanza |
| DDT | ⚠️ non «vuoto» ma **«non pronto all'emissione»**: cinque condizioni distinte (§1a-bis) | ✅ **tutti a DB**, in 4 trigger diversi: righe 543 · causale 544 · prezzi 545 · indirizzi · componenti pendenti |
| Offerte | `listino_versione_id` mancante/non ATTIVA (le righe sono espanse dal listino) | ✅ trigger (`E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`) |

FE: con la forma disabled+reason decisa, il render disabled + tooltip sulla
`reason` è a carico nostro (piccolo adeguamento in
`mapAvailableActionsToDrawerActions`/`DrawerActionsBar`, lo facciamo noi
appena la capability espone i campi — comunicateci nome e formato, §3).

### 1a-bis. DDT: la capability "emetti" copre TUTTE le condizioni di emissione (DL-28)

> ⚠️ **Nota di scopo (Rev 2)**: per il DDT il concetto di «vuoto» non regge più —
> causale, prezzi, indirizzi e componenti pendenti non sono vuotezza. Per questo
> dominio si legga **«non pronto all'emissione»**. Il titolo del brief resta, ma
> il criterio con cui giudicare cosa ci sta dentro è questo, non «documento vuoto»:
> serve per non farlo diventare un contenitore buono per tutto.

Rilievo in-app di Tid (2026-07-19, validazione slice DDT-resi-dashboard): la regola
UX del progetto è che un'azione non pronta non venga offerta — invece «Emetti» su un
DDT **senza causale di trasporto** è visibile e cliccabile, e l'utente scopre il
vincolo solo dal banner 409.

I guard bloccanti **esistono già** (slice DDT-resi,
[brief in work-done](brief-db-fatturazione-ddt-resi.md) §4a DL-28,
`trgfn_ddt_guard_causale_emissione` applicato `20260718-04`): R1 causale
obbligatoria all'emissione (544) · R2 prezzo **risolvibile** su ogni riga attiva se
la causale è fatturabile (545, proprio o ereditato dall'ordine via fulfillment).
⚠️ La causale resta **legittimamente NULL in bozza** (decisione DL-28 — i DDT da
evasione nascono senza) → il vincolo NON va sul salvataggio né sulla creazione:
va **solo sulla capability dell'azione di emissione**, come per le righe.

#### ⛔ Correzione Rev 2: le condizioni sono CINQUE, e stanno in quattro trigger

La stesura Rev 1 diceva «tre condizioni». **Censimento sul DB vivo (2026-07-19)**:
l'emissione di un DDT è oggi sbarrata da **quattro funzioni trigger distinte**,
tutte `_a10_ BEFORE UPDATE` su `vendite.ddt`:

| guard trigger | cosa blocca all'emissione |
|---|---|
| `trgfn_ddt_guard_transizione` | matrice stati + **0 righe attive** (`E_DDT_EMISSIONE_SENZA_RIGHE`, **543**) |
| `trgfn_ddt_guard_causale_emissione` | causale mancante (**544**) · prezzo non risolvibile se causale fatturabile (**545**) |
| `trgfn_ddt_guard_indirizzi_obbligatori` | indirizzi documento mancanti (`E_INDIRIZZO_DOC_OBBLIGATORIO`) |
| `trgfn_ddt_guard_transizione_approvazione` | componenti pendenti di valorizzazione (`E_COMPONENTE_PREZZO_PENDENTE`, `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`) |

**Perché conta**: una capability che ne copre solo tre abilita il pulsante e
lascia fallire il click su indirizzi o componenti — lo stesso difetto che il
brief vuole eliminare, solo spostato di causa. Anzi peggio di oggi: adesso il
pulsante è sempre cliccabile e l'utente lo sa; con un fix parziale il pulsante
abilitato diventa una **promessa non mantenuta**.

➜ **Regola generale (vale per tutti i domini, non solo DDT)**: la capability
deve rispecchiare **l'unione di TUTTI i guard che gate-ano quella transizione**,
mai un sottoinsieme.

#### ✅ Il meccanismo: una funzione sola, due consumatori

«Non ricopiarla: single source col trigger» (Rev 1) era giusto come principio ma
**non eseguibile**: un trigger non è chiamabile da una funzione capability, e la
logica R2 è una query bespoke (`LATERAL` su `ordini_righe_fulfillment`; la vista
`vw_ddt_righe_iva_base` **non** è riusabile perché filtra
`prezzo_unitario IS NOT NULL`). Chi implementa avrebbe dovuto duplicarla,
violando la regola «niente logica duplicata tra livelli».

Si estrae quindi una funzione **pura** (convenzione `fn_check_*`: nessun raise)
che ritorna **i motivi ostativi**:

```sql
script.fn_check_ddt_emittibile(p_ddt vendite.ddt) RETURNS jsonb
  -- [] se emittibile; altrimenti [{codice, reason, reason_key, dettaglio}, ...]
  -- NB (in scrittura): parametro = RIGA, non id — i guard sono BEFORE UPDATE
  -- e devono valutare i valori CANDIDATI (NEW); con un id rileggerebbero i
  -- valori vecchi e un UPDATE che imposta insieme stato+causale fallirebbe.
```

- i **quattro guard trigger** la chiamano e sollevano sul primo motivo
  (fail-fast invariato, **codici errore invariati**: 543/544/545/indirizzi/componenti);
- `fn_available_actions_ddt` la chiama e, se non vuota, espone `emetti`
  **disabled** con quei motivi come `reason`.

Un solo posto dove vive «cosa rende un DDT emittibile», due comportamenti
diversi. Al prossimo vincolo aggiunto, capability e guard restano allineati **per
costruzione** — invece di scoprire l'asimmetria mesi dopo in produzione, che è
esattamente come è nato questo brief.

Forma decisa §1a: **disabled + `reason`** (es. «manca la causale di trasporto»,
«riga N senza prezzo»). Il FE ha già l'asterisco informativo sulla causale in
bozza: col pulsante disabilitato-e-motivato il percorso diventa coerente
end-to-end.

### 1b. ~~Guard mancante: DDT vuoto non deve emettersi~~ — GIÀ FATTO

**Corretto in Rev 2**: la stesura del 2026-07-16 diceva «`DRAFT→EMESSO` con 0
righe passa, nessun guard DB né BE». **Non è più vero**: il guard esiste come
`E_DDT_EMISSIONE_SENZA_RIGHE` (**543**), implementato dentro
`trgfn_ddt_guard_transizione` durante la slice DDT-resi — cioè *dopo* la stesura
originale. (Ironia utile: il §1a-bis cita quella slice per i guard 544/545 ma non
si era accorto che la stessa slice chiudeva anche questo punto.)

La decisione resta registrata perché è ancora la regola viva: **zero righe =
niente da trasportare**; il "DDT solo trasporto" resta legittimo perché è *righe
senza prezzo*, non *zero righe*.

➜ Nessun lavoro da fare. Lo **step 2 del §4 è da spuntare**.

### 1c. ~~Simmetria ordini: guard a DB~~ — GIÀ FATTO

**Corretto in Rev 2**: come il §1b, anche questo punto è stato chiuso il
2026-07-16 senza aggiornare il brief. `trgfn_ordini_guard_transizione` ha la
Regola 2 «DRAFT→CONFERMATO richiede almeno una riga ATTIVA»
(`E_ORDINE_CONFERMA_SENZA_RIGHE`, **471**), con nota esplicita nel corpo:
*«Spostata da ordini_service.py (E_ORD_NESSUNA_RIGA inline)»*. Il guard BE
resta come fail-fast, come auspicato. ➜ Nessun lavoro; **step 3 del §4 da
spuntare**.

## 2. Fuori perimetro (già coperti, nessuna azione)

- Preventivi/Resi: guard DB già corretti (verificati).
- Contratti: coperto nella sostanza per entrambe le forme.
- Offerte: il vincolo giusto è sul listino, non sulle righe (modello espanso).

## 3. Cosa comunicare indietro a BE/FE — FORMATO DEFINITO (Rev 2)

**Campi per azione** (già esistenti dal 2026-07-16 su 5 domini, ora su tutti 6):

- `enabled` boolean · `reason` text|null (codice macchina, es. `CAUSALE_MANCANTE`)
  · `reason_key` text|null (chiave i18n: se presente il FE traduce, altrimenti
  mostra `reason`).
- **Nuovo (solo azione emetti del DDT)**: `reasons` — array completo dei motivi
  `[{codice, reason, reason_key, dettaglio}]`, per tooltip multi-riga; il campo
  è assente quando l'azione è enabled.

**Nuove `reason_key` da tradurre lato FE**:

- `vendite.ddt.azione_reason.causale_mancante` · `.prezzo_non_risolvibile`
  · `.componenti_prezzo_pendente` · `.componenti_non_valorizzati`
- `common.azione_reason.indirizzi_mancanti`
- `vendite.offerte.azione_reason.listino_versione_mancante` · `.listino_versione_non_attiva`

**Codici errore**: nessun codice nuovo — i guard sollevano gli stessi di prima
(543/544/545/471/`E_INDIRIZZO_DOC_OBBLIGATORIO`/componenti): il mapping FE
esistente resta valido.

> ✅ **RECEPITO lato FE (2026-07-19)** — contratto implementato integralmente,
> vedi §5. Verificato: le **8 `reason_key`** emesse dal DB (grep su
> `20260719-01..04` + doc auto-gen) combaciano **esattamente** con le chiavi
> i18n create, zero typo.

## 4. Avanzamento

| # | Step | Stato |
|---|---|---|
| 0 | **`fn_check_ddt_emittibile`** (motivi ostativi, pura) + refactor dei 4 guard trigger perché la chiamino — **SVILUPPATO** (`20260719-01`/`-03` + manuale) | ☑ |
| 1 | Capability nelle 6 `fn_available_actions_*` — 5 domini già fatti il 2026-07-16 (`requires_righe`); **oggi**: DDT delega a `fn_check_ddt_emittibile` (`20260719-02`) e offerte ricevono `enabled/reason` sul listino (`20260719-04`) — **SVILUPPATO** | ☑ |
| 2 | ~~Guard DDT: emissione con 0 righe~~ — **GIÀ FATTO** (543, slice DDT-resi) | ☑ |
| 3 | ~~Guard ordini a DB~~ — **GIÀ FATTO** il 2026-07-16 (471, §1c) | ☑ |
| 4 | Apply dev + pgTAP — **FATTO 2026-07-19** (migrate applicato, test verdi) | ☑ |
| 5 | **Recepimento BE/FE del contratto §3** — **FATTO 2026-07-19** (non committato), §5 | ☑ |

> **Nota di sequenza**: lo step 0 va prima dell'1 **solo per il DDT**. Gli altri
> cinque domini hanno una condizione sola e non richiedono estrazione: la
> capability interroga direttamente il proprio predicato (righe o listino).

## 5. Consuntivo BE/FE (2026-07-19) — realizzato, non committato

**BE: nessun lavoro, ed è la forma giusta.** Le capability arrivano già al FE in
passthrough (`get_capabilities` → merge nel detail di ogni dominio) e i codici
errore sono invariati e già mappati in `error_policies.py`: tutto il contratto
nuovo viaggia nel jsonb che il DB emette. Nessun endpoint, nessun serializer.

**FE — tre interventi:**

| File | Cosa |
|---|---|
| `core/composables/useDrawerActions.js` | il mapper gestiva già `enabled:false → disabled+tooltip` (dal 2026-07-16). Aggiunto: supporto all'array **`reasons`** (tutti i motivi, non solo il primo) normalizzando motivo-singolo e lista a **un percorso solo**, con decodifica **fail-visible** via il BB `labelOrCode` (chiave i18n mancante → codice macchina, mai il path a video) |
| `core/composables/useActionBar.js` + `assets/main.css` | tooltip **multi-riga**: forma oggetto con `class: 'app-tooltip-multiline'` + regola `white-space: pre-line` in main.css |
| 6 drawer + `locales/it.json`/`en.json` | `te` iniettato al mapper (preventivi, offerte, ordini, contratti, DDT, resi) + le **7 chiavi i18n** `azione_reason` del §3, parità it/en verificata |

**Review critica (8 finder, 5 fix applicati)** — un **bug reale** che build e
lint non vedevano: la prima stesura passava lo stile del tooltip via `pt`, ma la
**directive** tooltip di PrimeVue 4.5.5 legge dall'oggetto solo
`value|disabled|escape|class|fitContent|id|showDelay|hideDelay|autoHide` —
**`pt` è dei componenti, non della directive**: veniva ignorato in silenzio e i
motivi multipli sarebbero comparsi collassati su una riga sola. Fix con `class`
(supportata) + classe in main.css, che chiude anche la violazione «niente stili
inline, classi `app-*` centralizzate». Altri fix: `resolveReason` duplicava
`labelOrCode` → riuso del BB; due rami per la stessa resa → uno; guard `te`
invertito nel merito (senza `te` traduceva a chiave cieca, cioè poteva mostrare
il path i18n proprio nel caso che doveva proteggere) → default `() => false`,
degrado al codice macchina.

⚠️ **Nota per chi tocca le barre azioni**: `buttonTooltip` di `useActionBar` è
condiviso anche da **`PageActionsBar`** (toolbar liste), non solo dai drawer. Il
cambio è retro-compatibile (la forma oggetto scatta solo con `\n` nel testo, che
oggi produce solo questa capability), ma il punto è comune alle due barre.

**Verifiche**: lint pulito, build Vite verde, logica del mapper esercitata su 6
casi (multi-motivo · singolo · senza `reason_key` · senza `te` · azione
abilitata · `reasons` vuoto). **Non validato in-app**: nei dati dev non esistono
DDT in DRAFT senza causale né preventivi vuoti (il backfill `20260718-06` ha
valorizzato tutto) — il comportamento a video si vedrà alla prima bozza reale,
con «Emetti» disabilitato e il tooltip che elenca **tutti** i motivi.
