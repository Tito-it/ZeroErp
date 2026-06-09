# Guida — Gestione Preventivi vendita

> **Ultima revisione**: 15 maggio 2026 — modello revisione attiva derivata
> (post refactor `is_attiva` su `vw_preventivi` + copia componenti BoM in
> `fn_crea_revisione_preventivo`).
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) / [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) / [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti)
> * [vendite.preventivi_indirizzi](/dbzero/vendite/tabelle/preventivi_indirizzi)
> * [vendite.vw_preventivi](/dbzero/vendite/manual/vw_preventivi) / [vendite.vw_preventivi_lista](/dbzero/vendite/manual/vw_preventivi_lista)
> * [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi) / [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni DB:
>
> * [vendite.fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo) — crea nuova revisione da EMESSO
> * [vendite.fn_preventivo_riga_componenti_init](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_init) — popola componenti BoM su riga padre composito
> * [vendite.fn_preventivo_riga_componenti_preview](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview) — read-only, suggerimento prezzi pre-save
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver pricing bundle-aware
> * [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) — azioni disponibili sullo stato corrente
>
> **Vedi anche** — API e service backend:
>
> * [API Preventivi](/backend/vendite/manual/api_preventivi)
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
> * [API Approvazioni prezzo (workflow L3)](/backend/vendite/manual/api_approvazioni_prezzo)
>
> **Vedi anche** — guide correlate:
>
> * [Gestione Listini e Pricing v5](/guide/gestione-listini)
> * [Fatturazione end-to-end](/guide/fatturazione) — il push commessa attiva la pipeline fatturazione
> * [Documenti e stampe](/guide/documenti-e-stampe) — generazione PDF preventivo
> * [Gestione Pratiche](/guide/gestione-pratiche) — flusso approvazione prezzo L3
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom)

---

## 1. Cosa è un preventivo

Un preventivo è l'**offerta commerciale** che l'azienda emette verso un cliente per
una specifica fornitura. Risponde alla domanda: *"Quanto costerebbe questo cliente
se accettasse questa configurazione di articoli oggi?"*

Caratteristiche di base:

- è intestato a un **billing account** (cliente) e a una **utility** (servizio:
  Gas, Energia, Idrico, oppure "Base" per commercio)
- raccoglie **righe** (articoli con quantità, UoM, prezzo) e produce un totale
- ha un **ciclo di vita** con stati che vanno da bozza a emesso, fino ad
  accettato o rifiutato
- può essere **revisionato** un numero qualsiasi di volte mantenendo lo stesso
  numero documento
- quando accettato, viene **spinto in commessa** che a sua volta alimenta il
  ciclo di fatturazione

Il numero documento è auto-generato (prefisso `PRV`) e non modificabile.

---

## 2. Le entità in gioco

### 2.1 Testata `preventivi`

Contiene il contesto commerciale del preventivo:

- **chi** (`billing_account_id`, `istanza_utility_id`)
- **per cosa** (`utility_id`)
- **quando** (`data` di emissione, `validita_dal`/`validita_al` dell'offerta,
  `competenza_mese` per la fatturazione downstream)
