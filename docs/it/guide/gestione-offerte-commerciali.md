# Guida — Gestione Offerte commerciali

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) / [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) / [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti)
> * [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities)
> * [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) / [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — genera il contratto DRAFT dall'offerta ACCETTATA
> * [vendite.fn_genera_ordine_da_offerta](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta) — genera l'ordine DRAFT dall'offerta ACCETTATA
> * [script.fn_check_righe_documento](/dbzero/script/funzioni/fn_check_righe_documento) — le righe che un'offerta o un contratto non ammette più
> * [vendite.fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — crea una nuova revisione da EMESSA
> * [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione) — guard sulle transizioni di stato
> * [vendite.trgfn_offerte_commerciali_revisione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione) — porta la rev padre a SUPERATA
> * [vendite.fn_offerta_eccezione_componenti_init](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_init) — popola i componenti BoM su un'eccezione composita
> * [vendite.fn_offerta_eccezione_componenti_preview](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_preview) — anteprima prezzi componenti, read-only
> * [vendite.trgfn_offerte_commerciali_default_valuta](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_default_valuta) — valuta di default da resolver
> * [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) — azioni disponibili sullo stato corrente
>
> **Vedi anche** — guide correlate:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Contratti](/guide/gestione-contratti) — la destinazione dell'offerta accettata; modello simmetrico
> * [Gestione Preventivi](/guide/gestione-preventivi) — proposta puntuale (→ commessa); confronto in §1.2
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — cascata promo → contratto → categoria
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom) — simmetria cross-dominio

---

## 1. Cosa è un'offerta commerciale

Un'offerta commerciale è la **proposta di condizioni quadro** che l'azienda
sottopone a un cliente per una specifica utility, prima della firma. Risponde alla
domanda: *"A quali condizioni di prezzo proponiamo a questo cliente questo servizio,
e cosa diventa quando le accetta?"*

Caratteristiche di base:

* è intestata a un **billing account** (cliente), a una **istanza utility** e a una
  **utility** (Gas, Energia, Idrico, ecc.)
* parte **sempre da un listino di riferimento** (`listino_id` obbligatorio), con
  un'eventuale **variazione globale** (sconto o maggiorazione su tutto il listino)
* può contenere **eccezioni puntuali** per singoli articoli (prezzi personalizzati,
  esclusioni, articoli fuori listino) — esattamente come un contratto
* ha un **ciclo di vita** con stati da bozza a emessa, fino all'accettazione o al
  rifiuto, e supporta **revisioni**
* quando **accettata**, può prendere **una** di due strade alternative (mai
  entrambe): essere **spinta in un contratto** (push a contratto) — nasce un
  contratto in DRAFT che eredita 1:1 le condizioni, per la fornitura ricorrente —
  oppure **generare un ordine** one-shot (azione `genera_ordine`), per una vendita
  puntuale. Le due azioni sono **mutuamente esclusive**: vedi §1.1 e §8.bis

Il numero documento è auto-generato (prefisso `OFC`, trigger
`trgfn_offerte_commerciali_gen_codice`) e non modificabile.

### 1.1 Il collegamento offerta → contratto

L'offerta commerciale è il **documento che mancava** all'inizio del ciclo di vita
del contratto: formalizza la proposta di condizioni prima che il contratto esista.
Il legame è **1:1**: un'offerta accettata genera **un solo** contratto. Il legame
è registrato sul contratto (colonna `contratti.offerta_id`, con vincolo di unicità),
non sull'offerta — così la generazione è idempotente (vedi §8).

> **Contratto OPPURE ordine — mai entrambi (XOR).** Da un'offerta ACCETTATA si può
> generare *o* un contratto (fornitura ricorrente) *o* un ordine di vendita
> one-shot, ma **al massimo uno dei due**. La semantica è "both-or-neither": finché
> l'offerta è vergine, entrambe le azioni (`push_contratto` e `genera_ordine`) sono
> disponibili; appena se ne usa una, **entrambe spariscono in modo permanente**
> (vale anche se il documento generato viene poi annullato). Generare tutti e due
> significherebbe fatturare due volte lo stesso oggetto. Vedi §8.bis.

### 1.2 Offerta commerciale vs preventivo

Entrambi sono proposte al cliente, ma rispondono a esigenze diverse:

|                            | **Preventivo** (`PRV-*`)                                         | **Offerta commerciale** (`OFC-*`)                                              |
| -------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Cosa propone               | Una transazione puntuale: articoli + quantità + prezzi, *adesso* | Condizioni quadro: listino + variazione + eccezioni                            |
| Forma delle righe          | Righe da ordinare (ogni riga è una voce con prezzo)              | Eccezioni "delta del listino" (OVERRIDE / ESCLUSIONE / AGGIUNTA)               |
| Cosa genera l'accettazione | Una **commessa** → fattura una tantum                            | Un **contratto** in DRAFT (ricorrente) **oppure** un **ordine** one-shot — XOR |
| "Fotografia" congelata     | Prezzo riga-per-riga                                             | Versione del listino (`listino_versione_id`)                                   |

