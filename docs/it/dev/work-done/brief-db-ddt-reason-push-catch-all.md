# Brief DB — Il DDT non pushabile dice sempre il motivo sbagliato (catch-all)

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Priorità**: 🟡 MEDIA per impatto (nessun dato errato: un
> messaggio che mente su una situazione legittima), ma **sforzo M/L, non S**: la
> Decisione A (fonte unica sul lister) è un intervento architetturale, non
> manutenzione di testi — vedi §3.
> **Stato**: ✅ **CHIUSO DB + FE** (2026-07-20) — DB: changeset `20260719-15`
> (fonte unica `fn_ddt_push_diagnosi`) + `20260719-16` (capability), pgTAP
> **7/7 verde**, doc auto-gen rigenerata, committato/pushato (`8b6614539`).
> FE: 3 traduzioni + generico riscritto it/en, e **Decisione D applicata
> davvero** — la reason non è più un banner fisso ma tooltip su pulsante
> «Invia a commessa» DISABILITATO (§4-bis), esteso per simmetria XOR anche al
> drawer ordini. Verificato sul caso reale: DDT0000326 → `DDT_FATTURA_DA_ORDINE`.
> Guard i18n verde, build Vite verde.
> **Origine**: rilievo in-app di Tid (2026-07-19) su **DDT0000326 / ORD0000580**,
> emerso validando la slice [brief-be-fe-ddt-resi-dashboard.md](../work-in-progress/brief-be-fe-ddt-resi-dashboard.md)
> (**documento BE/FE collegato**: FE-5 gate solo-trasporto nel drawer DDT).
> Il DDT è **CONSEGNATO**, ma nel drawer non compare il push a commessa e il
> banner recita *«DDT non ancora inviabile a commessa: dev'essere spedito o
> consegnato»* — cioè chiede una condizione **già soddisfatta**.
> **Stessa famiglia**: [brief-db-push-commessa-gia-inviato.md](brief-db-push-commessa-gia-inviato.md)
> (reason vere al posto di un no-op) ·
> [brief-db-i18n-namespace-reason-ordini.md](brief-db-i18n-namespace-reason-ordini.md)
> (namespace delle reason ordini) · [brief-db-guard-righe-avanzamento-stato.md](brief-db-guard-righe-avanzamento-stato.md)
> (azione non pronta → disabled+reason). ⚠️ **Non è però lo stesso difetto**: qui
> la `reason_key` è nel namespace giusto e il messaggio **si vede** — è il
> *contenuto* a essere falso.

## 1. Il rilievo, verificato sul DB vivo

`ORD0000580` ha **`fatturazione_trigger = 'CONFERMATO'`** (il default di
`billing_account.fatturazione_ordini`) ed è già `EVASO`; il suo `DDT0000326` è
`CONSEGNATO`, causale `VENDITA` fatturabile, BA valorizzato.

**Il comportamento del motore è corretto**: con trigger `CONFERMATO` vale la
regola XOR — fattura l'ordine alla conferma, il DDT non transita **mai** in
commessa (cintura `src_fatturazione_trigger != 'CONFERMATO'` nel lister, che
questo brief **non tocca**).

**È il messaggio a essere sbagliato.** In `script.fn_available_actions_ddt` il
classificatore delle reason ha tre soli esiti:

| condizione | reason |
| --- | --- |
| esiste riga in `fn_list_ddt_da_pushare` | *(azione push offerta)* |
| segmento `ALLOCATA` | `DDT_GIA_INVIATO` |
| segmento `EMESSA` | `DDT_GIA_FATTURATO` |
| **tutto il resto** | `DDT_NON_PUSHABILE` → *«dev'essere spedito o consegnato»* |

L'ultimo ramo è un **catch-all**: assorbe cause tra loro diverse e le racconta
tutte come un problema di stato di spedizione.

## 2. Le cause che oggi finiscono nel catch-all (censimento sul lister)

Dal `WHERE` vivo di `fn_list_ddt_da_pushare` (riverificato su DB 2026-07-19), un
DDT non eleggibile può esserlo per **sette** ragioni distinte — non cinque: il
primo censimento aveva omesso i casi 6 e 7, che il `WHERE` esclude con predicati
propri (`NOT is_abortito`, `codice_interno <> 'RESO'`).