- **chi emette** (`emittente_fiscale_id`)
- **come fattura** (`fatturazione_immediata`, `valuta_id`, `termine_pagamento_id`)
- **stato** corrente (`stato_doc_preventivo_id`)
- **revisione** (`numero` + `rev`, l'attivazione è derivata — vedi §4)
- **totali** (`totale_imponibile`, `totale_iva`, `totale_documento`) ricalcolati
  da trigger sulle righe

I totali non si scrivono dall'API: sono il riassunto delle righe e vengono
mantenuti coerenti dal database.

### 2.2 Righe `preventivi_righe`

Ogni riga rappresenta una voce dell'offerta:

- articolo + UoM operativa + quantità
- prezzo unitario, sconto percentuale, IVA
- ordine di presentazione

#### La quantità e l'unità di misura operativa

L'operatore inserisce la quantità **nell'unità di misura che ha scelto** (la "UoM
operativa": per esempio *scatole*, anche se l'articolo a magazzino è contato in
*pezzi*). È il sistema, non l'operatore, a tradurla nell'unità di misura "base"
usata per i calcoli interni: se una scatola contiene 6 pezzi e si inseriscono 2
scatole, il sistema registra automaticamente 12 pezzi.

In pratica:

- l'operatore vede e digita **2** (scatole) — è il dato di partenza;
- il sistema calcola e salva **12** (pezzi) — è il valore derivato;
- il fattore di conversione (6) viene "fotografato" sulla riga al momento
  dell'inserimento, così resta stabile anche se in futuro cambia a catalogo.

La quantità **può essere negativa** (per gestire resi o storni); non può essere
zero. Questa conversione funziona allo stesso identico modo su preventivi, offerte
e contratti.

Il prezzo unitario può venire dal **resolver pricing** (riempito automaticamente
al cambio articolo/UoM) oppure essere inserito manualmente dall'operatore, con
controlli L1/L2/L3 di autorizzazione che vedremo in §6.

Per gli articoli **compositi** (kit, bundle) la riga è solo la "testata" del
gruppo: i prezzi reali stanno nei componenti BoM (§5).

#### Quali articoli possono stare su un preventivo

Sul preventivo puoi mettere **merce** e **servizi una tantum**. **Non** puoi
inserire articoli a **servizio ricorrente** (canone/abbonamento): se ci provi, il
sistema rifiuta la riga con un messaggio che ti invita a usare l'**offerta
commerciale**. Il motivo è semplice — la ricorrenza ha un suo ciclo di vita
([offerta → contratto → fatturazione periodica](gestione-offerte-commerciali.md))
che non passa dal preventivo. Ogni articolo porta con sé questa "natura" dal
catalogo, e l'operatore non può cambiarla sulla riga.

> **Come funziona sotto il cofano.** Ogni articolo ha una *natura di vendita*
> (`catalogo.articoli.natura_vendita_id` → `config.nature_vendita`) con una
> *destinazione*: `MERCE → ordine`, `SERVIZIO_UNA_TANTUM → commessa`,
> `SERVIZIO_RICORRENTE → contratto`. Quando aggiungi una riga, un trigger
> (`trgfn_preventivi_righe_set_natura_vendita`) copia e **congela** la natura
> dall'articolo sulla riga. Se la destinazione è `CONTRATTO`, il trigger blocca
> subito l'inserimento con l'errore `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`: il
> blocco è *data-driven* (vale per qualunque natura mappata a contratto) e scatta
> all'inserimento, non alla conferma. Le destinazioni operative del preventivo
> sono quindi solo **ordine** e **commessa**.

### 2.3 Componenti BoM `preventivi_righe_componenti`

Quando una riga punta a un articolo `is_composito = TRUE`, il sistema crea
automaticamente un record per ogni **componente** definito nella BoM
dell'articolo. Il prezzo del padre è la **somma pesata** dei prezzi figli, mai
inserita a mano.

I componenti BoM portano:

- riferimento al componente del catalogo + UoM + quantità (= padre × `coeff_qta`)
- prezzo unitario (modificabile dall'operatore con autorizzazioni)
- snapshot del coefficiente quantità al momento della creazione
- origine prezzo (PROMO / CONTRATTO_OVERRIDE / CONTRATTO_LISTINO / CATEGORIA / MANUALE)
- stato approvazione prezzo (L3)

La struttura del bundle (quali componenti, in che quantità relative) è
**immutabile per documento**: l'operatore può cambiare i prezzi, non la
composizione. Vedi [modello componenti BoM](/dev/manual/modello-componenti-bom)
per il dettaglio.

### 2.4 Indirizzi `preventivi_indirizzi`

Snapshot multi-tipo (consegna, fatturazione, ecc.) congelati alla creazione.
Sono **autonomi**: una modifica all'indirizzo del cliente in anagrafica non
retroagisce sul preventivo già emesso. La revisione li copia 1:1 nella nuova rev.

### 2.5 Documenti generati

Quando il preventivo viene stampato/inviato, il sistema produce un PDF tramite
il motore documentale parametrico:

- in stato **DRAFT** la stampa è solo **anteprima** (PDF temporaneo, niente
  persistenza)
- al passaggio **DRAFT → EMESSO** il PDF viene generato e salvato come
  documento ufficiale collegato al preventivo
- da EMESSO in poi le ristampe restituiscono il documento salvato (non
  rigenerato), per preservare il layout storico

Vedi [documenti e stampe](/guide/documenti-e-stampe) per i template e il motore.

---

## 3. Ciclo di vita e stati

### 3.1 Stati e transizioni

Gli stati sono governati da `config.stati_doc_preventivi` e le transizioni
ammesse da `config.transizioni_stati_preventivi`:

| Stato | Significato | Modificabile? |
|---|---|---|
| `DRAFT` | Bozza in costruzione | Sì: testata, righe, indirizzi |
| `EMESSO` | Inviato al cliente, in attesa di risposta | No (escluso azioni di stato) |
| `ACCETTATO` | Cliente ha accettato — pronto per push commessa | No |
| `RIFIUTATO` | Cliente ha rifiutato — chiusura negativa del numero | No (terminale) |
| `SCADUTO` | Validità offerta scaduta automaticamente (job notturno) | No (terminale) |
| `ANNULLATO` | Annullamento manuale | No (terminale, **abortito**) |

Le transizioni manuali permesse:

```text
DRAFT      → EMESSO     (emetti)
EMESSO     → ACCETTATO  (accetta)
EMESSO     → RIFIUTATO  (rifiuta)
EMESSO     → ANNULLATO  (annulla)
```

`EMESSO → SCADUTO` è automatica (job notturno quando supera `validita_al`).

Le azioni disponibili in ogni momento sono esposte dal backend tramite
[`fn_available_actions_preventivo`](/dbzero/script/funzioni/fn_available_actions_preventivo)
e arrivano al frontend come array `available_actions`. Le capability derivate
(`can_edit_testata`, `can_edit_righe`, `can_push_commessa`, `can_create_revisione`)
governano la disabilitazione dei pulsanti.

### 3.2 Stati terminali e stato "abortito"

`config.stati_doc_preventivi` ha un campo `is_abortito` che marca lo stato
**ANNULLATO** come "rinuncia". Tutti gli altri stati terminali (RIFIUTATO,
SCADUTO, ACCETTATO) sono conclusioni del documento ma **non rinunce**: il
numero ha trovato un esito definitivo.

Questa distinzione è importante per la logica revisione (§4): solo gli stati
abortiti permettono al predecessore di "riprendere vita".

---

## 4. Revisioni

### 4.1 Cos'è una revisione

Una revisione è una **nuova istanza** dello stesso numero preventivo, con un
contatore `rev` incrementato. Permette di aggiornare l'offerta dopo che il
cliente ha chiesto modifiche, senza perdere lo storico della precedente
proposta.

```text
PRV-0001 rev=0  EMESSO     ← prima offerta inviata
PRV-0001 rev=1  DRAFT      ← revisione in corso (post-creazione)
```

Caratteristiche:

- una revisione si crea **solo da uno stato EMESSO**
- non possono coesistere due revisioni DRAFT per lo stesso numero
- la nuova revisione nasce **DRAFT** e diventa la "rev attiva" del numero
- la rev precedente resta in DB come storico (stato EMESSO conservato)

### 4.2 Cosa viene copiato nella nuova rev

La funzione [`fn_crea_revisione_preventivo`](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo)
copia in transazione atomica:

- testata (campi commerciali + dati cliente)
- righe attive (`preventivi_righe` con `attivo=TRUE` e `quantita > 0`)
- componenti BoM (`preventivi_righe_componenti`, con FK rimappata sulle nuove
  righe via `ROW_NUMBER`)
- indirizzi (`preventivi_indirizzi`)

Non viene copiato lo stato (la nuova rev è sempre DRAFT) né il numero documento
generato per la rev precedente (il nuovo rev mantiene lo stesso `numero`).

### 4.3 Predicato `is_attiva` derivato

ZeroERP non mantiene un flag persistito "questa è la rev attiva": il predicato
è **calcolato dalla view `vw_preventivi`** come:

> "è la rev viva del numero" = "non esiste una rev superiore non-abortita per
> lo stesso numero"

Conseguenza pratica nei casi limite:

| Sequenza | rev N attiva? | rev N+1 attiva? |
|---|---|---|
| rev 0 EMESSO, rev 1 DRAFT | no (superseded) | sì |
| rev 0 EMESSO, rev 1 ANNULLATO | **sì** (rev 1 è abortita, non conta) | no |
| rev 0 EMESSO, rev 1 RIFIUTATO | no (rev 1 conclude il numero negativamente) | sì |

Il caso "**revisione annullata rifluisce al predecessore**" è quello tipico
dell'operatore che sbaglia a revisionare: la revisione viene annullata e il
preventivo originale torna disponibile per nuove operazioni (annullamento,
accettazione, ulteriore revisione). Senza ricorrere a interventi manuali.

### 4.4 Filtro lista e storico

La lista preventivi mostra di default solo le rev attive (una per numero).
Esiste un toggle "Mostra storico revisioni" che espone tutte le righe,
incluse quelle annullate o superseded. Il filtro lato API è il parametro
`solo_attiva` (default `true`).

---

## 5. Articoli compositi e BoM

### 5.1 Cosa succede quando aggiungi un composito

Inserendo una riga preventivo con articolo `is_composito = TRUE`, il sistema:

1. apre il dialog di **anteprima componenti** che pre-popola i prezzi dei
   figli BoM via [`fn_preventivo_riga_componenti_preview`](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview)
2. l'operatore conferma (oppure modifica i prezzi suggeriti, con controlli
   L1/L2/L3) e salva
3. il backend crea in transazione atomica:
   - una riga padre in `preventivi_righe` con prezzo iniziale 0 (placeholder)
   - N righe figlie in `preventivi_righe_componenti` (una per ogni figlio
     attivo nella BoM valida alla data del preventivo)
4. trigger DB ricalcola il prezzo padre come SUM(figli × `coeff_qta_snapshot`)

Se la BoM del padre non ha figli validi alla data del preventivo, il sistema
solleva `E_DOC_COMPOSITO_BOM_VUOTA` e blocca la creazione della riga (la
configurazione del catalogo è incoerente per la data scelta).

### 5.2 Cosa può modificare l'operatore

Per BoM contratto immutabile (decisione 2026-05-13):

- ✅ **prezzi unitari** dei componenti, con controlli di autorizzazione
- ✅ **IVA** del componente (deve restare coerente col padre)
- ❌ **non** può aggiungere o rimuovere componenti dalla composizione
- ❌ **non** può cambiare `coeff_qta` (è snapshot immutabile)

Componenti **obbligatori** (definiti nella BoM con `obbligatorio=TRUE`) non
ammettono prezzo zero: il trigger DB rifiuta con
`E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`. Componenti opzionali ammettono
prezzo zero.

### 5.3 Esposizione in fattura

Ogni componente porta un flag `esposto_in_fattura` (proviene dalla BoM):

- `TRUE` → in fattura compare come riga descrittiva separata (oltre al padre)
- `FALSE` → in fattura non appare; il suo prezzo è già incluso nel totale padre

Il flag è solo di **presentazione finale**, non incide sulla composizione del
preventivo o sui calcoli.

---

## 6. Pricing applicato

### 6.1 Resolver

Quando l'operatore seleziona articolo + UoM, il backend chiama il
[resolver pricing v5](/guide/gestione-listini#3-resolver--i-3-stadi-in-dettaglio)
che valuta in sequenza promo → contratto → categoria/listino e restituisce un
prezzo candidato + origine. Il frontend pre-compila il campo prezzo nel form.

Per articoli compositi il resolver è **bundle-aware**: passa il padre come
contesto (`p_articolo_padre_contesto`), così se esiste un listino bundle
dedicato (`listini_righe_componenti`) i figli ricevono prezzi specifici per
quel bundle, altrimenti fallback al pricing standalone.

### 6.2 Controlli L1 / L2 / L3

L'operatore può modificare il prezzo proposto dal resolver. Le modifiche
passano per tre livelli di autorizzazione, gestiti dal motore L1/L2/L3 dei
limiti pricing:

- **L1 — Override manuale**: il flag `prezzo_override_manuale` deve essere
  abilitato sul profilo operatore
- **L2 — Limiti sconto/maggiorazione**: la deviazione rispetto al prezzo
  resolver non può eccedere le soglie configurate (es. sconto max 15%). Oltre
  il limite, il save è bloccato salvo richiesta approvazione
- **L3 — Workflow approvazione**: l'operatore può chiedere autorizzazione al
  superiore tramite una **pratica APPROVAZIONE_PREZZO** dedicata. La riga
  resta in stato `PENDING` finché approvata o rifiutata

Vedi [API Approvazioni prezzo](/backend/vendite/manual/api_approvazioni_prezzo)
e [gestione pratiche](/guide/gestione-pratiche) per il workflow completo.

### 6.3 Snapshot resolver

Ogni riga (e ogni componente BoM) salva nel campo `prezzo_resolver_context` un
**audit JSONB** con i valori che hanno determinato il pricing: origine, listino
applicato, contratto/promo riferiti, eventuale override manuale. Questo
snapshot sopravvive a future modifiche del listino e permette di ricostruire
"perché in quel momento il prezzo era X".

---

## 7. Workflow end-to-end

### 7.1 Flusso tipico

```text
   ┌──────────────────┐
   │  Nuovo preventivo │
   │  (Nuovo cliente   │
   │   o esistente)    │
   └────────┬──────────┘
            │
   ┌────────▼──────────┐
   │     DRAFT         │
   │ Operatore compila │
   │ testata + righe   │
   └────────┬──────────┘
            │
            │ Stampa anteprima PDF se serve
            │
   ┌────────▼──────────┐    ┌─────────────────────┐
   │     EMESSO        │◀───┤  Genera PDF, salva  │
   │ Cliente vede      │    │  in documenti       │
   └────┬────┬──────┬──┘    └─────────────────────┘
        │    │      │
   ┌────▼─┐ ┌▼──┐ ┌─▼─────────┐ ┌─────────┐
   │ACCETT│ │RIF│ │  ANNULLATO│ │ SCADUTO │
   └────┬─┘ └───┘ └─────┬─────┘ └─────────┘
        │               │
        │               │ (job notturno)
        │
   ┌────▼──────────────────┐
   │   Push commessa       │
   │ (transizione          │
   │  EVASO automatica)    │
   └───────────────────────┘
```

### 7.2 Revisione (deviazione dal flusso)

Da EMESSO l'operatore può creare una nuova rev DRAFT, modificare e ri-emettere.
Il numero documento resta lo stesso, il contatore `rev` incrementa.

Una rev annullata torna a far valere il predecessore (vedi §4.3).

---

## 8. Push commessa e fatturazione downstream

Quando un preventivo arriva in stato **ACCETTATO**, l'operatore può eseguire
l'azione **push commessa**. Il sistema:

1. crea (o riusa) una commessa nel dominio `vendite.commesse`
2. trasforma le righe del preventivo in attività commessa
3. **espande** i compositi: ogni riga padre composita produce N attività
   commessa (una per ogni figlio attivo)
4. transiziona il preventivo a **EVASO** (terminale operativo positivo)

Da lì in poi la pipeline fatturazione opera sulle commesse e produce le
fatture. Vedi [fatturazione end-to-end](/guide/fatturazione) per il processo
downstream.

Importante: dopo il push commessa il preventivo è **congelato**. Modifiche
agli articoli vanno fatte sulle commesse, non più sul preventivo.

---

## 9. Casi d'uso operativi

### 9.1 Cliente chiede una modifica al preventivo già inviato

1. Apri il preventivo in stato EMESSO
2. Crea **nuova revisione** → rev N+1 DRAFT
3. Modifica righe / prezzi nella DRAFT
4. Emetti → la nuova rev diventa quella corrente, la precedente resta storico

### 9.2 L'operatore ha sbagliato la revisione

1. Sulla rev N+1 (DRAFT o EMESSO) clicca **Annulla**
2. Stato → ANNULLATO
3. La rev N (precedente) torna automaticamente "attiva" — l'operatore può
   accettarla, rifiutarla, oppure creare un'altra revisione

Non serve nessuna riattivazione manuale: la logica `is_attiva` derivata gestisce
il fallback per costruzione.

### 9.3 Cliente VIP richiede sconto oltre soglia

1. L'operatore modifica il prezzo riga oltre il limite L2
2. Il frontend rileva il blocco e propone "Richiedi approvazione"
3. Confermando, il sistema crea una pratica `APPROVAZIONE_PREZZO` collegata
   alla riga, e marca lo stato approvazione = `PENDING`
4. Il responsabile riceve la pratica nella coda approvazioni, decide
   APPROVATO / RIFIUTATO con eventuale nota
5. La riga si sblocca (approvato) o torna al prezzo precedente (rifiutato)

Vedi [API Approvazioni prezzo](/backend/vendite/manual/api_approvazioni_prezzo).

### 9.4 Articolo composito (es. "Kit installazione caldaia")

1. Aggiungi una riga selezionando il kit dal lookup articoli
2. Si apre automaticamente il dialog **anteprima componenti** con i figli BoM
   pre-popolati di prezzo (resolver bundle-aware)
3. Conferma o modifica prezzi singoli (con eventuali approvazioni L3 se servono)
4. Salva: la riga padre viene creata, i componenti sono persistiti come righe
   figlie, il prezzo padre = SUM(figli × coeff)
5. In EDIT successivo puoi modificare i prezzi figli dal pannello componenti;
   il padre si aggiorna automaticamente

### 9.5 Preventivo annullato e ricreato

L'annullamento è terminale. Per ripartire serve un nuovo preventivo (nuovo
numero PRV). Non c'è "ripristino" da ANNULLATO. La logica è: la sequenza
PRV-0042 è morta, ne emetti un'altra (PRV-0043).

---

## 10. Errori principali

Codici lanciati dal dominio preventivi (registrati in `error_policies`):

| Codice | HTTP | Quando |
|---|---|---|
| `E_PREV_VALIDAZIONE` | 400 | Payload incoerente (modalità, riferimenti) |
| `E_PREV_NOT_FOUND` | 404 | Preventivo / riga / componente inesistente |
| `E_PRICING_SCONTO_ECCESSIVO` | 400 | L2: sconto oltre limite, no richiesta approvazione |
| `E_PRICING_MAGGIORAZIONE_ECCESSIVA` | 400 | L2: maggiorazione oltre limite |
| `E_PRV_REVISIONE_STATO_NON_AMMESSO` | 400 | Crea revisione da stato diverso da EMESSO |
| `E_PRV_REVISIONE_BOZZA_ESISTENTE` | 400 | Esiste già una DRAFT per quel numero |
| `E_DOC_COMPOSITO_BOM_VUOTA` | 400 | Composito senza figli BoM validi alla data |
| `E_DOC_COMPONENTE_OBBLIGATORIO` | 400 | Tentativo disattivare componente obbligatorio |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | 400 | Prezzo 0 su obbligatorio |
| `E_BOM_IVA_DISCORDANTE` | 400 | IVA componente ≠ IVA padre (vincolo BoM) |
| `E_PREZZO_LISTINO_NON_TROVATO` | 400 | Resolver non trova listino applicabile |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | 400 | Modalità C: articolo non in contratto |

Per il dettaglio dei codici pricing e degli errori L1/L2/L3 vedi
[gestione listini §11](/guide/gestione-listini) e
[API Pricing](/backend/vendite/manual/api_pricing).

---

## 11. Pattern e principi di design

### 11.1 Stato derivato vs persistito

ZeroERP preferisce stati derivati dove possibile per evitare drift fra flag
e dati strutturali. `is_attiva` sui preventivi è l'esempio tipico: non c'è
una colonna che dice "questa è la rev attiva", c'è una vista che lo deriva
da (`rev`, stato del successore).

Vantaggio: nessun trigger di sincronizzazione, nessuna casistica
"il flag dice X ma i dati dicono Y", nuovi flussi non rompono la coerenza.

### 11.2 Snapshot e immutabilità

Le entità che vengono "fissate" al momento dell'emissione (indirizzi snapshot,
componenti BoM `coeff_qta_snapshot`, prezzo_resolver_context audit) **non
retroagiscono** ai cambiamenti dell'anagrafica/catalogo. Il preventivo è una
fotografia commerciale ad un istante.