In breve: il preventivo è una proposta di **vendita puntuale**, l'offerta è una
proposta di **relazione duratura**. Per questo l'offerta è strutturalmente gemella
del contratto, non del preventivo.

> **Gli articoli a servizio ricorrente partono da qui.** Un articolo ricorrente
> (canone/abbonamento) **non** può essere messo su un preventivo (verrebbe
> rifiutato): la ricorrenza si avvia dall'offerta commerciale, che genera il
> contratto. L'offerta è quindi il punto d'ingresso unico per la fornitura
> ricorrente. Vedi [Gestione preventivi §2.2](gestione-preventivi.md).

---

## 2. Le entità in gioco

### 2.1 Testata `offerte_commerciali`

Contiene il contesto commerciale e i parametri di pricing:

* **chi** (`billing_account_id`, `istanza_utility_id`)
* **per cosa** (`utility_id`)
* **chi emette** (`emittente_fiscale_id`) — copiato 1:1 nel contratto generato
* **listino** (`listino_id` obbligatorio, `listino_versione_id` nullable — fissato
  all'emissione)
* **variazione globale** (`tipo_variazione_globale`, `valore_variazione_globale`) — opzionale
* **quando** (`validita_dal`, `validita_al` nullable = senza scadenza)
* **valuta** (`valuta_id`) — riempita di default dal resolver (vedi §9)
* **stato** corrente (`stato_doc_offerta_id`)
* **revisione** (`revisione_numero`, `revisione_padre_id` — vedi §4)
* **date evento** (`data_emissione`, `data_accettazione`, `data_rifiuto`,
  `data_annullamento`) — popolate dai trigger di transizione
* **`motivazione_rifiuto`** — testo libero, valorizzato alla chiusura negativa
  (RIFIUTATA o ANNULLATA)

### 2.2 Eccezioni `offerte_commerciali_eccezioni`

Come nei contratti, le righe **non** sono "articoli da ordinare", ma **eccezioni
al listino** — modificatori puntuali. Il campo `tipo_eccezione` (ENUM NOT NULL)
qualifica il tipo:

| `tipo_eccezione` | Significato                                                 | `prezzo_unitario` |
| ---------------- | ----------------------------------------------------------- | ----------------- |
| `OVERRIDE`       | Prezzo personalizzato per articolo **presente nel listino** | NOT NULL          |
| `ESCLUSIONE`     | Articolo del listino **non disponibile** per questo cliente | NULL              |
| `AGGIUNTA`       | Articolo **non presente nel listino**, aggiunto all'offerta | NOT NULL          |

Constraint principali:

* al massimo una riga OVERRIDE/ESCLUSIONE per `(offerta, articolo)` (unique parziale)
* al massimo una riga AGGIUNTA per `(offerta, articolo)` (unique parziale separato)
* CHECK di coerenza prezzo per tipo: `prezzo_unitario` obbligatorio se OVERRIDE o
  AGGIUNTA, NULL se ESCLUSIONE

**Quali articoli ammette un'eccezione** (dal 2026-10-13, le stesse regole del contratto):

* un **prezzo diverso** (OVERRIDE) o un'**esclusione** valgono solo per un articolo che sta nel
  listino dell'offerta, e solo se l'offerta ha un listino in vigore;
* una **riga nuova** (AGGIUNTA) vale solo per un articolo che nel listino **non** c'è: per uno che
  c'è già si usa il prezzo diverso;
* chi vende (OVERRIDE e AGGIUNTA) non può usare un articolo che si vende solo dentro un kit, un
  kit senza componenti (dal 2026-10-14), né un articolo la cui tipologia non è prevista per la utility dell'offerta o che non ha nessun
  modo di erogazione;
* non si esclude il componente di un kit: si esclude il kit.

Lo dice il database, in una regola sola per tutte le righe di documento
([script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga)).

**Nella ricerca dell'articolo** trovi prima quelli che la riga può usare. Gli altri compaiono dopo, in grigio, col motivo sotto, e non si possono scegliere: chi cerca un codice preciso e non lo trova fra i primi vede perché. La ricerca e il rifiuto al salvataggio usano la stessa regola, quindi un articolo proposto non viene rifiutato dopo.

Per gli **articoli compositi** (distinta base): un'eccezione ESCLUSIONE **non genera
componenti**. L'esclusione toglie l'articolo per intero, quindi non ha prezzo né
pezzi da dettagliare — coerente con il vincolo "ESCLUSIONE ⇒ prezzo NULL". I
componenti si inizializzano solo per OVERRIDE e AGGIUNTA su articolo composito.

Oltre al prezzo, l'eccezione porta i **parametri di fornitura** che serviranno al
contratto e alla fatturazione ricorrente: `tipo_erogazione`, `fonte_quantita_attesa`,
`periodicita`, `generazione_canone`, `competenza_canone`, e la quantità.

La quantità si inserisce **nell'unità di misura operativa scelta** e il sistema la
converte da sé nell'unità base (stesso meccanismo di preventivi e contratti — vedi
[Gestione preventivi §2.2](gestione-preventivi.md)). Quando la fonte non è *fissa*
(`fonte_quantita_attesa ≠ FISSA`, es. fatturazione *a consumo*) la quantità resta
vuota: arriverà dal consumo effettivo, non da un valore fisso. Quando invece è
*fissa* la quantità è obbligatoria.