Le cause non sono tutte dello stesso tipo, e la distinzione **è portante** per la
regola di precedenza (§3, Decisione E):

- **di documento** = vale per l'intero DDT (tutto-o-niente): non c'è competizione;
- **di riga** = può differire riga per riga dello stesso DDT.

| # | causa | predicato vivo | tipo | messaggio attuale | permanente |
| --- | --- | --- | --- | --- | --- |
| 1 | ordine sorgente `fatturazione_trigger = 'CONFERMATO'` (XOR) | `src_fatturazione_trigger != 'CONFERMATO'` | **riga** | **falso** — mai soddisfacibile | sì, ed è il **default** |
| 2 | causale di trasporto **non fatturabile** (DL-28) | `caus.fatturabile IS TRUE` (JOIN) | **documento** | **falso** — non è questione di stato | sì |
| 3 | stato DDT **prima** dello stato-trigger (merce in viaggio) | `sdd.ordine >= sdd_trg.ordine` | **riga** | **corretto** — è il caso per cui il testo è nato | no |
| 4 | standalone senza `billing_account` risolvibile | `COALESCE(...billing_account...) IS NOT NULL` | **documento** | **falso** | ~ |
| 5 | contatore differenza ≤ 0 (merce resa/già fatturata altrove) | `quantita_push > 0` (filtro finale) | **riga** | **falso** | sì |
| 6 | DDT **ANNULLATO** | `NOT sdd.is_abortito` | **documento** | **falso** | sì (morto) |
| 7 | DDT **RESO** | `sdd.codice_interno <> 'RESO'` | **documento** | **falso** | sì (morto) |

Solo **1 caso su 7** (il 3) è descritto correttamente. Cinque sono **permanenti**:
nessuna azione dell'utente li sblocca, ma il testo suggerisce di attendere/avanzare
lo stato.

## 3. Cosa serve — decisioni chiuse (2026-07-19)

Il classificatore deve **distinguere le cause**. Le cinque decisioni sotto sono
state prese; questa sezione è ora prescrittiva, non più aperta.

### Decisione A — Come il DB conosce il motivo (fonte unica)

La logica di esclusione vive nel `WHERE` del lister e dipende da fatti **per-riga**
(il trigger arriva a ogni riga via `ordini_righe_fulfillment`; righe diverse dello
stesso DDT possono avere trigger diversi). Due strade: (a) ricopiare i predicati
come `EXISTS` nella capability — fragile, duplica il lister, diverge; (b) far
restituire al **lister** anche le righe scartate con il loro motivo, fonte unica.

→ **Scelta: (b).** È l'unica che rende impossibile la divergenza fra chi decide
l'esclusione e chi la spiega. È **lavoro architetturale**, non manutenzione di
testi — la stima va rivista di conseguenza (intestazione). Il classificatore della
capability non riscrive i predicati: consuma il motivo dalla fonte unica.

### Decisione B — Quali cause hanno un ramo proprio

- **`DDT_FATTURA_DA_ORDINE`** (caso 1) — *«la fatturazione è a carico dell'ordine
  (conferma): questo DDT non transita in commessa»*.
  ⚠️ **Speculare esatto di `ORDINE_FATTURA_DA_DDT`**, che `fn_available_actions_ordine`
  espone da giugno. Metà della regola XOR è spiegata all'utente, l'altra metà no:
  è **quell'asimmetria** il difetto, più del singolo messaggio.
- **`DDT_SOLO_TRASPORTO`** (caso 2) — *«causale non fatturabile: il documento
  accompagna la merce senza generare fatturazione»* (DL-28).
- Casi **6/7 (annullato/reso)**: nessun ramo proprio — sono documenti morti, già
  segnalati come tali nel drawer (Tag di stato `stato_descrizione` +
  `statoDdtSeverity`, `DdtDrawer.vue` righe 521-523, verificato 2026-07-19);
  restano nel generico riscritto.
- Casi **4/5 (senza BA, contatore)**: restano nel generico riscritto (§ Decisione C).