Una revisione produce un **nuovo snapshot** ricalcolato sui dati correnti, non
modifica lo snapshot della rev precedente.

### 11.3 Trigger DB come ultima difesa

I controlli più stringenti (modalità contratto coerente, IVA BoM coerente,
intersezione BoM-listino valida) sono **trigger DB**: anche se un frontend
bypassa i controlli applicativi, il DB rifiuta. Backend e frontend hanno
controlli equivalenti per UX migliore (errori parlanti pre-roundtrip), ma
la fonte di verità è sempre il DB.

### 11.4 BoM modello unificato cross-dominio

Lo stesso modello componenti BoM viene riusato su `vendite.preventivi_righe`,
`vendite.contratti_righe`, `vendite.ordini_righe`, `vendite.ddt_righe` (e in
futuro acquisti). Stessi guard, stessi trigger di ricalcolo padre, stessa UI.
Vedi [modello componenti BoM](/dev/manual/modello-componenti-bom) per la
simmetria del pattern a 3 livelli (struttura, listino, documento).

---

## 12. Glossario rapido

| Termine | Significato |
|---|---|
| **Preventivo** | Offerta commerciale verso un cliente, ciclo di vita DRAFT → EMESSO → ACCETTATO/RIFIUTATO/ANNULLATO/SCADUTO |
| **Revisione** | Nuova istanza dello stesso numero preventivo con `rev` incrementato. Si crea da EMESSO |
| **is_attiva** | Predicato derivato: "non esiste rev superiore non-abortita per lo stesso numero" |
| **is_abortito** | Metadato di stato: TRUE solo per ANNULLATO. Marca la rev come rinuncia, abilita fallback al predecessore |
| **Composito** | Articolo con `is_composito=TRUE` che ha una distinta base (BoM). Prezzo padre = SUM figli × coeff |
| **BoM** | Bill of Materials, distinta base del composito (`articoli_componenti`). Immutabile per design |
| **L1/L2/L3** | Livelli di autorizzazione pricing: Override Manuale / Limiti soglie / Workflow approvazione |
| **Push commessa** | Trasferimento del preventivo ACCETTATO in commessa per innescare la fatturazione |
| **Snapshot** | Copia congelata di dati al momento di un evento. Non retroagisce ai cambi anagrafica |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi
[API Preventivi](/backend/vendite/manual/api_preventivi). Per il modello
componenti BoM e le decisioni di design vedi
[modello-componenti-bom](/dev/manual/modello-componenti-bom).*