> L'offerta converte la quantità e imposta il default della fonte **esattamente
> come il contratto**: senza questa coerenza, al push le righe a quantità fissa
> verrebbero rifiutate, perché mancherebbe il dato di quantità operativa.

### 2.3 Componenti BoM `offerte_commerciali_eccezioni_componenti`

Quando un'eccezione punta a un articolo `is_composito = TRUE`, il sistema genera
automaticamente un record per ogni **componente** della distinta base (BoM). Come
nei contratti, il prezzo del padre è la **somma pesata** dei prezzi figli, mai
inserita a mano. La struttura è lo specchio di `contratti_righe_componenti`.

I componenti portano, oltre al prezzo e alla quantità:

* `coeff_qta_snapshot` — il coefficiente BoM congelato al momento della creazione
* `origine_prezzo` e `prezzo_resolver_context` — da dove viene il prezzo (audit)
* `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` — l'eventuale
  approvazione L3 (vedi §6), che viene **trasportata 1:1 nel contratto** al push

La composizione (quali componenti, in che quantità relative) è **immutabile**: si
possono cambiare i prezzi, non i componenti.

### 2.4 Utility `offerte_commerciali_utilities`

Riga 1:1 con l'utility dell'offerta (vincolo di unicità su `offerta_id`). È lo
specchio fedele di `contratti_utilities`: porta tipo utenza, classe utenza, dati
precontrattuali del PDP e i parametri della fornitura. Tutti i suoi campi vengono
copiati nel contratto al push.

---

## 3. Ciclo di vita e stati

⭐ Le regole comuni a tutti i documenti — in che stato si nasce, chi cambia lo stato, quale permesso chiede un passaggio, l'emissione, l'annullo — stanno nel [modello del documento di vendita](/guide/modello-documento-di-vendita), che al §10 dice anche a che punto è l'offerta rispetto al modello. Qui ci sono gli stati e i passaggi che sono suoi.

### 3.1 Stati e transizioni

Gli stati sono governati da `config.stati_doc_offerte` e le transizioni ammesse da
`config.stati_doc_offerte_transizioni`:

| Stato       | Significato                                            | Modificabile?                   | Terminale? |
| ----------- | ------------------------------------------------------ | ------------------------------- | ---------- |
| `BOZZA`     | In preparazione                                        | Sì: testata, eccezioni, utility | No         |
| `EMESSA`    | Inviata al cliente, in attesa di risposta              | No                              | No         |
| `ACCETTATA` | Accettata dal cliente — da trasformare in contratto o in ordine | No                     | No         |
| `RIFIUTATA` | Rifiutata dal cliente (il "no" del cliente)            | No                              | Sì         |
| `ANNULLATA` | Ritirata da noi: prima dell'emissione, o accettata e non trasformabile | No              | Sì         |
| `SUPERATA`  | Sostituita da una revisione successiva                 | No                              | Sì         |

Le transizioni permesse:

```text
BOZZA     → EMESSA     (emetti)    controlli dell'emissione: §3.2
BOZZA     → ANNULLATA  (annulla)   richiede motivazione_rifiuto
EMESSA    → ACCETTATA  (accetta)
EMESSA    → RIFIUTATA  (rifiuta)   richiede motivazione_rifiuto
EMESSA    → SUPERATA   (automatica) quando nasce la revisione successiva
ACCETTATA → ANNULLATA  (annulla)   richiede motivazione_rifiuto; solo senza contratto o ordine vivo
```

Da **ACCETTATA** si esce trasformando l'offerta (contratto *o* ordine, §8 e §8.bis) oppure,
se non si può trasformare, **annullandola**. L'annullo è ammesso solo se dall'offerta non vive
un contratto o un ordine non annullato (`E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`): prima si annulla
quel documento, che non consuma più l'offerta. Il «sì» del cliente non si ricontrolla, e
un'offerta accettata non si rivede: per riproporla si annulla e se ne crea una nuova.

Due transizioni sono **volutamente vietate** per non confondere la semantica:

* `BOZZA → RIFIUTATA`: il rifiuto è il "no" del cliente, e un cliente può rifiutare
  solo qualcosa che gli è stato emesso. Una bozza si **annulla**, non si rifiuta.