### Decisione C — Testo del generico

Il generico non può più affermare «dev'essere spedito o consegnato» (vero solo nel
caso 3). Formulazione neutra, es. *«questo DDT non è al momento inviabile a
commessa»* — non mente su nessuna delle cause residue.

### Decisione D — Superficie UI: **tooltip discreto**, non banner

Un tooltip è *a domanda* (compare all'hover sul pulsante grigio); un banner è
sempre visibile. Le cause permanenti (1, 2, 5, 6, 7) come banner sarebbero rumore
perpetuo — e il caso 1 è il **default**, quindi colpirebbe quasi ogni DDT. Il
tooltip dissolve il problema: la spiegazione c'è per chi la cerca, senza urlare.
Costo FE zero: i drawer leggono già `can_push_commessa_reason_key` con `te(key)`.

### Decisione E — Precedenza (regola a due livelli)

Quando righe dello stesso DDT cadono in bucket diversi, la capability riporta
**un** motivo. Regola:

1. **Prima le cause di documento** (tutto-o-niente): annullato/reso → solo-trasporto
   → senza-BA. Se una vale, blocca tutto: domina senza ambiguità.
2. **Poi, fra le cause di riga, vince la più azionabile**: merce in viaggio (basta
   avanzare lo stato) prima di XOR e contatore (permanenti). Principio: dire la
   cosa più vicina a sbloccare qualcosa. Siccome è un tooltip (Decisione D), è un
   *consiglio*, non un verdetto — quindi non "mente" sul resto.

Ordine finale dal più forte: `annullato/reso` → `solo-trasporto` → `senza-BA` →
`merce in viaggio` → `XOR` → `contatore`.

**Vincoli sul risultato:**

- **La logica di push non si tocca**: cintura XOR, JOIN causale fatturabile,
  contatore, `ordine >= trigger` restano **identici**. Cambia solo *come si spiega*
  un'esclusione già decisa altrove.
- **Namespace**: le reason DDT usano già `vendite.ddt.push_commessa_reason.*` —
  corretto, **mantenerlo**.

## 4. Cosa comunicare indietro a BE/FE

### Backend — nulla da fare

Il BE **non** consuma i codici `reason` né le `reason_key`: le trasporta opache
nell'envelope della capability. Verificato — nessun riscontro in `backend/`
(fuori dai test). Nessun mapping a HTTP status, nessun adeguamento in
`error_policies`. La slice è a impatto BE zero.

### Frontend — 3 chiavi nuove + 1 testo da cambiare

Da aggiungere in `it.json` **e** `en.json` sotto `vendite.ddt.push_commessa_reason`
(namespace conforme allo standard radici; testi proposti, adattabili):

| `reason` (codice DB) | `reason_key` | testo it proposto |
| --- | --- | --- |
| `DDT_FATTURA_DA_ORDINE` | `…fattura_da_ordine` | «La fatturazione è a carico dell'ordine (conferma): questo DDT non transita in commessa.» |
| `DDT_SOLO_TRASPORTO` | `…solo_trasporto` | «Causale non fatturabile: il documento accompagna la merce senza generare fatturazione.» |
| `DDT_MERCE_IN_VIAGGIO` | `…merce_in_viaggio` | «Non ancora inviabile a commessa: dev'essere spedito o consegnato.» |

**Testo da CAMBIARE** — `…non_pushabile` (generico) non deve più affermare una
condizione di stato: oggi dice «dev'essere spedito o consegnato» (che è passato al
ramo `merce_in_viaggio`). Nuovo testo neutro proposto: «Questo DDT non è al momento
inviabile a commessa.» — copre senza-BA / contatore / annullato / reso.

I codici `reason` (`DDT_*`) **non** sono chiavi i18n: non toccarli.

### ⚠️ Nota FE sulla presentazione — la Decisione D non è (ancora) rispettata

Il brief aveva scelto **tooltip discreto**, non banner (Decisione D §3), proprio
per evitare che le cause permanenti facciano rumore. Ma il drawer DDT oggi mostra
la reason con un `<Message severity="info">` **sempre visibile** quando la chiave
risolve (`DdtDrawer.vue` ~riga 547), non un tooltip all'hover.

Conseguenza: appena il FE aggiunge la traduzione `fattura_da_ordine`, **ogni** DDT
consegnato di un ordine a trigger `CONFERMATO` — cioè il default — mostrerà un
banner info permanente. Il DB ora dice il vero; ma «vero e sempre in faccia» non è
l'esito che la Decisione D voleva.

Questo comportamento **preesiste** al mio intervento (il `<Message>` mostrava già
il vecchio catch-all su ogni DDT non pushabile): non lo introduco, lo rendo solo
più evidente perché il messaggio ora è corretto e frequente. Decisione FE, non DB:

- opzione minima — tenere il `<Message>` e accettare il banner sulle cause
  permanenti (è pur sempre `severity=info`, discreto);
- opzione allineata a D — rendere la reason come **tooltip sul pulsante disabilitato**
  invece che come `<Message>` fisso, oppure mostrare il `<Message>` solo per la
  causa azionabile (`merce_in_viaggio`) e il tooltip per le permanenti.

Il DB non cambia in nessuno dei due casi: espone la stessa `reason_key`.

#### ✅ Risolta (2026-07-20) — presa la strada allineata a D, senza tocchi DB

Implementazione FE nei drawer **DDT e Ordini** (ordini per simmetria XOR:
`fattura_da_ddt` è la causa permanente speculare, stesso rumore perpetuo):

- il `<Message>` fisso è stato **rimosso**;
- quando `can_push_commessa=false` con reason valorizzata, il drawer
  **sintetizza** l'entry `push_commessa` con `enabled:false` +
  `reason`/`reason_key`, nella stessa shape delle azioni emesse dal DB, e la
  accoda ad `available_actions` prima del mapper condiviso
  (`mapAvailableActionsToDrawerActions`), che già rende `enabled:false` come
  pulsante **disabilitato con tooltip** (pattern guard-righe, «disabled, mai
  nascosto») con fallback fail-visible `labelOrCode`;
- risultato: il pulsante «Invia a commessa» è **sempre presente** — attivo se
  pushabile, grigio col motivo all'hover altrimenti. Le cause permanenti non
  urlano più; la spiegazione c'è per chi la cerca, come voleva la D.
- Nota tecnica: i tooltip sui pulsanti disabilitati funzionano nei browser
  correnti (Chrome 119+/Firefox: gli eventi mouse vengono emessi anche sugli
  elementi `disabled`) — stesso meccanismo già in uso per le azioni
  `requires_righe`.

I drawer **preventivi/offerte** conservano il `<Message>`: le loro cause
prevalenti sono azionabili (non accettato) e il rumore permanente lì è marginale
(`gia_generato` offerte) — eventuale allineamento è un follow-up a parte.

## 5. Impatto sulla validazione in corso (contesto utile)

Il rilievo è emerso mentre si validava la slice DDT-resi-dashboard: il giro di
test su `ORD0000580` **non è recuperabile** (con trigger `CONFERMATO` quel DDT
non pusherà mai e la merce è già fatturata via ordine). Il test riparte da un
ordine con `fatturazione_trigger ∈ {SPEDITO, CONSEGNATO}`. Nessun dato da
correggere: la situazione è legittima, era solo mal descritta.

## 6. Avanzamento

Decisioni A–E: ✅ chiuse (§3). Implementazione:

| # | Step | Stato |
| --- | --- | --- |
| 1 | **Fonte unica** `fn_ddt_push_diagnosi` (Decisione A) — `20260719-15`; equivalenza col lister 0/0 verificata | ✅ |
| 2 | Capability consuma il motivo + precedenza a due livelli (Decisione E) — `20260719-16` | ✅ |
| 3 | Ramo `DDT_FATTURA_DA_ORDINE` (caso 1, speculare di `ORDINE_FATTURA_DA_DDT`) | ✅ |
| 4 | Ramo `DDT_SOLO_TRASPORTO` (caso 2) + ramo `DDT_MERCE_IN_VIAGGIO` (caso 3, rifinitura §3) | ✅ |
| 5 | Generico riscritto, non più basato sullo stato (casi 4/5/6/7) — Decisione C | ✅ (testo FE §4) |
| 6 | pgTAP `test-fn-available-actions-ddt-reason-catch-all-v1.sql` **7/7**: equivalenza + un caso per ramo + precedenza + namespace | ✅ |
| 7 | Migrate dev + pgTAP verdi | ✅ 2026-07-19 |
| 8 | Manuale funzione `vendite/manual/fn_ddt_push_diagnosi.md` | ✅ |
| 9 | Rigen doc auto-gen (crea `funzioni/fn_ddt_push_diagnosi.md`) + comunicazione §4 a BE/FE | ✅ (commit `8b6614539`) |
| 10 | Commit DB | ✅ 2026-07-19 (`8b6614539`, PR #1020) |
| 11 | **FE**: 3 traduzioni + generico riscritto (it/en) · Decisione D applicata — tooltip su pulsante disabilitato al posto del banner, drawer DDT **e** Ordini (§4-bis) · guard i18n verde · build verde | ✅ 2026-07-20 |
| 12 | Validazione in-app Tid — ✅ 2026-07-20 su ORD0000608/DDT0000337 (ramo `fattura_da_ordine`, il default): reason corretta e pulsante disabled+tooltip. Durante la validazione emersi e chiusi due difetti FE collaterali (readonly-leak drawer impilati dai Passaggi + freshness liste KeepAlive — v. brief dashboard collegato). ⚠️ Rami `merce_in_viaggio`/`gia_inviato`-da-DDT non esercitabili coi dati attuali: **tutti i 42 BA dev hanno `fatturazione_ordini=CONFERMATO`** — restano coperti dal pgTAP; alla prima anagrafica con trigger `SPEDITO`/`CONSEGNATO` si esercitano in-app | ✅ |

### 6b. Nota sulla fonte unica (Decisione A) — cosa è stato fatto e cosa no

`fn_ddt_push_diagnosi` è una **lettura parallela** degli stessi predicati del
lister, non una riscrittura del lister. Scelta di rischio: il lister è critico
(~13 pgTAP dipendono da lui) e la delega letterale non dà alcun beneficio visibile.
La garanzia anti-drift — che i due non possano divergere — è il **test 1 di
equivalenza** (`diagnosi motivo NULL == output lister`): se qualcuno cambia
l'eleggibilità in un solo posto, il test diventa rosso e forza l'allineamento.
È il contratto della fonte unica, senza il rischio di rifattorizzare il lister.
La delega letterale resta un follow-up sicuro, se e quando serve.

## 7. Riferimenti

**Documento BE/FE collegato**: [brief-be-fe-ddt-resi-dashboard.md](../work-in-progress/brief-be-fe-ddt-resi-dashboard.md)
(slice da cui è emerso il rilievo; FE-5 gate solo-trasporto nel drawer DDT).

**Prodotto da questo brief:**

- Fonte unica: `db/changelog/migrations_v2/20_code/vendite/20260719-15-create-fn-ddt-push-diagnosi-mctit.yaml`
- Capability: `db/changelog/migrations_v2/20_code/script/20260719-16-update-fn-available-actions-ddt-reason-catch-all-mctit.yaml`
- pgTAP: `db/pgtap/script/test-fn-available-actions-ddt-reason-catch-all-v1.sql`
- Manuale: `docs/it/dbzero/vendite/manual/fn_ddt_push_diagnosi.md`

**Contesto:**

- Caso reale: `DDT0000326` (id 504, CONSEGNATO) / `ORD0000580` (trigger CONFERMATO, EVASO)
- Definizione viva capability: `docs/it/dbzero/script/funzioni/fn_available_actions_ddt.md`
- Gemella con il ramo già presente: `docs/it/dbzero/script/funzioni/fn_available_actions_ordine.md`
- Predicati di eleggibilità (lister): `docs/it/dbzero/vendite/funzioni/fn_list_ddt_da_pushare.md`
- Consumatore FE: `frontend/src/vendite/ddt/components/DdtDrawer.vue` + `locales/{it,en}.json`