* `EMESSA → ANNULLATA`: una volta emessa, una correzione si fa con una **revisione**
  (che porta la precedente a SUPERATA), non con un annullamento.

La distinzione **RIFIUTATA vs ANNULLATA** è quindi semantica: rifiuto = no del
cliente; annullamento = ritiro nostro, prima dell'invio o dopo un «sì» che non si può
trasformare.

### 3.2 La guard sull'emissione (BOZZA → EMESSA)

Il trigger `trgfn_offerte_commerciali_guard_transizione` interviene sul cambio di
stato e, per l'emissione, controlla nell'ordine:

1. il **listino**: l'offerta vive sulla versione in vigore e la **congela** all'emissione.
   Senza una versione in vigore `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`; con una
   versione fissata non ATTIVA `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`;
2. i **prezzi**: nessun prezzo in attesa di autorizzazione o rifiutato;
3. gli **indirizzi**: ogni indirizzo preso dall'anagrafica è del cliente dell'offerta;
4. le **righe**: ogni riga è ancora ammessa (`E_DOC_RIGA_NON_AMMESSA`, che nomina
   l'articolo). Quali articoli, erogazioni e fonti della quantità una riga può avere
   dipende da dati che stanno fuori dalla riga (il listino in vigore, la tipologia o la
   natura dell'articolo): una riga scritta quando era ammessa può non esserlo più.

Il pulsante «Emetti» è spento con lo **stesso** motivo, letto dagli stessi controlli.

Ogni transizione non prevista in configurazione viene respinta con
`E_OFFERTA_TRANSIZIONE_NON_AMMESSA`.

---

## 4. Revisioni

### 4.1 Cos'è una revisione

Come per i preventivi, una revisione è una **nuova istanza** della stessa offerta
con un contatore incrementato (`revisione_numero`), collegata alla precedente da
`revisione_padre_id`. Serve ad aggiornare la proposta dopo le richieste del cliente
senza perdere lo storico.

Una revisione si crea **solo da uno stato EMESSA**, tramite
`fn_crea_revisione_offerta`. La nuova revisione nasce in **BOZZA** e diventa quella
viva; appena nasce, il trigger `trgfn_offerte_commerciali_revisione` porta
automaticamente la rev precedente a **SUPERATA**. Tentare la revisione da uno stato
diverso da EMESSA dà `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`.

### 4.2 Il predicato `is_attiva` derivato

ZeroERP non mantiene un flag persistito "questa è la rev attiva": il predicato è
**calcolato dalla vista** `vw_offerte_commerciali_list`:

> `is_attiva` = lo stato **non** è SUPERATA né ANNULLATA

La stessa vista espone `has_next_revisione` (esiste una revisione più recente),
che il frontend usa per avvisare l'operatore che sta guardando una versione
sostituita. La lista mostra di default solo le offerte attive; un toggle permette
di vedere anche lo storico.

### 4.3 Differenza col modello preventivi

Offerte e preventivi gestiscono le revisioni in **due modi diversi**. Vale la
pena conoscerli perché il comportamento visibile cambia.

| Aspetto                                                         | **Offerte**                                                                                            | **Preventivi**                                                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Cosa succede alla versione precedente quando nasce la revisione | passa **subito a SUPERATA** (stato chiuso e definitivo, imposto in automatico)                         | **resta EMESSA/viva**; il sistema calcola "qual è la versione valida" senza chiudere la precedente    |
| Se abbandono/annullo la revisione appena iniziata               | la precedente **resta chiusa** (SUPERATA): non torna indietro. Per riprovare si fa una nuova revisione | la precedente **torna automaticamente la versione valida**: si può accettarla o revisionarla di nuovo |
| Come nasce il concetto di "versione valida"                     | dallo **stato** (SUPERATA/ANNULLATA = non valida)                                                      | da un **calcolo** (`is_attiva`), non da uno stato dedicato                                            |

Il motivo della differenza: un'offerta è un **documento a sé** per ogni revisione
(OFC-… diversi in catena), quindi chiudere la precedente non crea problemi —
se serve si emette una nuova offerta. Un preventivo invece **è lo stesso
documento** (stesso numero, più revisioni), e il flusso previsto è *"comincio una
revisione, ci ripenso, la versione emessa di prima resta valida"*: per questo la
precedente **non** viene chiusa. Introdurre uno stato "SUPERATO" sui preventivi
romperebbe proprio questo ritorno. Dettaglio nella
[guida preventivi §4.5](gestione-preventivi.md).

Sui cruscotti entrambi i modelli sono corretti: le offerte escludono la SUPERATA
(è un esito negativo), i preventivi escludono le revisioni non valide tramite
`is_attiva`.

---

## 5. Articoli compositi e BoM

### 5.1 Cosa succede quando aggiungi un composito

Aggiungendo un'eccezione (OVERRIDE o AGGIUNTA) con articolo `is_composito = TRUE`,
il sistema:

1. apre il dialog di **anteprima componenti**, che pre-popola i prezzi dei figli via
   `fn_offerta_eccezione_componenti_preview` (read-only, suggerisce i prezzi senza
   salvare)
2. l'operatore conferma o modifica i prezzi suggeriti (con i controlli L1/L2/L3) e
   salva
3. il backend chiama `fn_offerta_eccezione_componenti_init`, che crea i figli in
   `offerte_commerciali_eccezioni_componenti` (uno per ogni componente attivo e
   valido alla data dell'offerta)
4. un trigger ricalcola il prezzo del padre come somma pesata dei figli

Se l'articolo composito non ha componenti validi alla data, il sistema solleva
`E_DOC_COMPOSITO_BOM_VUOTA`.

### 5.2 Offerta permissiva, contratto rigoroso

C'è una differenza voluta rispetto al contratto: in fase di **offerta** la
risoluzione del prezzo di un componente è **permissiva** — se il resolver non trova
un prezzo a listino, il componente entra comunque con prezzo 0 e origine "manuale",
così l'operatore può comporre la proposta liberamente. Nel **contratto** la stessa
logica è più rigorosa. Questo riflette la natura dei due documenti: l'offerta è una
proposta in lavorazione, il contratto è un impegno.

### 5.3 Cosa può modificare l'operatore

* ✅ **prezzi unitari** dei componenti, con controlli di autorizzazione
* ✅ **IVA** del componente (coerente col padre)
* ❌ **non** può aggiungere o rimuovere componenti dalla composizione
* ❌ **non** può cambiare il coefficiente di quantità (snapshot immutabile)

---

## 6. Pricing e gate prezzo (L1 / L2 / L3)

L'offerta usa lo stesso modello di pricing dei contratti: il listino fissato come
base, l'eventuale variazione globale percentuale a livello testata, e le eccezioni
puntuali (OVERRIDE / ESCLUSIONE / AGGIUNTA) sulle righe. Un OVERRIDE è il prezzo
finale per quell'articolo e **non** riceve la variazione globale.

Quando l'operatore inserisce un prezzo personalizzato, passa per i tre gate di
autorizzazione:

* **L1 — Permesso**: senza il permesso di variare i prezzi, i campi di
  override/variazione sono disabilitati e il backend rifiuta.
* **L2 — Soglia**: il delta rispetto al prezzo suggerito non può eccedere le soglie
  configurate (cascata user → categoria_cliente → group → emittente → default).
* **L3 — Escalation**: oltre la soglia, l'operatore richiede l'approvazione al
  superiore tramite una pratica `APPROVAZIONE_PREZZO`; il prezzo resta `PENDING`
  finché approvato.

Un punto importante delle offerte: l'eventuale **approvazione L3 ottenuta
sull'offerta viaggia fino al contratto**. Al push, lo stato di approvazione e il
collegamento alla pratica vengono copiati 1:1 nei componenti del contratto, così non
serve riapprovare ciò che era già stato autorizzato in fase di proposta.

---

## 7. Azioni disponibili

Le azioni eseguibili in ogni momento sono calcolate dal database da
`script.fn_available_actions_offerta` ed esposte al frontend come un blob di
*capability* — così l'interfaccia non deve replicare la macchina a stati.

La funzione combina due fonti:

* le **transizioni manuali** lette dalla configurazione
  (`config.stati_doc_offerte_transizioni`): `emetti`, `annulla`, `accetta`, `rifiuta`
* tre azioni **speciali**: `crea_revisione` (solo da EMESSA), `push_contratto` e
  `genera_ordine` (entrambe solo da ACCETTATA e **mutuamente esclusive**: ciascuna
  è disponibile solo se dall'offerta non è stato ancora generato né un contratto né
  un ordine — vedi §8.bis)

Per ogni azione la funzione restituisce i metadati per l'interfaccia (chiave di
dispatch, stato target, etichetta i18n, se serve conferma, se serve una
motivazione; l'icona la sceglie l'interfaccia dalla chiave dell'azione) e una serie di flag di capability:

| Flag                                                                      | Vero quando                                                                                                   |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `can_edit_testata`                                                        | almeno una colonna della testata si cambia nello stato (in BOZZA tutte; EMESSA e ACCETTATA le note): lo legge il database dal suo blocco di testata |
| `can_edit_eccezioni` / `can_edit_utility` / `can_edit_indirizzi`         | l'offerta è in BOZZA (eccezioni, fornitura e indirizzi): lo legge il database dal blocco «solo in bozza» che li protegge |
| `can_create_revisione`                                                    | l'offerta è EMESSA                                                                                            |
| `can_push_contratto`                                                      | l'offerta è ACCETTATA, non esiste già né un contratto né un ordine generati dall'offerta (XOR) **e** ogni riga può andare nel contratto |
| `can_genera_ordine`                                                       | l'offerta è ACCETTATA, non esiste già né un contratto né un ordine generati dall'offerta (XOR) **e** ogni riga può andare in un ordine (solo merce) |
| `can_push_contratto_reason` / `can_genera_ordine_reason` (+`_reason_key`) | (se l'azione non è possibile) il motivo, es. `OFFERTA_CONTRATTO_GIA_GENERATO`, `OFFERTA_ORDINE_GIA_GENERATO` o `RIGA_NON_AMMESSA` |

Quando l'offerta è trasformabile ma una riga non può andare nel documento da generare,
«Genera contratto» o «Genera ordine» restano **proposti e spenti**, col motivo. L'azione
`annulla` da ACCETTATA è spenta col motivo `DOCUMENTI_VIVI` finché dall'offerta vive un
contratto o un ordine.

---

## 8. Push a contratto

Quando un'offerta arriva in **ACCETTATA**, l'azione **push a contratto** genera il
contratto. Il cuore è la funzione `fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id)`,
che opera in transazione atomica.

### 8.1 Regole

1. l'offerta deve essere in **ACCETTATA**, altrimenti `E_OFFERTA_PUSH_STATO_NON_AMMESSO`
2. il push è **idempotente**: se un contratto è già stato generato per quell'offerta
   (vincolo di unicità su `contratti.offerta_id`), solleva
   `E_OFFERTA_CONTRATTO_GIA_GENERATO`
3. stato target e sorgente sono **letti dalla configurazione** (contratto in DRAFT,
   sorgente OFFERTA_COMMERCIALE), senza valori hardcoded

### 8.2 Cosa viene copiato 1:1

* **Testata** → contratto DRAFT: billing account, istanza/utility, listino e
  versione fissata, variazione globale, date di validità, emittente fiscale, valuta,
  metadati. Il nuovo contratto registra `offerta_id` come riferimento alla sorgente.
* **Eccezioni** → `contratti_righe`: articolo, tipo eccezione, prezzo, quantità,
  parametri di fornitura, e — per ogni eccezione composita — i **componenti BoM**,
  con lo stato di approvazione prezzo trasportato (§6).
* **Utility** → `contratti_utilities`: tutti i campi di fornitura.
* **Pratica** (opzionale): se passata, l'offerta e il contratto vengono collegati
  alla pratica come sorgenti.

Il contratto nasce in **DRAFT**: il push non lo attiva. Da lì segue il proprio ciclo
di vita (vedi [Gestione Contratti](/guide/gestione-contratti)).

---

## 8.bis Genera ordine — l'alternativa one-shot al contratto

Quando l'offerta è in **ACCETTATA**, accanto al push a contratto è disponibile
l'azione **genera ordine**: invece di avviare una fornitura ricorrente, trasforma
l'offerta in un **ordine di vendita** one-shot (vendita puntuale).

### Regole

1. l'offerta deve essere in **ACCETTATA**, altrimenti `E_ORD_ORIGINE_NON_CONVERTIBILE`;
2. vale la **mutua esclusività XOR**: l'azione è disponibile solo se dall'offerta
   non vive già né un contratto né un ordine. La prima generazione (contratto *o*
   ordine) disabilita l'altra, finché quel documento non viene annullato;
3. la generazione ordine è **idempotente 1:1**: un secondo tentativo sulla stessa
   offerta è rifiutato con `E_ORD_OFFERTA_GIA_CONVERTITA` (rete di sicurezza:
   vincolo di unicità `uq_ordini_v_documento_origine_offerta`);
4. se l'offerta ha già generato un contratto, la generazione ordine è bloccata con
   `E_OFFERTA_CONTRATTO_GIA_GENERATO` (e, specularmente, il push a contratto su
   un'offerta che ha già un ordine è bloccato con `E_OFFERTA_ORDINE_GIA_GENERATO`);
5. ogni riga dell'offerta deve poter stare in un ordine — un ordine contiene **solo
   merce** — altrimenti il pulsante è spento e la generazione è rifiutata con
   `E_DOC_RIGA_NON_AMMESSA`, che nomina l'articolo. Un'offerta di servizi si
   trasforma in un contratto.

La generazione la fa il database in un passo solo (`vendite.fn_genera_ordine_da_offerta`,
gemello del push a contratto): i controlli prima di scrivere, poi la testata, l'indirizzo
di default del cliente e le righe.

### Cosa viene copiato

L'ordine nasce in **DRAFT** ereditando le **righe espanse** dell'offerta (listino +
variazione globale + eccezioni, con i componenti BoM), preservando i **prezzi
negoziati/override**. Sull'ordine viene registrata l'origine
(`documento_origine = ('OFFERTA_COMMERCIALE', id)`). L'offerta resta **ACCETTATA**.

Da lì l'ordine segue il proprio ciclo di vita (conferma, push a commessa); vedi
[Gestione Ordini di vendita](/guide/gestione-ordini).

---

## 9. Valuta

La valuta dell'offerta (`valuta_id`) viene riempita di default dal trigger
`trgfn_offerte_commerciali_default_valuta` (BEFORE INSERT), se non già indicata nel
payload. La logica è la **stessa di preventivi e contratti**: il trigger risolve la
valuta via `fn_get_valuta_id`, seguendo la catena *billing account → soggetto
gestore → valuta predefinita del gestore*. Se nessuna valuta è risolvibile, solleva
`E_CONFIG_MANCANTE` (nessun fallback hardcoded).

---

## 10. Workflow end-to-end

```text
   ┌──────────────────┐
   │ Nuova offerta    │
   │ (operatore crea) │
   └────────┬─────────┘
            │
   ┌────────▼──────────┐   annulla (motivazione)   ┌─────────────┐
   │      BOZZA        │ ─────────────────────────► │  ANNULLATA  │
   │ testata + utility │                            │ (terminale) │
   │ + eccezioni       │                            └─────────────┘
   └────────┬──────────┘
            │ emetti — guard: versione listino fissata e ATTIVA
            │
   ┌────────▼──────────┐   crea revisione    ┌──────────────────┐
   │      EMESSA       │ ──────────────────► │ rev. N+1 in BOZZA │
   │                   │                     │ (la N → SUPERATA) │
   └───┬──────────┬────┘                     └──────────────────┘
       │          │
  accetta      rifiuta (motivazione)
       │          │
   ┌───▼────┐  ┌──▼────────┐
   │ACCETTATA│  │ RIFIUTATA │
   └───┬────┘  │(terminale)│
       │       └───────────┘
       │  bivio XOR — una sola delle due (entrambe se non già usate, poi sparisce l'altra)
       ├──────────────────────────────┐
       │ push a contratto              │ genera ordine
       │                               │
   ┌───▼──────────────────┐   ┌────────▼───────────────┐
   │  Contratto in DRAFT   │   │  Ordine vendita DRAFT   │
   │  (fornitura ricorrente)│   │  (vendita one-shot)     │
   └───────────────────────┘   └─────────────────────────┘
```

---

## 11. Casi d'uso operativi

### 11.1 Proposta standard con sconto globale

1. Crea una nuova offerta → seleziona BA, istanza/utility, listino
2. Imposta la variazione globale (es. `-5%`)
3. Salva in BOZZA → la preview mostra gli articoli del listino scontati
4. "Emetti" → il trigger fissa la versione del listino; l'offerta passa a EMESSA
5. Il cliente accetta → "Accetta" → ACCETTATA
6. "Push a contratto" → nasce un contratto DRAFT con le stesse condizioni

### 11.2 Cliente che chiede una modifica a offerta già inviata

1. Apri l'offerta EMESSA
2. "Crea revisione" → nasce la rev. N+1 in BOZZA; la precedente diventa SUPERATA
3. Modifica eccezioni/prezzi nella nuova revisione ed emetti di nuovo

### 11.3 Articolo con prezzo personalizzato (override)

1. Nella vista eccezioni, seleziona un articolo del listino → "Modifica prezzo"
2. L'eccezione è salvata come `OVERRIDE`; la variazione globale non si applica a
   quell'articolo
3. Se il delta supera la soglia L2 → richiesta approvazione L3 (pratica)
4. Quando l'offerta viene accettata e spinta a contratto, l'approvazione già
   ottenuta viaggia con i componenti — niente doppia approvazione

### 11.4 Articolo fuori listino o escluso

1. "Aggiungi articolo fuori listino" → eccezione `AGGIUNTA` con prezzo esplicito
2. Oppure seleziona un articolo del listino → "Escludi" → eccezione `ESCLUSIONE`
   (prezzo NULL): quell'articolo non sarà disponibile nel contratto risultante

### 11.5 Offerta ritirata prima dell'invio

1. Offerta ancora in BOZZA → "Annulla" con motivazione
2. Stato → ANNULLATA (terminale). Per ripartire si crea una nuova offerta

### 11.6 Offerta accettata che non si può trasformare

1. L'offerta è ACCETTATA, ma «Genera contratto» e «Genera ordine» sono spenti con il
   motivo (per esempio una riga che non è più ammessa)
2. "Annulla" con motivazione: l'offerta va in ANNULLATA. Se dall'offerta vive già un
   contratto o un ordine, prima si annulla quello
3. Per riproporre l'offerta al cliente se ne crea una nuova

---

## 12. Errori principali

Codici sollevati dal dominio offerte (registrati in `config.messaggi_errore`):

| Codice                                            | Quando                                                                                                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`      | Emissione (BOZZA→EMESSA) con `listino_versione_id` non valorizzato                                                                                  |
| `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` | Emissione con versione listino non in stato ATTIVA                                                                                                  |
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`               | Transizione di stato non prevista in configurazione                                                                                                 |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`           | "Crea revisione" da uno stato diverso da EMESSA                                                                                                     |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO`                | Push a contratto da uno stato diverso da ACCETTATA                                                                                                  |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`                | Push a contratto già generato (idempotenza) **oppure** tentativo di generare un ordine quando l'offerta ha già un contratto (mutua esclusività XOR) |
| `E_OFFERTA_ORDINE_GIA_GENERATO`                   | Push a contratto quando l'offerta ha già generato un ordine (mutua esclusività XOR)                                                                 |
| `E_ORD_OFFERTA_GIA_CONVERTITA`                    | Secondo tentativo di generare un ordine dalla stessa offerta (univocità 1:1 offerta→ordine)                                                         |
| `E_ORD_ORIGINE_NON_CONVERTIBILE`                  | Genera ordine da un'offerta che non è ACCETTATA                                                                                                     |
| `E_DOC_RIGA_NON_AMMESSA`                          | Emissione, genera ordine (o attivazione del contratto) con una riga che non è più ammessa: nomina l'articolo                                        |
| `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`            | Annullo di un'offerta accettata da cui vive ancora un contratto o un ordine                                                                         |
| `E_DOC_COMPOSITO_BOM_VUOTA`                       | Articolo composito senza componenti validi alla data                                                                                                |
| `E_CONFIG_MANCANTE`                               | Configurazione mancante (valuta non risolvibile, stato/sorgente assenti)                                                                            |

---

## 13. Pattern e principi di design

### 13.1 L'offerta come delta del listino

Come il contratto, l'offerta non importa le righe del listino: in
`offerte_commerciali_eccezioni` vivono **solo le eccezioni**. Il listino resta un
riferimento esterno. Se una riga esiste, è un'eccezione intenzionale.

### 13.2 Simmetria con il contratto

L'offerta è la **gemella in proposta** del contratto: stessa forma (testata +
eccezioni + componenti BoM + utility), stesso modello di pricing, stessi gate L1/L2/L3.
Il push è la "saldatura" fra i due: traduce 1:1 l'offerta accettata in un contratto
DRAFT. Questa simmetria rende il push semplice e robusto, e fa sì che chi conosce il
contratto conosca già quasi tutta l'offerta.

### 13.3 Stato derivato vs persistito

Come per i preventivi, "qual è la revisione viva" non è un flag salvato ma un
predicato derivato (`is_attiva` nella vista). Niente trigger di sincronizzazione,
niente rischio che il flag e i dati divergano.

### 13.4 Idempotenza del push

Il vincolo di unicità su `contratti.offerta_id` rende impossibile generare due
contratti dalla stessa offerta: un secondo tentativo fallisce in modo pulito. La
generazione è quindi sicura anche se l'operatore clicca due volte o l'API viene
richiamata di nuovo.

### 13.5 Trigger DB come ultima difesa

Le guard sull'emissione, sulle transizioni e sull'idempotenza sono trigger e
funzioni DB: anche se il backend non verifica, il database rifiuta. Il backend ha
controlli equivalenti solo per dare messaggi parlanti prima del roundtrip.

---

## 14. Glossario rapido

| Termine                              | Significato                                                                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Offerta commerciale**              | Proposta di condizioni quadro a un cliente. Stati BOZZA → EMESSA → ACCETTATA → (push) contratto; oppure RIFIUTATA / ANNULLATA / SUPERATA         |
| **Push a contratto**                 | Generazione del contratto DRAFT dall'offerta ACCETTATA, idempotente, con copia 1:1 di eccezioni, componenti e utility                            |
| **Genera ordine**                    | Generazione di un ordine di vendita one-shot DRAFT dall'offerta ACCETTATA (righe espanse, prezzi negoziati), **alternativa** al push a contratto |
| **XOR contratto/ordine**             | Da un'offerta ACCETTATA si genera al massimo *uno* tra contratto e ordine; la prima generazione disabilita l'altra in modo permanente            |
| **OVERRIDE / ESCLUSIONE / AGGIUNTA** | I tre tipi di eccezione al listino (prezzo personalizzato / articolo non disponibile / articolo fuori listino)                                   |
| **SUPERATA**                         | Stato terminale automatico: l'offerta è stata sostituita da una revisione successiva                                                             |
| **ANNULLATA**                        | Ritiro interno prima dell'emissione (≠ RIFIUTATA, che è il "no" del cliente)                                                                     |
| **is_attiva**                        | Predicato derivato dalla vista: lo stato non è SUPERATA né ANNULLATA                                                                             |
| **Versione listino fissata**         | `listino_versione_id` congelato all'emissione: l'offerta propone i prezzi di quella versione                                                     |
| **L1/L2/L3**                         | Livelli di autorizzazione pricing: Permesso / Soglia / Workflow approvazione                                                                     |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi la
documentazione backend di dominio. Le decisioni di modello sono raccolte negli
addendum di sviluppo (`dev/work-done/addendum-db-offerta-commerciale.md` e correlati).*

---
{% include-markdown "signature-core.md" %}
