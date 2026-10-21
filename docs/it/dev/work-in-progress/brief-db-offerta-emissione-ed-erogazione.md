# Brief DB — Offerta, dal collaudo del drawer: l'emissione e l'erogazione

## ⏭️ Chi riparte — aggiornato al 2026-10-21 (notte)

**Riparte: la sessione BE/FE** (§I.5.5). Il lato DB è finito: `20261021-44` → `-61` applicati su
dbdev e scratch, pgTAP verdi (Tid, 2026-10-21, nessuna regressione).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ~~Tid~~ | ~~decisioni I-D1…I-D6~~ ✅ 2026-10-21 | §I.3 | — |
| 2 | ~~team DB~~ | ~~giro unico: ritiro della DERIVATA, kit solo FISSA, riga intera, guard e capability, verbo «genera ordine», annullo da ACCETTATA, seed, doc, pgTAP~~ ✅ 2026-10-21, provato sullo scratch | §I.5 | — |
| 3 | ~~Tid~~ | ~~query della riga DERIVATA su dbdev, apply su dbdev e scratch, corsa pgTAP~~ ✅ 2026-10-21 | §I.5.4 | — |
| 4 | sessione BE/FE | genera ordine sul verbo, pulsanti spenti col motivo, annullo da ACCETTATA, codici e chiavi i18n, via la DERIVATA, `quantita` fuori dal payload | §I.5.5, §H.5 | — |
| 5 | Tid | collaudo a video: §D.5 + §G.4 + §H.5 (`OFC-0001064`) | §D.5, §G.4, §H.5 | 4 |
| 6 | chi chiude | archiviazione in `work-done/`, riga di PROJECT_CONTEXT (oggi ferma al §G «non committato») | — | 5 |

Decisioni aperte di Tid: nessuna (I-D7, 2026-10-21: le 9 righe fuori perimetro di dbdev restano per
il collaudo, §I.5.4). Lavoro da committare: i changeSet `20261021-44` → `-61`, i quattro
CSV, il pgTAP nuovo e i nove pgTAP aggiornati, manual e guide, questo file.

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-07. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§A.5, §B.5), che **attende** la consegna DB.
> **Origine:** il collaudo a video di Tid del drawer dell'offerta
> (`brief-db-righe-esclusione-solo-non-si-vende` §13). Due difetti di modello, in un brief solo
> (richiesta di Tid): **A** blocca l'emissione e va per primo; **B** è la forma delle righe.
> **Decisione:** di Tid, 2026-10-07, su B: il default dell'erogazione (e della fonte) si
> **eredita dall'articolo**, dalla sua tipologia; il perimetro delle scelte segue la utility.
> **Stato (2026-10-07, notte): ✅ LATO DB CHIUSO.** Parte A (`20261007-40 → -47`) e parte B
> (`-50 → -54`, `-60 → -65`) applicate da Tid; pgTAP verdi su dbdev. **✅ Giro BE/FE fatto**
> (2026-10-07, §D): restano il collaudo a video di Tid (§D.5) e l'archiviazione in `work-done/`.
> **✅ Secondo giro DB (§E): le tre domande del §D.4, decise da Tid.** ChangeSet
> `20261007-28 → -30` e `-66 → -68` applicati da Tid il 2026-10-08, pgTAP verdi su dbdev.
> **⏳ Secondo giro BE/FE (§E.5) in parte fatto; serve un terzo giro DB (§F: F-1 la quantità
> calcolata, F-2 il listino del documento), poi il resto del BE/FE, il collaudo e l'archiviazione.**
> **✅ Terzo giro DB chiuso (§F.4, 2026-10-08):** `20261008-10 → -16` e codici 1222-1223 applicati
> da Tid su dbdev, pgTAP verdi; pgTAP nuovo e 25 fixture corretti (§F.4.6). **⏳ Restano** il giro
> BE/FE del §F.4.5, i tre trovati del §F.4.3 da decidere (il primo: la quantità DERIVATA), il
> collaudo a video e l'archiviazione.
> **✅ Terzo giro BE/FE fatto (§G, 2026-10-08).** ✅ I 14 file pgTAP sono usciti dai registri dei
> rossi di CI (Tid, 2026-10-08). **⏳ Restano** i tre trovati del §F.4.3 (il primo, la quantità
> DERIVATA_COMPONENTI, torna al team DB dopo la decisione di Tid; con lui `quantita` nel payload
> di riga: §G.1), poi il collaudo a video (§D.5 + §G.4, dopo, per scelta di Tid) e l'archiviazione.
> Il §G è committato (`67a0cac2e`, in `Tito-dev`); chi riparte lo dice il blocco in cima.
> Il secondo trovato (FISSA, `quantita` a mano) resta aperto senza richiesta; il terzo (ordine fra
> guard del listino e lock del contratto attivo) è **passato** a
> [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md) §5 (§F.4.3).
> **⏳ Quarto giro DB (§H, 2026-10-11):** l'offerta ACCETTATA che non si trasforma (righe fuori
> perimetro dopo la scrittura; nessuna uscita da ACCETTATA). Supera B-D6. Al team DB, poi BE/FE.
> **Da leggere per primo:** §C.10 (riepilogo di chiusura), poi §C.6.4 e §C.9.6 per chi fa il BE/FE.
> **Le decisioni** (di Tid, 2026-10-07) stanno in §C.5 e in coda al §C.7: A-D1 chiusa dal modello,
> A-D2 il contratto non si attiva senza versione in vigore, A-D3 la revisione congela alla sua
> emissione, B-D1 tipologia e poi natura, B-D1 bis fonte FISSA per i generici, B-D2 nessun
> STANDARD, B-D3 la matrice resta come ripiego (fatta dato), B-D4 il perimetro è la tipologia
> dell'articolo (dentro la utility), B-D5 DERIVATA_COMPONENTI sul composito, B-D6 le righe già
> scritte restano come sono.
> ⚠️ Le sezioni §A e §B qui sotto sono la richiesta originale del BE/FE: dove la decisione le ha
> cambiate (A-R5 sulla revisione, B-R3 sulla utility) vale il §C.

## A. «Emetti» spento per una versione di listino che l'emissione stessa dovrebbe fissare

> Il sintomo: «Emetti» è spento col motivo «Manca la versione di listino», il form non permette
> di sceglierla, e intanto le righe si gestiscono senza problemi.

### A.1 Il difetto, sul modello

La regola è una sola: **l'offerta vive sulla versione di listino in vigore, e la congela
all'emissione.** Il form sceglie il listino, non la versione. Il DB ha già la sede unica della
prima metà, `vendite.fn_documento_listino_operativo('OFFERTA', id)`: la versione fissata se c'è,
altrimenti `vendite.fn_listino_versione_in_vigore(listino, oggi)` (ATTIVA o CHIUSA).

Oggi però quattro sedi rispondono alla domanda, e in tre modi diversi:

| Sede | Che cosa guarda | Esito |
| --- | --- | --- |
| Righe: `fn_offerta_righe_espanse` / `fn_offerta_righe_preview` | il BB operativo | ✅ righe dalla versione in vigore |
| Capability: `script.fn_available_actions_offerta` (dal 2026-07-19, `brief-db-guard-righe-avanzamento-stato` §1a) | la **colonna nuda** `listino_versione_id`: NULL → `LISTINO_VERSIONE_MANCANTE` | 🔴 «Emetti» spento |
| Guard: `trgfn_offerte_commerciali_guard_transizione`, BOZZA→EMESSA | colonna NOT NULL **e** ATTIVA | rifiuta CHIUSA |
| Congelamento: `OfferteService._fissa_versione_listino_se_necessario` (Python, prima del cambio stato) | ATTIVA alla data, **altrimenti CHIUSA** (copia Python di `fn_listino_versione_in_vigore`) | fissa una CHIUSA che poi il guard rifiuta |

L'effetto: il congelamento sta **dentro** «Emetti», e la capability spegne «Emetti» **perché**
il congelamento non c'è ancora stato. Il pulsante non arriva mai al passo che lo renderebbe vero.
Un'offerta nuova non si emette.

### A.2 Richiesta

| # | Cosa |
| --- | --- |
| **A-R1** | **Il congelamento all'emissione è del DB**: nella transizione BOZZA→EMESSA, se `listino_versione_id` è NULL, il DB lo fissa alla versione del BB operativo, nella stessa scrittura del cambio stato. La forma (nel guard di transizione o in un trigger a sé che lo precede) la sceglie il team DB |
| **A-R2** | **La capability e il guard leggono il BB**, non la colonna: «Emetti» è spento solo se la versione **che verrebbe congelata** manca (listino senza versione in vigore) o non è ammessa. Stesso predicato nelle due sedi, perché pulsanti e DB non possano dissentire |
| **A-R3** | **Decidere CHIUSA** (A-D1, §A.3): oggi le righe la usano, il Python la congela e il guard la rifiuta. Una risposta sola, scritta nel BB |
| **A-R4** | Motivo e testo per il caso vero: «il listino non ha una versione in vigore oggi» invece di «manca la versione». Il FE ha già `listino_versione_mancante` / `listino_versione_non_attiva`: si riusano se il significato tiene, altrimenti chiave nuova da comunicare |
| **A-R5** | pgTAP: offerta in BOZZA senza versione → «Emetti» acceso; l'emissione fissa la versione del BB; listino senza versione in vigore → spento col motivo e rifiutato dal guard; la revisione e il push portano la versione congelata |

### A.3 Da decidere (team DB, poi Tid)

* **A-D1 — Una versione CHIUSA può governare un'offerta?** `fn_listino_versione_in_vigore` dice sì,
  in ripiego su ATTIVA; il guard dice no. Se no, il BB delle righe deve dirlo anche per la
  BOZZA, o l'operatore costruisce un'offerta su prezzi che all'emissione verranno rifiutati.
* **A-D2 — Il contratto.** Il BB serve anche il contratto, che congela all'attivazione. Va
  verificato che `fn_available_actions_contratto` e il suo guard non abbiano lo stesso difetto
  (non verificato da questa sessione).

### A.4 Fuori perimetro

* Scegliere la versione a mano nel form: oggi il modello non lo prevede, e il difetto non lo
  richiede.

### A.5 Lato BE/FE, a consegna DB fatta

* Ritirare `OfferteService._fissa_versione_listino_se_necessario` e la sua chiamata in `emetti`
  (il DB congela da sé), e con lei la copia Python della regola in
  `ListiniRepository.get_versione_attiva_alla_data` se non ha altri lettori. Il codice
  `E_VENDITE_VALIDATION` di quel ramo sparisce: parla il DB.
* Policy dei codici nuovi o cambiati, ripieghi senza `%s`; le chiavi i18n di A-R4.
* Doc: `api_offerte.md` § emissione.

## B. Come si eroga una riga lo dice l'articolo: erogazione e fonte dalla tipologia

> Il sintomo: su una utility BASE il form proponeva «Canone / Consumo / Una tantum» e, come
> fonte, «Da letture utility»: scelte pensate per le utility a contatore, che su un articolo
> generico non hanno senso.

### B.1 Il difetto, sul modello

* `tipo_erogazione` (CANONE, UNA_TANTUM, ORARIO, CONSUMO) esiste **solo sulla riga**
  (`vendite.contratti_righe`, `vendite.offerte_commerciali_eccezioni`) ed è obbligatoria su
  OVERRIDE/AGGIUNTA (`E_RIGA_EROGAZIONE_OBBLIGATORIA`), **senza default**: l'operatore la sceglie
  riga per riga, anche quando l'articolo l'ha già detta.
* L'articolo la dice già: `catalogo.articoli.listino_tipologia_id` → `config.listini_tipologie`
  (CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA, PRODOTTI, SERVIZI, coi flag `e_consumo`,
  `e_quota_fissa`, `e_imposta`, `e_onere`, `e_prodotto`, `e_servizio`). Il legame tipologia →
  erogazione però non è scritto da nessuna parte.
* La utility dichiara già le sue tipologie (`config.listini_tipologie_utilities`: BASE ammette
  solo PRODOTTI e SERVIZI). Nemmeno questo legame arriva all'erogazione: una riga di una
  utility BASE può essere CONSUMO + LETTURE, cioè fatturata da letture che quella utility non ha.
* La fonte (`fonte_quantita_attesa`) nasce dalla matrice di `script.trgfn_righe_default_fonte_qta`
  sul solo `tipo_erogazione` (CONSUMO → LETTURE). La matrice è giusta per l'energia e sbagliata
  per un servizio generico venduto a consumo, dove la quantità la scrive l'operatore (MANUALE).
* Il frontend ricopia la matrice delle combinazioni ammesse (`fontiQuantitaErogazione.js`, specchio
  del CHECK `chk_*_coerenza_fonte_erogazione`): una seconda verità, che non sa niente di tipologia
  né di utility.

### B.2 Richiesta

| # | Cosa |
| --- | --- |
| **B-R1** | **La tipologia dichiara come si eroga**: per ogni `config.listini_tipologie` l'erogazione di default e la fonte di default (e, se il team DB lo ritiene la forma giusta, quali erogazioni e fonti ammette). La forma (colonne sulla tipologia o tabella a sé) la sceglie il team DB |
| **B-R2** | **La riga eredita dall'articolo**: su contratto e offerta, una riga OVERRIDE/AGGIUNTA senza `tipo_erogazione` la prende dalla tipologia dell'articolo; la fonte non indicata la prende dalla tipologia, prima della matrice generica. L'operatore che sceglie diversamente vince, dentro il perimetro di B-R3. ⚠️ L'esclusione resta vuota (`chk_*_esclusione_senza_dati`) |
| **B-R3** | **Il perimetro lo dà la utility del documento**: una combinazione erogazione/fonte che le tipologie ammesse dalla utility non prevedono è rifiutata dal DB col campo (es. LETTURE su una utility BASE). Codice nuovo se serve, con la sua policy |
| **B-R4** | **Una lettura per il form**: per (documento, articolo) le erogazioni e le fonti ammesse, col default. Il form la legge invece di ricopiare la matrice, e `fontiQuantitaErogazione.js` si ritira |
| **B-R5** | Seed dei default per le sei tipologie e prova pgTAP: riga senza erogazione ereditata dall'articolo, scelta dell'operatore che vince, combinazione fuori perimetro rifiutata col campo, esclusione ancora vuota, push offerta → contratto con i valori ereditati |

### B.3 Da decidere (team DB, poi Tid)

* **B-D1 — L'articolo senza tipologia.** `listino_tipologia_id` è nullable: per un articolo
  «generico» senza tipologia serve un default. Due candidati:
  * `natura_vendita_id`, che è `NOT NULL` e dice già qualcosa di vicino (MERCE, SERVIZIO_UNA_TANTUM,
    SERVIZIO_RICORRENTE: la terza è un canone);
  * un default fisso per i generici. Tid indica una **fonte generica, MANUALE**, e un'erogazione
    «standard».

  Proposta della sessione BE/FE: la natura di vendita come ripiego, perché è un fatto
  dell'articolo e non una costante. Va però scritto **quale delle due vince** quando
  dicono cose diverse.
* **B-D2 — Un valore «STANDARD» di `tipo_erogazione`.** Proposta: **no**. Non dice come si fattura
  la riga, e su un articolo generico i valori che ci sono bastano (UNA_TANTUM per un bene o un
  intervento, CANONE per un servizio ricorrente), con la fonte MANUALE dove la quantità la scrive
  l'operatore.
* **B-D3 — La matrice CONSUMO → LETTURE.** Con B-R2 la fonte arriva prima dalla tipologia. La matrice
  resta solo come ripiego, o si ritira?

### B.4 Fuori perimetro

* Le righe di preventivo, ordine e DDT: non hanno `tipo_erogazione`.
* ORARIO resta modellato e non esposto (modulo timesheet futuro).

### B.5 Lato BE/FE, a consegna DB fatta

* Il form delle righe (`RigheEccezioniDrawer`, contratto e offerta) legge erogazioni e fonti
  ammesse e il default da B-R4; preseleziona l'ereditato; ritira `fontiQuantitaErogazione.js` e il
  suo specchio Python `_FONTE_VIETATE_PER_TIPO_EROGAZIONE` / i default in `contratti_service.py`
  (lasciar parlare il DB).
* Il codice nuovo di B-R3, se nasce: policy generata e ripiego senza `%s`.
* Doc: `api_contratti.md`, `api_offerte.md`, `modello-contratti.md`.

## C. Analisi del team DB (`dev/db-tid`, 2026-10-07)

> Letta la **struttura**: corpi delle funzioni dalla doc auto-generata, vincoli e trigger dal
> catalogo, seed di catalogo. Nessun conteggio di righe entra negli argomenti.

### C.1 Parte A, l'emissione

#### C.1.1 A-D1: una versione CHIUSA non è mai «in vigore oggi», per costruzione

* `trgfn_listini_versioni_guard_transizione_stato` ammette ATTIVA → CHIUSA **solo** con
  `valido_al < CURRENT_DATE`.
* `trgfn_listini_versioni_guard_date_chiusa` impedisce di cambiare le date di una CHIUSA.
* `validita` è `[valido_dal, valido_al]` (colonna generata).

Quindi `fn_listino_versione_in_vigore(listino, CURRENT_DATE)` **non può restituire una CHIUSA**: il
ramo «ATTIVA o CHIUSA» serve solo alle date passate. Per il congelamento all'emissione
(data = oggi) la versione del BB è sempre ATTIVA o NULL. Il guard («solo ATTIVA») e il BB **non
dissentono** sull'emissione di un'offerta nuova. Il difetto vero è solo quello del §A.1: la capability
legge la colonna nuda.

⚠️ **Resta una sola strada per arrivare a una CHIUSA**, e il brief non la vede: la **revisione**.
`fn_crea_revisione_offerta` ricopia `listino_versione_id` dal padre, che è congelata. Se nel frattempo
quella versione si è chiusa, la revisione nasce in BOZZA con una versione CHIUSA già fissata. Il BB
la rispetta, e le righe mostrano i prezzi del padre. La capability la spegne
(`LISTINO_VERSIONE_NON_ATTIVA`), il guard la rifiuta, e il form non permette di cambiarla
(§A.4). **La revisione non si emette più.** È la decisione **A-D3** (§C.3).

⚠️ Porta secondaria, fuori dal perimetro di questo brief: su `vendite.listini_versioni` nessun
guard sull'INSERT vieta di creare una versione **già** CHIUSA, con date qualsiasi. Il
«per costruzione» qui sopra vale per le versioni passate dal workflow. Da chiudere in un giro
`listini` (un guard o un CHECK sull'INSERT: si nasce BOZZA), oppure da dichiarare.

#### C.1.2 A-D2: il contratto congela già a DB, ma lascia passare l'attivazione senza versione

`vendite.trgfn_contratti_freeze_listino_versione` (`trg_contratti_a10_freeze_listino_versione_upd`)
fa sul contratto proprio ciò che A-R1 chiede per l'offerta. Su DRAFT → ATTIVO, se la versione è
NULL, la fissa con `fn_listino_versione_in_vigore(listino, CURRENT_DATE)`. È lo stampo da seguire.

🔴 **Ma se il listino non ha una versione in vigore, il contratto si attiva lo stesso con
`listino_versione_id` NULL** (commento: «§4.4, warning UI»). Da quel momento il BB operativo lo fa
**galleggiare** sulla versione in vigore di ogni giorno. Un contratto ATTIVO cambia prezzi in
silenzio a ogni nuova versione del listino, cioè l'opposto di «congela all'attivazione».
`fn_available_actions_contratto` non dice niente del listino, quindi coerente col guard, ma su una
regola che contraddice il modello. La sezione `refactor-contratti-modalita` §4.4 del 2026-05-18 è
stata scritta **prima** del BB operativo. È la decisione **A-D2** (§C.3).

#### C.1.3 La forma proposta per A-R1…A-R4

1. **Una check pura sui valori**, sede unica del predicato «la versione che governerebbe questo
   documento, e se è ammessa per congelarlo»:
   `vendite.fn_check_listino_congelabile(p_listino_id, p_listino_versione_id)` → array dei motivi
   (§12.5.1 delle linee guida). Prende i **valori** e non l'id, perché la chiama un guard
   `BEFORE ROW` che ha in mano `NEW`. La versione candidata è
   `COALESCE(p_listino_versione_id, fn_listino_versione_in_vigore(p_listino_id, CURRENT_DATE))`, cioè
   la stessa composizione del BB `fn_documento_listino_operativo`. Il BB passa a chiamarla al posto
   della sua `COALESCE`, così la regola del 2 resta chiusa.
2. **Il guard di transizione dell'offerta congela e poi verifica**. Su BOZZA → EMESSA:
   `NEW.listino_versione_id := <candidata>` se NULL, poi solleva il primo motivo della check
   (`fn_raise_primo_motivo_se_presente`). Stessa scrittura del cambio stato (A-R1), nessun trigger
   nuovo. Il ramo attuale «NULL → errore; ≠ ATTIVA → errore» si ritira.
3. **La capability chiama la stessa check** con i valori della testata. Ritira la lettura della
   colonna nuda. Pulsante e guard non possono più dissentire (A-R2, §12.5.2).
4. **Motivi** (A-R4):
   * listino senza versione in vigore oggi: `reason = LISTINO_SENZA_VERSIONE_IN_VIGORE`,
     **`reason_key` nuova** `vendite.offerte.azione_reason.listino_senza_versione_in_vigore`. Il
     testo FE attuale di `listino_versione_mancante` («Manca la versione di listino: obbligatoria per
     emettere l'offerta») descrive il difetto, non il caso. Codice `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`
     riusato con il **testo riscritto** nel CSV («il listino non ha una versione in vigore oggi:
     pubblicarne una»);
   * versione fissata e non più ammessa (solo la revisione, C.1.1): `LISTINO_VERSIONE_NON_ATTIVA`
     e il suo codice restano, se A-D3 tiene la copia.
   * `listino_versione_mancante` resta senza emettitori. Va ritirata dai locales nello stesso giro
     FE.
5. **Contratto** (se A-D2 = rifiutare): `trgfn_contratti_freeze_listino_versione` chiama la stessa
   check, e `fn_available_actions_contratto` spegne «Attiva» col motivo. Il negoziato puro
   (`listino_id` NULL) resta fuori, come oggi.
6. **pgTAP** (A-R5): costruisce listino e versioni da sé, senza appoggiarsi a quelli di dbdev. Copre
   l'offerta nuova emessa con la versione fissata dal DB; il listino senza versione in vigore,
   spento col motivo e rifiutato col codice; la revisione secondo A-D3; il push al contratto con la
   versione dell'offerta (`trgfn_contratti_freeze_listino_versione` non la tocca, è già valorizzata).

Ricadute sul BE, oltre al §A.5: anche il **secondo** lettore di
`ListiniRepository.get_versione_attiva_alla_data` (`offerte_service.py`, risoluzione del
`listino_versione_id_preferito` per il pricing) è una copia del BB. Deve leggere
`vendite.fn_documento_listino_operativo`. Il commento del repository («a DB non esiste un UNIQUE…»)
è stantio: `ex_listini_versioni_no_overlap` garantisce al più una versione in vigore.

### C.2 Parte B, l'erogazione

#### C.2.1 Tre vincoli che il brief non vede

1. **CANONE vuole anche `generazione_canone`**: `chk_contrighe_coerenza_canone` /
   `chk_offerte_eccezioni_coerenza_canone`. Una riga che **eredita** CANONE senza
   `generazione_canone` viene rifiutata dal CHECK, con un messaggio tecnico. L'eredità deve portare
   anche il default di `generazione_canone`, ed eventualmente di `periodicita` e
   `competenza_canone`. Oppure il default dell'erogazione non può essere CANONE. B-R1 si allarga di
   conseguenza.
2. **L'articolo senza tipologia esiste solo sull'AGGIUNTA.** `trgfn_listini_righe_guard_tipologia`
   rifiuta in un listino un articolo senza tipologia (`E_ARTICOLO_TIPOLOGIA_MANCANTE`) o di tipologia
   diversa da quella del listino. Quindi ogni OVERRIDE ha un articolo con tipologia, e la tipologia è
   quella del listino del documento. B-D1 riguarda **solo** le AGGIUNTE (articolo fuori listino).
3. **L'ordine dei trigger è portante.** L'eredità deve scrivere `tipo_erogazione` **prima** di
   `…_a10_default_fonte_qta_…` (la fonte dipende dall'erogazione) e di
   `…_a10_guard_erogazione_obbligatoria_…`. Il nome `…_a10_default_erogazione_da_articolo_ins_upd`
   precede entrambi sulle due tabelle. ⚠️ `default_fonte_qta` è agganciato con
   `UPDATE OF tipo_erogazione, fonte_quantita_attesa`: su un UPDATE l'erogazione scritta da un altro
   trigger `BEFORE` **non** lo fa scattare (linee-guida-trigger, «cosa fa davvero `UPDATE OF`»).
   L'eredità va quindi limitata all'**INSERT**, oppure quel trigger va riagganciato con `WHEN`. La
   proposta è l'INSERT: un UPDATE che svuota l'erogazione è una scelta dell'operatore, e il guard
   d'obbligo resta la rete.

E un fatto sulla forma di oggi: la matrice erogazione × fonte è scritta **quattro volte**. Due
CHECK gemelli, il `CASE` di `trgfn_righe_default_fonte_qta` (due volte nello stesso corpo),
`fontiQuantitaErogazione.js` e `_FONTE_VIETATE_PER_TIPO_EROGAZIONE`. Una quinta copia nella lettura di
B-R4 non è accettabile (regola del 2).

#### C.2.2 La forma proposta

1. **La matrice diventa un dato**: `config.erogazioni_fonti` (`tipo_erogazione`,
   `fonte_quantita_attesa`, `e_default_erogazione`), una riga per combinazione ammessa, seed CSV.
   Sulle due tabelle di riga una **FK composta**
   `(tipo_erogazione, fonte_quantita_attesa) → config.erogazioni_fonti`. Con `MATCH SIMPLE` non
   controlla le righe con un NULL, cioè l'ESCLUSIONE, che resta vuota. La FK prende il posto di
   `chk_*_tipo_erog`, `chk_*_fonte_qta` e `chk_*_coerenza_fonte_erogazione`. Il `CASE` di
   `trgfn_righe_default_fonte_qta` legge `e_default_erogazione` (B-D3: la matrice generica resta
   come **ultimo** ripiego, ma diventa dato e non codice).
   ⚠️ Una FK nuova genera i suoi guard e i suoi indici. Va censito cosa oscura e quali pgTAP
   pinnano i nomi dei CHECK ritirati (presidio: grep dei nomi in `db/pgtap`).
2. **La tipologia dichiara ciò che ammette e il default**: `config.listini_tipologie_erogazioni`
   (`tipologia_id`, `tipo_erogazione`, `fonte_quantita_attesa`, `e_default`), con FK composta su
   `config.erogazioni_fonti` e un UNIQUE parziale «un default per tipologia». I default di canone
   (C.2.1, punto 1) stanno sulla stessa riga quando l'erogazione è CANONE. Il seed copre le sei
   tipologie (B-R5). È la forma «tabella a sé» di B-R1: ammessi e default in un posto solo, senza sei
   colonne sulla tipologia.
3. **Eredità** (B-R2): `script.trgfn_righe_default_erogazione_da_articolo`, generica sulle due
   tabelle come `trgfn_righe_default_fonte_qta`, `BEFORE INSERT`, `WHEN tipo_eccezione <>
   'ESCLUSIONE'`. Riempie solo i campi **NULL**, perché la scelta dell'operatore vince, dentro il
   perimetro del punto 4. Scrive il valore nella riga (non lo deriva in lettura): revisione e push
   ricopiano le colonne, quindi B-R5 «push con i valori ereditati» vale per costruzione.
4. ⚠️ **Superato da B-D4 (§C.5)**: il perimetro è la tipologia dell'articolo, non l'unione della utility.
   **Perimetro** (B-R3): un guard `BEFORE INSERT OR UPDATE` rifiuta una combinazione
   (erogazione, fonte) che **nessuna** tipologia ammessa dalla utility del documento
   (`config.listini_tipologie_utilities`, `utility_id` NOT NULL su offerta e contratto) prevede. Il
   predicato sta in una `fn_check_*` pura sui valori, perché lo legge anche il punto 5. Codice nuovo
   `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` (DATO_ERRATO, `campo = fonte_quantita_attesa` o
   `tipo_erogazione`), con la sua policy.
5. **La lettura per il form** (B-R4): `vendite.fn_documento_riga_erogazioni(p_documento,
   p_documento_id, p_articolo_id)` restituisce le combinazioni ammesse dal perimetro, ciascuna con
   `e_default`, risolte con la **stessa** funzione del trigger d'eredità. Il form preseleziona ciò che
   il DB scriverebbe.

### C.3 Le decisioni di Tid che servono per partire

| # | Domanda | Proposta del team DB |
| --- | --- | --- |
| **A-D1** | CHIUSA può governare un'offerta? | **Chiusa dal modello** (C.1.1): all'emissione la versione in vigore oggi è sempre ATTIVA. Il guard resta «ATTIVA» |
| **A-D2** | Il contratto con listino si attiva senza versione in vigore? | **No**: si rifiuta come l'offerta, con motivo e capability (C.1.2). Rovescia il §4.4 del 2026-05-18 |
| **A-D3** *(nuova)* | La revisione eredita la versione congelata del padre? | **No**: nasce con `listino_versione_id` NULL e congela alla **sua** emissione. Una revisione è una proposta nuova, mandata in un giorno nuovo. ⚠️ Contraddice A-R5 («la revisione porta la versione congelata»), quindi va scelta esplicitamente. Con la copia, invece, la revisione su una versione chiusa non si emette più |
| **B-D1** | L'AGGIUNTA con articolo senza tipologia | Ripiego sulla **natura di vendita**, con una colonna di default su `config.nature_vendita` (MERCE e SERVIZIO_UNA_TANTUM → UNA_TANTUM/FISSA, SERVIZIO_RICORRENTE → CANONE/FISSA + default di canone). **Vince la tipologia** quando c'è. ⚠️ Controesempio sul modello: un articolo SERVIZI può essere una tantum o ricorrente, e un default unico per SERVIZI sbaglia uno dei due. Alternativa: la natura sceglie **fra le combinazioni ammesse dalla tipologia**, e la tipologia decide solo se la natura non vi rientra |
| **B-D1 bis** | Fonte dei generici: FISSA o MANUALE? | Tid indica MANUALE. FISSA vuol dire «la quantità della riga», MANUALE «la scrive l'operatore a ogni periodo». Per un bene una tantum la proposta è FISSA, da confermare |
| **B-D2** | Valore STANDARD di `tipo_erogazione` | **No**, come la sessione BE/FE |
| **B-D3** | La matrice CONSUMO → LETTURE | Resta come **ultimo ripiego**, fatta dato (`e_default_erogazione`), dopo tipologia e natura |
| **B-D4** *(nuova)* | Perimetro della utility o della tipologia dell'articolo? | Tid ha deciso: **la utility**. Effetto da sapere: su ENE un articolo QUOTA_FISSA venduto CONSUMO + LETTURE passa, perché la utility ammette CONSUMO. Da confermare che sia voluto |

### C.4 Ordine di consegna proposto

1. **Parte A da sola, subito dopo A-D2/A-D3**: sblocca l'emissione e non dipende da B.
2. **Parte B**: prima il vocabolario e la FK (C.2.2, punti 1-2, con il censimento dei CHECK
   ritirati), poi eredità, perimetro e lettura.

### C.5 Decisioni di Tid (2026-10-07)

| # | Decisione |
| --- | --- |
| **A-D2** | ✅ Come da proposta: un contratto con listino **non** si attiva senza una versione in vigore. Lo rifiuta il freeze, e la capability spegne «Attiva» col motivo |
| **A-D3** | ✅ Come da proposta: la revisione nasce con `listino_versione_id` NULL e congela alla **sua** emissione. Il punto di A-R5 «la revisione porta la versione congelata» è superato; resta vero per il **push** al contratto |
| **B-D1** | ✅ Come da proposta: vince la tipologia dell'articolo. Senza tipologia (solo AGGIUNTA, C.2.1) si ripiega sulla natura di vendita |
| **B-D1 bis** | ✅ Fonte dei generici FISSA |
| **B-D4** | ⛔ **Non voluto.** Una QUOTA_FISSA si eroga **a periodo** e la sua fonte non sono le letture. Il perimetro non può essere l'unione delle tipologie della utility |

#### C.5.1 Il perimetro dopo B-D4 (sostituisce C.2.2, punto 4)

* **Articolo con tipologia**: le combinazioni ammesse sono quelle di **quella** tipologia
  (`config.listini_tipologie_erogazioni`). In più, la tipologia dev'essere fra quelle ammesse dalla
  utility del documento (`config.listini_tipologie_utilities`). Su un OVERRIDE questo è già vero,
  perché lo garantisce il listino. Su un'AGGIUNTA è un controllo nuovo: un articolo CONSUMO non entra
  in un documento BASE.
* **Articolo senza tipologia** (solo AGGIUNTA): le combinazioni ammesse dalla **natura di vendita**.
  Per questo la natura vuole una tabella gemella, `config.nature_vendita_erogazioni`, con la stessa
  forma e lo stesso default, e non una sola colonna di default. Nessuna natura ammette LETTURE: le
  letture vengono da una tipologia a contatore.
* Il default (B-R2) è quello dichiarato `e_default` dalla stessa sede del perimetro. Perimetro e
  default non possono dissentire.
* Codici: `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` (combinazione non ammessa, campo
  `fonte_quantita_attesa` o `tipo_erogazione`) e `E_RIGA_TIPOLOGIA_FUORI_UTILITY` (AGGIUNTA di un
  articolo con una tipologia che la utility non ammette, campo `articolo_id`).

#### C.5.2 Seed proposto (B-R5), da confermare prima di scriverlo

| Tipologia / natura | Ammesse (⭐ = default) |
| --- | --- |
| CONSUMO | ⭐ CONSUMO/LETTURE · CONSUMO/MANUALE |
| QUOTA_FISSA | ⭐ CANONE/FISSA |
| IMPOSTA | ⭐ CONSUMO/LETTURE · CANONE/FISSA |
| ONERE_SISTEMA | ⭐ CONSUMO/LETTURE · CANONE/FISSA |
| PRODOTTI | ⭐ UNA_TANTUM/FISSA · UNA_TANTUM/MANUALE |
| SERVIZI | ⭐ UNA_TANTUM/FISSA · UNA_TANTUM/MANUALE · CANONE/FISSA · CONSUMO/MANUALE |
| natura MERCE | ⭐ UNA_TANTUM/FISSA · UNA_TANTUM/MANUALE |
| natura SERVIZIO_UNA_TANTUM | ⭐ UNA_TANTUM/FISSA · UNA_TANTUM/MANUALE · CONSUMO/MANUALE |
| natura SERVIZIO_RICORRENTE | ⭐ CANONE/FISSA · CONSUMO/MANUALE |

* Su ogni riga CANONE il seed porta anche `generazione_canone` (il CHECK la pretende): proposta
  **INIZIO_PERIODO**, da confermare.
* ORARIO resta nel vocabolario generico (`config.erogazioni_fonti`), ma nessuna tipologia o natura
  lo ammette finché il modulo timesheet non c'è (§B.4).
* ⚠️ Con il default dalla tipologia, un articolo SERVIZI ricorrente nasce UNA_TANTUM: la natura non
  vince sulla tipologia (B-D1). L'operatore sceglie CANONE, che il perimetro ammette. Se diventa un
  fastidio, la strada è il raffinamento scritto in §C.3, cioè la natura che sceglie fra le
  combinazioni della tipologia.

### C.6 Consegna della parte A (team DB, 2026-10-07)

#### C.6.1 ChangeSet

| ChangeSet | Oggetto | Cosa |
| --- | --- | --- |
| `20261007-40` | `vendite.fn_listino_versione_operativa` (nuova) | la versione fissata, altrimenti quella in vigore oggi, sui **valori** della testata |
| `20261007-41` | `script.fn_check_listino_congelabile` (nuova) | i motivi per cui un'offerta non si emette o un contratto non si attiva per la versione di listino |
| `20261007-42` | `vendite.fn_documento_listino_operativo` | la sua `COALESCE` passa a `-40`, stesso esito |
| `20261007-43` | `vendite.trgfn_offerte_commerciali_guard_transizione` | BOZZA → EMESSA: primo motivo della check, poi **congela** `listino_versione_id` (A-R1) |
| `20261007-44` | `script.fn_available_actions_offerta` | «Emetti» dalla check sulla versione che verrebbe congelata, non dalla colonna nuda (A-R2) |
| `20261007-45` | `vendite.trgfn_contratti_freeze_listino_versione` | senza versione in vigore il contratto con listino **non** si attiva (A-D2). Una versione già fissata dal push resta, anche se chiusa |
| `20261007-46` | `script.fn_available_actions_contratto` | «Attiva» spento col motivo, prima dei prezzi |
| `20261007-47` | `vendite.fn_crea_revisione_offerta` | la revisione nasce con `listino_versione_id` NULL (A-D3) |

Ogni `CREATE OR REPLACE` parte dall'ultimo changeSet dell'oggetto: il `prosrc` è stato verificato
uguale al vivo su dbdev e su `zeroerp_ci` il 2026-10-07. Le sostituzioni sono contate e il
rollback è il blocco precedente alla lettera. ⚠️ `-45` riscrive anche il COMMENT, che descriveva
ancora l'attivazione senza versione; il rollback non lo ripristina.

**Codici** (CSV `messaggi_errore` / `codici_errore`):

* `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO` (457): testo riscritto, «il listino di riferimento
  non ha una versione in vigore oggi». Prima diceva «versione non impostata».
* `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` (458): invariato.
* `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` (**1201, nuovo**): CONFLITTO_STATO, frase
  chiusa.

#### C.6.2 pgTAP

* **Nuovo** `vendite/offerte_commerciali/test-offerta-emissione-congela-listino-v1` (25
  asserzioni, fixture costruita: un listino valido da oggi e uno con la sola versione 2022). Copre
  la regola sui valori; «Emetti» acceso su un'offerta senza versione (il difetto del collaudo);
  l'emissione che congela; il listino senza versione in vigore, spento e rifiutato con lo stesso
  codice; la revisione senza versione che congela alla sua emissione; la versione fissata CHIUSA;
  il contratto rifiutato, congelato o che tiene la versione del push; il codice a catalogo.
* **Aggiornati**, perché pinnavano la forma vecchia:
  * `script/test-fn-available-actions-offerta-v1` 16a/16b: pretendeva «Emetti» spento con
    `LISTINO_VERSIONE_MANCANTE`, cioè il difetto stesso;
  * `script/test-rubinetto-primo-motivo-v1` test 5: da 32 a 33, il freeze del contratto è un
    sito nuovo dell'helper;
  * `vendite/test-listino-versione-in-vigore-v1` test 13: l'elenco dei consumatori della sede
    unica, con la regola sui valori in mezzo (da 7 a 10);
  * `vendite/offerte_commerciali/test_offerte_commerciali_state_machine` test 2: il rifiuto
    vuole un listino **senza** versione in vigore, ora costruito. Prima prendeva il «primo per id»
    del DB.

#### C.6.3 La prova (2026-10-07, prima dell'apply)

Su `zeroerp_ci`, come owner (le credenziali disponibili), in transazione annullata con l'SQL
**estratto** dagli YAML:

* tutti gli otto blocchi compilano; `plpgsql_check` non dà errori. Restano due avvisi
  STABLE/VOLATILE dal ramo d'errore, gli stessi che il BB aveva già. Una firma sola per funzione;
* il pgTAP nuovo dà 24/25 senza il CSV e 25/25 con le due righe del codice simulate. Il 22 legge
  il catalogo, che si carica in `80_data`;
* **regressione**: 46 pgTAP vicini (capability, offerte, contratti con listino, revisioni, push,
  presidi dei motivi e dei messaggi), eseguiti ciascuno prima e dopo l'SQL estratto. Si sono
  mossi solo i tre file pinnati qui sopra, rossi prima della correzione e verdi dopo. Gli `err`
  presenti già «prima» sono fixture che prendono dati da dbdev e su `zeroerp_ci` non li trovano:
  identici prima e dopo;
* ⚠️ `test_offerte_commerciali_state_machine` su `zeroerp_ci` non parte nemmeno prima (fixture da
  dbdev). Il test 2 corretto lo vede solo la tua corsa;
* rollback: eseguiti dopo i changeSet riportano i sei corpi identici al vivo (md5) e tolgono le
  due funzioni nuove.

⚠️ Non provato: la corsa come app sotto RLS e i presidi trasversali completi. Restano della tua
corsa.

Fatto datato (dbdev, 2026-10-07, letto come app nel contesto dell'operatore di prova): **0**
contratti ATTIVO con listino e versione NULL, **1** offerta in BOZZA con una versione già fissata
(una revisione nata con la copia). Nessuno dei due casi viene corretto dai changeSet. La
revisione si emette se la versione copiata è ancora ATTIVA; altrimenti «Emetti» è spento col
motivo. **Da decidere con Tid se correggerla a mano.** Verificato lo stesso giorno: è
`OFC-0000181` (rev. 2), e la versione copiata (`v1-clone`) è ATTIVA ed è proprio quella in vigore
oggi. All'emissione congela la stessa versione che sceglierebbe la regola nuova, quindi
**nessuna correzione** serve (proposta a Tid).

#### C.6.4 Richieste al BE/FE, dopo l'apply (aggiornano il §A.5)

* **BE**: ritirare `OfferteService._fissa_versione_listino_se_necessario` e la sua chiamata in
  `emetti`. Il secondo lettore di `ListiniRepository.get_versione_attiva_alla_data` (la versione
  preferita del pricing in `offerte_service.py`) deve leggere
  `vendite.fn_documento_listino_operativo`. Poi il metodo si ritira, perché è una copia della
  regola. Rigenerare le policy per `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` (ripiego senza
  `%s`) e aggiornare il ripiego di `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`. Va tolto anche
  il «warning UI» del contratto attivo senza versione, se esiste (§4.4 del 2026-05-18).
* **FE**, due `reason_key` nuove (`scripts/check_i18n_keys.py` è rosso finché mancano):
  * `vendite.offerte.azione_reason.listino_senza_versione_in_vigore`, per esempio «Il listino non
    ha una versione in vigore oggi: pubblicane una o scegli un altro listino.»;
  * `vendite.contratti.azione_reason.listino_senza_versione_in_vigore`, per esempio «Il listino non
    ha una versione in vigore oggi: il contratto non si può attivare.».
* **FE**: ritirare `vendite.offerte.azione_reason.listino_versione_mancante`, che non ha più
  emettitori.
* Doc: `api_offerte.md` § emissione e `api_contratti.md` § attivazione.

#### C.6.5 Dopo l'apply: le regressioni dei fixture presi dai dati (2026-10-07)

Tid ha applicato `-40 → -47` e la corsa su dbdev ha dato rossi che la prova pre-apply non aveva
visto. **Perché non li aveva visti**: quei file prendono billing account e listino «primo per id» dai
dati di dbdev. Su `zeroerp_ci` i dati non ci sono, il fixture non costruisce niente e i conteggi
«prima/dopo» risultavano uguali. La prova era cieca proprio su di loro (§C.6.3 va letto così).

La causa è una sola, ed è la decisione A-D2: il fixture **attiva** un contratto su un listino che
oggi non ha una versione in vigore. Prima l'attivazione passava con la versione NULL. Ora è
rifiutata, e siccome avviene fuori da un'asserzione il file muore.

| File | Correzione |
| --- | --- |
| `vendite/test-bozza-non-operativa-e-preview-contratto-v1` | il caso «ATTIVO su listino BOZZA-only» non è più costruibile. Il test 3 diventa «attivazione rifiutata», il 6 «resta DRAFT, versione NULL» |
| `vendite/test-contratti-modalita-pricing-v1` | listino costruito (`dbops.fn_pgtap_crea_listino`, versione da oggi) |
| `vendite/test-fn-resolve-prezzo-listino-v2-step24-v1` | listino costruito. I test 6-7 (COND, versione in vigore con righe) vanno in skip, come già facevano sul listino dei dati |
| `vendite/test-contratti-guard-transizione-stato-v1` | listino costruito |

Censimento statico degli altri file che attivano contratti o emettono offerte su un listino preso
dai dati:

* `test-contratti-step23-v1` attiva solo se il listino ha una versione in vigore (COND);
* `test-contratti-schema-step22-v1`, `test-fn-resolve-prezzo-listino-v2-classe-da-contratto-v1` e
  `test-vw-dash-*` inseriscono il contratto già ATTIVO, e il freeze scatta solo sull'UPDATE;
* `test_fn_push_offerta_successione`, `test_offerte_commerciali_end_to_end`, `test_fn_push_*` e
  gli altri test delle offerte fissano una versione ATTIVA, che la regola 2 della check ammette.
  Le revisioni che creano non vengono emesse.

Su `zeroerp_ci` i quattro file non costruiscono i fixture, né prima né dopo: l'esito vero è quello
della corsa su dbdev. Lezione salvata: una prova su ci con «prima = dopo» su un fixture vuoto vuol
dire «non provato», non «verde».

⚠️ **Secondo giro, stesso giorno.** Tre di quei file (`modalita-pricing`, `guard-transizione-stato`,
`step24`) erano già nel registro dei rossi di CI (`baseline-rossi-ci.tsv`, righe 188, 189, 269):
anche il billing account era preso dai dati. Il listino costruito li faceva fermare sull'utility
NULL e cambiava la classe del rosso. Corretti fino in fondo: anche cliente e BA sono costruiti
(`dbops.fn_pgtap_crea_cliente_ba`). Su `zeroerp_ci`, come owner e con `-40 → -47` in testa: 4/4,
9/9, 9/9. ⏳ Dopo la corsa di Tid **come app** su CI, le tre righe escono dal registro (anche da
`baseline-rossi-scratch.tsv`, righe 66, 67, 140).

### C.7 Parte B: piano di consegna (team DB, 2026-10-07, dopo i pgTAP verdi della parte A)

Quattro giri, ognuno applicabile da solo:

| Giro | Cosa | Effetto visibile |
| --- | --- | --- |
| **B1** | Vocabolario `config.erogazioni_fonti` (combinazioni coerenti + default della fonte per erogazione, seed CSV). FK composta dalle due tabelle di riga; ritiro dei tre CHECK gemelli (`chk_*_tipo_erog`, `chk_*_fonte_qta`, `chk_*_coerenza_fonte_erogazione`). `trgfn_righe_default_fonte_qta` legge il default dalla tabella | **nessuno**: le stesse combinazioni di oggi, scritte come dato |
| **B2** | `config.listini_tipologie_erogazioni` e `config.nature_vendita_erogazioni` col seed del §C.5.2 (e `generazione_canone` = INIZIO_PERIODO sulle righe CANONE) | nessuno: tabelle senza lettori |
| **B3** | La regola: BB «combinazioni dell'articolo» (tipologia, altrimenti natura). Trigger d'eredità `BEFORE INSERT`, che riempie i campi vuoti col default. Guard del perimetro, che chiama una `fn_check_*` sui valori. Codici `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` e `E_RIGA_TIPOLOGIA_FUORI_UTILITY` | **sì**: righe ereditate, combinazioni fuori perimetro rifiutate |
| **B4** | Lettura per il form: `vendite.fn_documento_riga_erogazioni(documento, id, articolo)`, dalla stessa BB | il BE/FE può ritirare `fontiQuantitaErogazione.js` e la copia Python |

⚠️ **Il costo vero è B3 sui pgTAP**: 26 file inseriscono righe con un'erogazione scritta a mano,
quasi sempre `CANONE`/`FISSA` su un articolo qualunque. Il censimento statico si fa **prima** di
scrivere B3, file per file (articolo → tipologia o natura → combinazione), su dbdev e non solo su
`zeroerp_ci` (lezione del §C.6.5). Quattro file e un test BE nominano i CHECK che B1 ritira.

Il ripiego sulla natura (B-D1) si prova quanto il ramo della tipologia: `listino_tipologia_id` è
nullable, quindi il modello ammette l'articolo senza tipologia e il ramo esiste. Fatto datato, che
non decide niente: su dbdev, il 2026-10-07, 15 articoli attivi sono PRODOTTI, 16 SERVIZI e 221 senza
tipologia.

**Da decidere prima di B3** (Tid):

* **B-D5, `DERIVATA_COMPONENTI`**: la fonte del padre di un bundle, che il form propone e il seed
  del §C.5.2 non nomina. Proposta: ammessa per **ogni articolo composito**, accanto a ogni
  erogazione che la tipologia o la natura ammette (se il vocabolario B1 la dichiara coerente). È un
  fatto della distinta, non della tipologia.
* **B-D6, le righe già scritte**: il guard del perimetro scatta su INSERT e quando cambiano
  articolo, erogazione o fonte. Le righe di oggi fuori perimetro restano dove sono. Proposta: sì, e
  un presidio a catalogo che le conta, invece di una bonifica alla cieca.

**Decisioni di Tid (2026-10-07, sera):**

* **B-D5** ✅ come da proposta: `DERIVATA_COMPONENTI` è ammessa per ogni articolo composito, con
  ogni erogazione che la tipologia o la natura ammette, se il vocabolario B1 la dichiara coerente.
  ⛔ **Superata dal §I (I-D1, 2026-10-21)**: la DERIVATA si ritira, i componenti seguono sempre
  la quantità del padre.
* **B-D6** ✅ le righe già scritte restano come sono, **senza presidio**: sono solo dati di test.
  Il guard scatta su INSERT e quando cambiano articolo, erogazione o fonte.
  ⛔ **Superata dal §H (2026-10-11)**: il perimetro dipende da dati che stanno fuori dalla riga,
  quindi il controllo serve anche all'emissione e alla trasformazione, non solo alla scrittura.

### C.8 Consegna dei giri B1 e B2 (team DB, 2026-10-07)

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/config/20261007-50` | `config.erogazioni_fonti`: le combinazioni coerenti erogazione/fonte, `e_default` (al più uno per erogazione, indice unico parziale) |
| `00_schema/config/20261007-51` | `config.listini_tipologie_erogazioni` e `config.nature_vendita_erogazioni`: combinazioni ammesse, default, `generazione_canone` sulle righe CANONE (CHECK: valorizzata se e solo se CANONE). FK composta sul vocabolario |
| `20_code/script/20261007-52` | `script.trgfn_righe_default_fonte_qta` legge il default e la coerenza dal vocabolario; ritirato il CASE della matrice |
| `80_data/changelog/20261007-53` + 3 CSV | seed dei tre vocabolari (mirror `loadUpdateData`, `nullValue: "NULL"`) |
| `80_data/changelog/20261007-54` | FK `(tipo_erogazione, fonte_quantita_attesa)` dalle due tabelle di riga su `config.erogazioni_fonti`; ritirati i sei CHECK della matrice. In `80_data` perché punta a righe di seed (forma di `20261004-22`) |

**Effetto visibile: nessuno.** Il vocabolario contiene esattamente le 13 combinazioni che i CHECK
ammettevano, con i default del CASE ritirato. Cambiano solo due cose:

* una combinazione fuori vocabolario esce **23503** (nome della FK), non più 23514 (nome del CHECK);
* una riga **senza erogazione** non prende più la fonte FISSA, ma il guard d'obbligo la rifiuta
  comunque, come prima.

**pgTAP**: nuovo `vendite/test-erogazioni-vocabolario-v1` (12: vocabolario uguale alla matrice
ritirata; completezza dei default per erogazione, tipologia e natura; nessuna natura a LETTURE;
QUOTA_FISSA solo CANONE; FK presenti, CHECK ritirati; trigger che legge il vocabolario). Aggiornati
`vendite/test-contratti-righe-coerenza-fonte-erogazione` (test 2: la FK; test 5-11: 23503) e
`vendite/offerte_commerciali/test_offerte_commerciali_eccezioni_struttura` (test 4, 5, 7: la FK
al posto dei tre CHECK).

**Prova** (su `zeroerp_ci`, come owner, in transazione annullata con l'SQL estratto e il seed
**simulato** dai CSV):

* compila tutto e `plpgsql_check` non segnala niente; `zeroerp_app` ha `SELECT` sulle tre tabelle
  nuove, dai privilegi di default (il trigger le legge come INVOKER);
* regressione su 38 pgTAP che toccano righe, erogazione o fonte, prima e dopo: si muovono solo i
  tre file aggiornati;
* rollback: trigger identico al vivo (md5), i sei CHECK tornano.

⚠️ **Non provati**: il loader di Liquibase (il seed è simulato: `nullValue` e tipi delle colonne
li prova solo l'apply) e `test-contratti-righe-coerenza-fonte-erogazione` su dbdev. Su
`zeroerp_ci` il suo fixture prende contratto e articoli dai dati, quindi i test 5-11 vanno in skip.
Su dbdev girano e ora aspettano 23503 (lezione del §C.6.5).

**Al BE, a consegna fatta**: il codice nomina `chk_contrighe_coerenza_fonte_erogazione` solo nei
commenti (`contratti_service.py` righe 368 e 2286, `test_contratti_service.py` riga 2243). Nessuna
traduzione d'errore lo usa, quindi niente si rompe. I commenti vanno aggiornati, e la copia Python
della matrice si ritira con B4.

### C.9 Consegna dei giri B3 e B4 (team DB, 2026-10-07 sera)

#### C.9.1 ChangeSet

| ChangeSet | Oggetto | Cosa |
| --- | --- | --- |
| `20_code/vendite/20261007-60` | `vendite.fn_articolo_erogazioni(articolo)` | **la sede unica del perimetro**: combinazioni ammesse e default, dalla tipologia; senza tipologia, dalla natura (B-D1). Sul composito si aggiunge DERIVATA_COMPONENTI, mai di default (B-D5) |
| `20_code/script/20261007-61` | `script.fn_check_riga_erogazione(...)` | check sui valori. Due motivi: `E_RIGA_TIPOLOGIA_FUORI_UTILITY` (campo `articolo_id`) e `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` (campo `fonte_quantita_attesa` se l'erogazione è ammessa con un'altra fonte, `tipo_erogazione` altrimenti) |
| `20_code/script/20261007-62` | `script.trgfn_righe_default_erogazione_da_articolo()` | **eredità** (B-R2). Su INSERT riempie solo i campi vuoti: erogazione, fonte, `generazione_canone`. Su UPDATE della sola erogazione riallinea la fonte a quella dell'articolo |
| `20_code/script/20261007-63` | `script.trgfn_righe_guard_erogazione_perimetro()` | **guard** (B-R3/B-D4): solleva il primo motivo della check, col campo |
| `20_code/vendite/20261007-64` | 6 trigger sulle due tabelle gemelle | `…_a10_default_erogazione_articolo_ins_upd` (INSERT, UPDATE OF `tipo_erogazione`), `…_a10_guard_erogazione_perimetro_ins`, `…_upd` (solo quando cambiano articolo, erogazione o fonte: B-D6). Ordine: eredità → fonte generica → obbligo → perimetro |
| `20_code/vendite/20261007-65` | `vendite.fn_documento_riga_erogazioni(documento, id, articolo)` | **la lettura per il form** (B-R4, giro B4): le combinazioni dell'articolo col default in testa, oppure nessuna se la tipologia è fuori utility |

Codici nuovi (CSV): `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` (1202) ed `E_RIGA_TIPOLOGIA_FUORI_UTILITY`
(1203), entrambi DATO_ERRATO, con frase chiusa.

#### C.9.2 Due difetti trovati scrivendo, già corretti nel giro

* **Fonte indicata senza erogazione.** Nella prima stesura il trigger metteva l'erogazione di
  default e teneva la fonte data: poteva nascere CONSUMO/FISSA, e il guard lo rifiutava. Ora sceglie
  un'erogazione che l'articolo ammette **con quella fonte**, partendo dal default.
* **UPDATE che cambia la sola erogazione.** `trgfn_righe_default_fonte_qta` rimetteva la fonte di
  default del **vocabolario**: un servizio passato da CANONE a CONSUMO prendeva LETTURE, che la sua
  natura non ammette. Ora la fonte si riallinea a quella che l'**articolo** ammette. Se
  l'operatore cambia anche la fonte, la scelta è sua e la giudica il guard: nessuna correzione
  silenziosa.

#### C.9.3 pgTAP

* **Nuovo** `vendite/test-righe-erogazione-da-articolo-v1` (20 test, fixture costruita). Copre:
  la sede unica (tipologia contro natura, composito, articolo inesistente); i tre casi
  d'eredità; i due rifiuti coi canali; l'ESCLUSIONE non giudicata; il riallineamento su UPDATE e
  la scelta esplicita non toccata; B-D6 (la riga fuori perimetro si aggiorna negli altri campi,
  ma non le si cambia la fonte); la lettura per il form; il push offerta → contratto coi valori
  ereditati (B-R5); l'ordine dei trigger; i codici a catalogo.
* `script/test-rubinetto-primo-motivo-v1` test 5: da 33 a 34.
* **Il significato cambia** in `vendite/test-righe-erogazione-obbligatoria-v1`. Una riga senza
  erogazione ora la eredita; il guard d'obbligo resta e morde l'UPDATE che la svuota, e lì si
  leggono frase e canali.
* `vendite/test-contratti-righe-coerenza-fonte-erogazione`: le combinazioni fuori vocabolario
  ora le rifiuta il perimetro (P0001), che parla prima della FK (la rete). ORARIO non lo ammette
  nessuno (§B.4). Il riallineamento su UPDATE va alla fonte dell'articolo (MANUALE).
* **Fixture adattati**, perché scrivevano CANONE (o CONSUMO/LETTURE) a mano su articoli che il
  perimetro non lo consente. In tutti i casi l'erogazione era incidentale al soggetto del test:
  `rls/test-rls-contratti-satelliti`, `rls/test-rls-offerte-satelliti`,
  `script/test-fn-check-prezzi-autorizzati-v1`, `vendite/test-contratto-esclusione-non-modificabile-v1`,
  `vendite/test-contratto-righe-lista-v1`, `vendite/test-contratto-righe-lista-uom-riga-v1`,
  `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1`, `vendite/test-fn-list-contratti-da-pushare-v1`,
  `vendite/test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1`, `vendite/test-righe-esclusione-solo-non-si-vende-v1`,
  `vendite/test-righe-gemelle-secondo-giro-v1`, `vendite/test-fn-resolve-prezzo-listino-v2-step24-v1`.
  La forma è la stessa ovunque: l'erogazione **ereditata** (colonne vuote) dove l'articolo sta nel
  listino del test; UNA_TANTUM sugli articoli MERCE del builder; un articolo scelto **chiedendo
  alla sede unica** che ammetta la combinazione, dove l'articolo viene dai dati.

#### C.9.4 ⚠️ I fixture presi dai dati di dbdev

Su dbdev (letto il 2026-10-07):
* il primo billing account è GAS, il primo «senza tipi utenze» è TEL;
* i primi due articoli per id sono PRODOTTI, che né GAS né TEL ammettono;
* i compositi sono SERVIZI.

Ogni fixture che accoppiava quei dati sarebbe stato fermato da `E_RIGA_TIPOLOGIA_FUORI_UTILITY`,
qualunque erogazione scrivesse. Su `zeroerp_ci` i fixture non trovano dati, quindi la prova lì
**non li vede** (§C.6.5). Corretti con lettura statica, file per file, senza poterli eseguire
sui dati di dbdev:

`vendite/offerte_commerciali/test_fn_crea_revisione_offerta`, `test_fn_push_offerta_a_contratto`,
`test_offerte_eccezioni_guard_pending`, `test_push_offerta_fissa_qta_operativa` (articoli del
builder), `test_offerte_eccezioni_componenti` e `test_offerte_eccezioni_qta_from_operativa`
(articoli scelti sul perimetro, cliente la cui utility ne ammette la tipologia),
`vendite/test-bozza-non-operativa-e-preview-contratto-v1`, `test-contratti-overlap-draft-escluso-v1`,
`test-contratti-righe-guard-pending-v1`, `test-contratti-schema-step22-v1`, `test-contratti-step23-v1`,
`test-fn-contratto-righe-preview-nuovi-campi-v1` (B-D5: la fonte DERIVATA_COMPONENTI del caso 8 era
su un articolo non composito, ora UNA_TANTUM/MANUALE), `test-fn-resolve-prezzo-listino-v2-v1`.

**Sono i file da guardare per primi nella corsa su dbdev.**

#### C.9.5 Prova (2026-10-07, prima dell'apply)

* Su `zeroerp_ci`, come owner, in transazione annullata con l'SQL estratto, e con B1/B2 già
  applicati sullo scratch: tutto compila, `plpgsql_check` dà solo il solito avviso STABLE/VOLATILE
  del ramo d'errore, il rubinetto conta 34, il rollback toglie tutto.
* Regressione su 43 pgTAP, ciascuno da solo prima e dopo. I file riscritti per il contratto nuovo
  sono rossi senza B3 (chiamano le funzioni nuove) e verdi con. Quelli coi fixture presi dai dati
  danno con B3 gli stessi rossi di CI che avevano prima (`overlap-draft` 6/2, `step22` 13/4,
  `step23` 7/6, `qta_from_operativa` 7/6). `preview-nuovi-campi` scende da 3 rossi a 1. Il test
  nuovo dà 19/20, perché il 20 legge il catalogo. `riferimenti-morti`, il catalogo dei messaggi e
  il classificatore dei motivi non si muovono.
* ⚠️ Non provati: la corsa come app e i fixture presi dai dati di dbdev (§C.9.4).

#### C.9.6 Richieste al BE/FE (aggiornano il §B.5)

* **BE, test Django che scrivono righe sul DB** (rossi attesi dopo l'apply, lato BE):
  `vendite/tests/db/test_righe_erogazione_obbligatoria_db.py` (OVERRIDE CANONE/FISSA; e la regola
  è cambiata: senza erogazione la riga eredita), `vendite/tests/db/test_ricerca_liste_db.py`,
  `vendite/tests/db/test_contratto_esclusione_non_modificabile_db.py`,
  `vendite/tests/db/test_scritture_dinamiche_vendite_db.py`. Stessa ricetta dei pgTAP: articolo
  e combinazione nel perimetro, o colonne vuote che ereditano.
* **BE**: esporre `vendite.fn_documento_riga_erogazioni` per il form. Ritirare
  `_FONTE_VIETATE_PER_TIPO_EROGAZIONE` e i default di `contratti_service.py`. Policy dei due codici
  nuovi; il campo viaggia nel canale COLUMN.
* **FE**: il form delle righe (`RigheEccezioniDrawer`) legge le combinazioni e preseleziona quella
  di default; erogazione e fonte possono restare vuote, perché le eredita il DB. Ritirare
  `fontiQuantitaErogazione.js` e la sua spec.

#### C.9.7 Dopo l'apply di B3 (2026-10-07, notte)

* `vendite/test-bozza-non-operativa-e-preview-contratto-v1` su dbdev: `ex_contratti_no_overlap`
  all'attivazione del contratto MX del fixture. **Causa mia**: la correzione del §C.9.4 sceglieva
  il primo billing account la cui utility ammette PRODOTTI, e su dbdev quel cliente ha già un
  contratto attivo sovrapposto alle date del fixture. **Correzione**: il cliente si costruisce
  (`dbops.fn_pgtap_crea_cliente_ba`, sulla prima utility che ammette la tipologia del listino
  copiato); un cliente nuovo non ha contratti. In più, i tre contratti del fixture nascono solo se
  il listino da copiare esiste, perché su CI non c'è. Su `zeroerp_ci` di nuovo 8/8 (6 in skip),
  come prima.
* Lezione, per gli altri file del §C.9.4: scegliere dai dati un cliente «compatibile» sposta il
  fixture su un cliente con una storia propria (contratti, sovrapposizioni). Dove il test attiva
  un contratto, il cliente si costruisce. `test-fn-resolve-prezzo-listino-v2-v1` esclude già i
  clienti con contratti sull'istanza; `preview-nuovi-campi` inserisce solo contratti DRAFT, che il
  vincolo di sovrapposizione non conta.

### C.10 Chiusura del lato DB (2026-10-07, notte)

**Applicati da Tid, pgTAP verdi su dbdev**: parte A (`20261007-40 → -47`), giri B1+B2
(`-50 → -54`, già committati) e B3+B4 (`-60 → -65`), con i codici 1201-1203.

| Richiesta | Esito |
| --- | --- |
| A-R1 il congelamento all'emissione è del DB | ✅ `trgfn_offerte_commerciali_guard_transizione` congela su BOZZA → EMESSA |
| A-R2 capability e guard leggono la stessa regola | ✅ `script.fn_check_listino_congelabile` |
| A-R3 CHIUSA | ✅ chiusa dal modello (§C.1.1) |
| A-R4 motivo e testo veri | ✅ `LISTINO_SENZA_VERSIONE_IN_VIGORE`, testo riscritto; ⏳ chiave i18n al FE |
| A-R5 pgTAP | ✅ `test-offerta-emissione-congela-listino-v1`. La revisione congela alla sua emissione (A-D3) |
| A-D2 il contratto | ✅ senza versione in vigore non si attiva (`E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`) |
| B-R1 la tipologia dichiara come si eroga | ✅ `config.listini_tipologie_erogazioni`, più `config.nature_vendita_erogazioni` per il ripiego |
| B-R2 la riga eredita dall'articolo | ✅ `script.trgfn_righe_default_erogazione_da_articolo` |
| B-R3 il perimetro | ✅ la tipologia dell'articolo, dentro la utility (B-D4); `script.trgfn_righe_guard_erogazione_perimetro` |
| B-R4 una lettura per il form | ✅ `vendite.fn_documento_riga_erogazioni`; ⏳ BE la espone, FE ritira `fontiQuantitaErogazione.js` |
| B-R5 seed e pgTAP | ✅ seed in tre CSV; `test-erogazioni-vocabolario-v1`, `test-righe-erogazione-da-articolo-v1` |
| La matrice erogazione/fonte in un posto | ✅ `config.erogazioni_fonti` + FK; ritirati i sei CHECK e il CASE del trigger. ⏳ Restano le due copie BE/FE |

**Cosa resta, tutto fuori dal DB:**

* **BE**: ritirare `_fissa_versione_listino_se_necessario` e `get_versione_attiva_alla_data`
  (§C.6.4); esporre `fn_documento_riga_erogazioni` e ritirare `_FONTE_VIETATE_PER_TIPO_EROGAZIONE`
  e i default di `contratti_service.py` (§C.9.6); policy dei codici 1201-1203; adattare i test
  Django che scrivono righe sul DB (§C.9.6).
* **FE**: le chiavi `vendite.offerte.azione_reason.listino_senza_versione_in_vigore` e
  `vendite.contratti.azione_reason.listino_senza_versione_in_vigore` (`check_i18n_keys` rosso
  finché mancano); ritirare `listino_versione_mancante`; il form delle righe legge le
  combinazioni e preseleziona il default; ritirare `fontiQuantitaErogazione.js`.
* **Doc**: `api_offerte.md` (emissione), `api_contratti.md` (attivazione), `modello-contratti.md`
  (erogazione dall'articolo).
* **Registro dei rossi di CI**: le righe di `test-contratti-modalita-pricing-v1`,
  `test-contratti-guard-transizione-stato-v1` e `test-fn-resolve-prezzo-listino-v2-step24-v1` in
  `baseline-rossi-ci.tsv` (188, 189, 269) e `baseline-rossi-scratch.tsv` (66, 67, 140) escono dopo
  la corsa CI come app (§C.6.5): ora i fixture si costruiscono.

**Lasciato fuori, da dichiarare** (non chiesto da questo brief):

* una versione di listino si può **inserire** già CHIUSA, con date qualsiasi: nessun guard
  sull'INSERT (§C.1.1). Da chiudere in un giro `listini`.
* `periodicita` e `competenza_canone` non hanno default dalla tipologia: nessun vincolo né
  funzione le pretende oggi (§C.7). Se la fatturazione del canone le chiederà, la sede è già
  pronta (`*_erogazioni`).
* ORARIO resta nel vocabolario e non lo ammette nessuna tipologia né natura (§B.4).

**Lezioni del cantiere** (salvate in memoria): una prova di regressione su `zeroerp_ci` è cieca
sui fixture che prendono i dati dalla macchina, perché «prima = dopo» su un fixture vuoto vuol
dire «non provato» (§C.6.5). Scegliere dai dati un cliente «compatibile» lo sposta su un cliente
con una storia propria: dove il test attiva un contratto, il cliente si costruisce (§C.9.7).

## D. Giro BE/FE (`dev/backend-tid`, 2026-10-07)

> Sostituisce §A.5 e §B.5, esegue §C.6.4 e §C.9.6. Non committato: lo decide Tid.

### D.1 Parte A — l'emissione

* **Congelamento**: ritirato `OfferteService._fissa_versione_listino_se_necessario` e la sua
  chiamata in `emetti`, che ora fa il solo cambio stato. Il codice `E_VENDITE_VALIDATION` di quel
  ramo non esiste piu': parla il DB (`E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`).
* **La versione del pricing** la legge un BB solo, `listino_versione_operativa(documento, id)`
  (`apps/vendite/db/_documento_eccezioni_repo.py`, su `vendite.fn_documento_listino_operativo`),
  per **l'offerta e il contratto**. Ritirate le **due** copie Python della regola:
  `ListiniRepository.get_versione_attiva_alla_data` (quella del brief) e
  `ContrattiRepository.get_listino_versione_attiva_alla_data`, che il brief non nominava ed era la
  stessa copia sul contratto (simmetria). ⚠️ **Cambio di comportamento, da sapere**: le due copie
  cercavano la versione alla data d'**inizio** del documento (`validita_dal` / `valido_dal`), il DB
  quella in vigore **oggi** — la stessa che le righe a video usavano gia'. Ora prezzo suggerito e
  righe coincidono per costruzione; su un documento in BOZZA che parte nel futuro, se nel frattempo
  il listino cambia versione, il prezzo suggerito e' quello di oggi, come le righe.
* **Codici**: policy rigenerate dal catalogo (`genera_error_policies`: solo i tre codici nuovi
  1201-1203); ripieghi senza `%s` per i tre nuovi e testo riscritto per il 457, come il CSV.
* **FE**: le due `reason_key` nuove in `it.json`/`en.json`
  (`vendite.offerte.azione_reason.listino_senza_versione_in_vigore`,
  `vendite.contratti.azione_reason.listino_senza_versione_in_vigore`); ritirata
  `vendite.offerte.azione_reason.listino_versione_mancante`. `check_i18n_keys` pulito.
* **Il «warning UI» del contratto attivo senza versione** (§4.4 del 2026-05-18): non esiste come
  avviso dell'ATTIVO. L'avviso che resta nel drawer delle righe del contratto
  (`preview_listino_senza_versione`) descrive il DRAFT su un listino senza versione in vigore — la
  preview e' vuota, legittimamente — e resta.

### D.2 Parte B — l'erogazione

* **La lettura per il form**: `GET …/contratti/<id>/righe/erogazioni/?articolo_id=` e
  `GET …/offerte/<id>/righe/erogazioni/?articolo_id=`, una base `RigaErogazioniView`
  (`apps/vendite/api/_riga_erogazioni_views.py`) e due sottoclassi; envelope dei lookup
  `{"results": [...]}`; il service legge **prima** la testata (404, non una lista vuota) e valida
  `articolo_id` UUID col campo. Il repository e' il BB `list_erogazioni_riga` dello stesso modulo
  della versione.
* **La copia Python della matrice**: ritirati `_FONTE_VIETATE_PER_TIPO_EROGAZIONE` e
  `_FONTE_DEFAULT_PER_TIPO_EROGAZIONE`. `_apply_fonte_quantita_logic` tiene la sola
  normalizzazione di `quantita` per fonte (§D.4, punto 2).
* **Il form** (`RigheEccezioniDrawer`, contratto e offerta, prop nuova `erogazioniArticolo`): legge
  le combinazioni quando l'articolo e' noto (scelta in «Aggiungi articolo», riga del listino in
  «Modifica prezzo», riga salvata in modifica); in creazione **preseleziona la combinazione di
  default** del DB; le tendine propongono solo cio' che il DB ammette, e il valore gia' scritto su
  una riga resta fra le opzioni (B-D6). Al cambio d'erogazione la fonte resta se ancora ammessa,
  diventa l'unica se e' una sola, altrimenti resta vuota e la sceglie l'operatore (§D.4, punto 1).
  Lista vuota → messaggio sotto l'articolo («non si vende su questo documento») e Salva spento.
  Il campo `fonte_quantita_attesa` si accende col canale `fields`. Ritirato il segnale «uso
  atipico» (`fonte_quantita_uso_atipico`): era un'invenzione della matrice FE, il DB non lo conosce.
  Aggiunta `tipo_erogazione_orario` (una riga ORARIO gia' scritta si legge).
* Le funzioni che mettono in forma le combinazioni stanno in `erogazioniRiga.js` (pure, con
  spec): `fontiQuantitaErogazione.js` e la sua spec sono **cancellati** (ok di Tid, 2026-10-07).
  `TIPO_EROGAZIONE` in `vendite/constants.js` resta (decisione di Tid, 2026-10-07): e' il
  vocabolario con cui `RigheEccezioniDrawer.spec.js` verifica che ogni erogazione che il DB puo'
  dichiarare abbia la sua etichetta, in it e in en.

### D.3 Test

* **Test Django sul DB** (§C.9.6): `test_righe_erogazione_obbligatoria_db` riscritto sulla regola
  nuova — la riga che nasce senza erogazione la **eredita** (si confronta col default che il DB
  dichiara, non con uno scritto a mano), il PATCH che la svuota resta rifiutato col campo; la riga
  di partenza prende la combinazione di default dell'articolo. `test_ricerca_liste_db`: la riga
  AGGIUNTA del fixture eredita (colonne vuote). Gli altri due file del §C.9.6 erano gia' verdi.
  `apps.vendite.tests.db` 161/161 con `ZEROERP_TEST_DB_E2E=1`.
* **Unitari**: emissione senza scrittura della versione; suite della fonte senza matrice ne' default;
  `tests/api/test_riga_erogazioni_api.py` nuovo (10 test, gli stessi sui due documenti). Provato per
  mutazione: togliendo la lettura della testata il test del 404 va rosso.
* **Suite BE completa** con i presidi su DB: 6256 test, verde.
* **FE**: `erogazioniRiga.spec.js` (6, provato per mutazione), vitest 733/733, `npm run guards`,
  eslint, build verdi.
* **Binding reale** delle due letture provato sul DB di sviluppo, come app sotto RLS col contesto
  operatore: versione operativa di un'offerta in BOZZA e di un contratto DRAFT, combinazioni di un
  articolo con tipologia, di un composito con tipologia e di un composito senza tipologia (natura).

### D.4 Al team DB (non bloccanti)

1. **L'ordine di `vendite.fn_documento_riga_erogazioni` non e' quello del trigger d'eredita'.** La
   lettura ordina `e_default DESC, tipo_erogazione, fonte_quantita_attesa`; il trigger, dentro
   un'erogazione, mette `DERIVATA_COMPONENTI` per ultima. Su un composito SERVIZI (dbdev,
   2026-10-07) l'erogazione CANONE viene letta come `DERIVATA_COMPONENTI` poi `FISSA`, mentre il
   trigger sceglierebbe `FISSA`. Per questo il form, al cambio d'erogazione, **non** preseleziona «la
   prima della lista» (sarebbe stata una copia della regola del trigger): lascia la scelta
   all'operatore quando le fonti sono piu' d'una. Se la lettura ordinasse come il trigger
   (`(fonte = 'DERIVATA_COMPONENTI')` dopo `e_default`), il form potrebbe proporre la prima fonte
   dell'erogazione e coincidere con il DB per costruzione. Una riga, a giudizio del team DB.
2. **La quantita' per fonte resta una regola del solo backend, e del solo contratto.**
   `_apply_fonte_quantita_logic` azzera `quantita`/`qta_operativa` sulle fonti a valle (MANUALE,
   TIMESHEET, LETTURE) e pretende una quantita' sulla FISSA; l'offerta non lo fa, e il DB non lo
   impone (`trgfn_qta_from_operativa` solleva solo sulla FISSA senza quantita'). Asimmetria
   preesistente, fuori dal perimetro del brief: va decisa la sede (un CHECK o il trigger della
   quantita'), e allora la copia Python si ritira. Dichiarata, non toccata.
3. **`_guard_listino_ha_versione_attiva`** (`contratti_service`, §4.4 del 2026-05-18): un listino
   senza **nessuna** versione ATTIVA non e' selezionabile sul contratto, controllo in Python. Con
   A-D2 l'attivazione pretende una versione **in vigore oggi**, controllata dal DB. Le due regole
   non sono la stessa (selezionabile ≠ attivabile), ma la prima e' una regola di dominio in Python
   accanto a una del DB: da valutare se resta, o se diventa una check del DB letta anche dal lookup
   dei listini. Non toccata.

### D.5 Collaudo a video (Tid)

* **Offerta nuova in BOZZA** su un listino con versione in vigore: «Emetti» **acceso**; l'emissione
  riesce e la testata mostra la versione congelata.
* Offerta su un listino **senza** versione in vigore oggi: «Emetti» spento col tooltip «Il listino
  non ha una versione in vigore oggi…».
* **Contratto DRAFT** con listino senza versione in vigore: «Attiva» spento col motivo.
* **Righe**, su un documento di una utility BASE: «Aggiungi articolo» con un articolo PRODOTTI/SERVIZI
  → erogazione e fonte preselezionate, nessuna «Da letture utility»; un articolo di una tipologia
  che la utility non prevede → il messaggio sotto l'articolo e Salva spento.
* «Modifica prezzo» su una riga del listino → la combinazione di default dell'articolo.
* Una riga salvata in modifica → erogazione e fonte com'erano; cambio d'erogazione → la fonte si
  adegua o si svuota.

## E. Secondo giro DB: le domande del §D.4 (`dev/db-tid`, 2026-10-07)

### E.1 Decisioni di Tid (2026-10-07)

| # | Domanda (§D.4) | Decisione |
| --- | --- | --- |
| **D.4.1** | L'ordine della lista non è quello dell'eredità | **L'ordine sta nel BB**: `vendite.fn_articolo_erogazioni` restituisce `ordine`, e l'eredità e la lista lo leggono. La regola d'ordine era scritta tre volte (due nel trigger, una nella lettura) |
| **D.4.2** | La quantità per fonte è una regola del solo BE, e del solo contratto | **Il DB, e rifiuta**: con una fonte a valle quantità e `qta_operativa` restano vuote, su contratto **e** offerta. Il BE smette di azzerare in silenzio |
| **D.4.3** | `_guard_listino_ha_versione_attiva` | **Si ritira**: la regola vera è «non si attiva senza una versione in vigore», e il DB la dice già (A-D2). In DRAFT un listino senza versione si sceglie, come sull'offerta. Il codice esce dal catalogo |

### E.2 ChangeSet

| ChangeSet | Oggetto | Cosa |
| --- | --- | --- |
| `00_schema/vendite/20261007-28` | `chk_contrighe_quantita_per_fonte`, `chk_offerte_eccezioni_quantita_per_fonte` | CHECK sulle due tabelle gemelle: solo FISSA e DERIVATA_COMPONENTI portano `quantita`/`qta_operativa`. È la rete. `preCondition` HALT se ci sono righe che il CHECK rifiuterebbe (§E.3) |
| `20_code/script/20261007-29` | `script.trgfn_righe_guard_quantita_per_fonte()` | Il guard che parla: `E_RIGA_QUANTITA_CON_FONTE_A_VALLE`, campo `qta_operativa` (o `quantita` se è la sola valorizzata). Stesso elenco del CHECK |
| `20_code/vendite/20261007-30` | 2 trigger `…_a10_guard_quantita_per_fonte_ins_upd` | BEFORE INSERT OR UPDATE, `WHEN tipo_eccezione <> 'ESCLUSIONE'`, **senza colonne sull'UPDATE**: la fonte la può riallineare un altro BEFORE (`default_erogazione_articolo`). Il nome lo mette dopo il perimetro: una fonte sbagliata la dice prima il perimetro |
| `20_code/vendite/20261007-66` | `vendite.fn_articolo_erogazioni` | **DROP + CREATE** (cambia `RETURNS TABLE`): colonna `ordine`, il rango della combinazione. Default in testa, poi per erogazione; dentro un'erogazione DERIVATA_COMPONENTI per ultima, poi la fonte |
| `20_code/script/20261007-67` | `script.trgfn_righe_default_erogazione_da_articolo` | Le cinque `ORDER BY` leggono `ae.ordine`. Stesso esito di prima |
| `20_code/vendite/20261007-68` | `vendite.fn_documento_riga_erogazioni` | `ORDER BY ae.ordine`. **Contratto invariato** (stesse colonne): cambia solo l'ordine |

⚠️ **Numerazione**: `-28 → -30` occupano il buco libero del giorno (`-28 … -39`): non dipendono
da niente di questo brief. `-66 → -68` stanno dopo `-60 → -65`, di cui sono revisioni. Il
`-66` deve precedere il `-67` (il corpo nuovo legge `ordine`).

**Codici** (CSV):

* `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` (**1210, nuovo**): DATO_ERRATO, frase chiusa.
* `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` (632): **ritirato**, `obsoleto_dal = 2026-10-07`
  in `codici_errore.csv`. La riga resta (`dbops.error_log` ci punta). Lo solleva solo il Python:
  dopo l'apply è il BE che deve smettere di usarlo (§E.5).

**La regola della quantità, sul modello.** La fonte dice da dove arriva la quantità che si
fattura. FISSA è la quantità della riga, ed era già obbligatoria e diversa da zero
(`E_QTA_MISSING`, `chk_*_qta_operativa_nonzero`). DERIVATA_COMPONENTI la scrive il DB dai
componenti. Con MANUALE, LETTURE e TIMESHEET arriva a valle, periodo per periodo. L'elenco è
quello delle fonti che **portano** la quantità: una fonte nuova del vocabolario nasce «a valle»
finché qualcuno non decide il contrario. Un pgTAP confronta l'elenco del CHECK con quello del
guard.

### E.3 ⚠️ Prima dell'apply, su dbdev

Il CHECK si convalida su tutte le righe, e la `preCondition` del `-28` ferma il migrate se ce ne
sono fuori regola. Non sono riuscito a contarle: come `zeroerp` non ho accesso allo schema
`vendite`, e come `zeroerp_app` la RLS le nasconde. Da lanciare come owner:

```sql
SELECT 'contratti_righe' AS tabella, id, fonte_quantita_attesa, quantita, qta_operativa
  FROM vendite.contratti_righe
 WHERE fonte_quantita_attesa NOT IN ('FISSA', 'DERIVATA_COMPONENTI')
   AND (quantita IS NOT NULL OR qta_operativa IS NOT NULL)
UNION ALL
SELECT 'offerte_commerciali_eccezioni', id, fonte_quantita_attesa, quantita, qta_operativa
  FROM vendite.offerte_commerciali_eccezioni
 WHERE fonte_quantita_attesa NOT IN ('FISSA', 'DERIVATA_COMPONENTI')
   AND (quantita IS NOT NULL OR qta_operativa IS NOT NULL);
```

Sul contratto il backend azzerava già: le candidate sono soprattutto righe d'offerta. La
correzione è un dato: svuotare `quantita` e `qta_operativa` di quelle righe. Sui documenti fuori
bozza scatta il lock `_a05_doc_righe_lock_fuori_bozza`, quindi o si correggono col trigger spento
per nome (la forma del `20261004-76`), o si cancellano, visto che sono dati di test.

### E.4 Prova (2026-10-07, prima dell'apply)

Su `zeroerp_ci`, come owner, in transazione annullata, con l'SQL **estratto** dagli YAML
(vincoli differiti, come Liquibase) e il seed del codice nuovo simulato:

* le `preCondition` estratte danno l'atteso (0, 0; la terza si prova dopo il `-29`);
* tutto compila, `plpgsql_check` non segnala niente sulle quattro funzioni (i due trigger
  provati su entrambe le tabelle); una firma sola per funzione;
* rollback: i tre corpi tornano identici al vivo (md5), il guard nuovo sparisce;
* **regressione su 87 pgTAP**, ciascuno prima e dopo (le due tabelle, le funzioni toccate, i
  codici, i presidi trasversali): dopo le correzioni qui sotto si muovono solo il test nuovo e
  `test-righe-erogazione-da-articolo-v1`, rossi senza i changeSet e verdi con. Fermi
  `riferimenti-morti` (9/9), `rubinetto-primo-motivo` (7/7, nessun sito nuovo dell'helper),
  `catalogo-messaggi-errore-completo` (7/7), `codici-errore-obsoleto-dal` (4/4).

**pgTAP**:

* **Nuovo** `vendite/test-righe-quantita-per-fonte-v1` (12): rifiuto col campo
  `qta_operativa` o `quantita`, fonte a valle senza quantità ammessa, FISSA e DERIVATA ammesse,
  l'offerta, l'UPDATE in cui la fonte la cambia un altro trigger, il perimetro che parla prima,
  CHECK e guard con lo stesso elenco, la forma del trigger, il codice a catalogo (rosso prima
  dell'apply: il CSV si carica in `80_data`).
* `vendite/test-righe-erogazione-da-articolo-v1`: 20 → 22. Il 21 e il 22 provano l'ordine (il
  caso del §D.4: un composito, CONSUMO, MANUALE prima di DERIVATA) e che la prima fonte proposta
  dal form sia quella che il DB eredita. Le righe che nascono MANUALE ora nascono senza quantità.
* **Fixture adattati**, perché scrivevano una quantità su righe che ereditano una fonte a valle
  (la tipologia del listino del builder ha come default CONSUMO/LETTURE). La quantità era sempre
  incidentale al soggetto del test, e ora si chiede alla sede unica (1 se la fonte di default è
  FISSA, altrimenti vuota): `test-contratti-righe-coerenza-fonte-erogazione` (13, 15),
  `test-contratto-esclusione-non-modificabile-v1` (helper e test 13: il prezzo, non la
  quantità), `test-contratto-righe-lista-v1`, `test-contratto-righe-lista-uom-riga-v1` (B),
  `test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1`, `test-righe-erogazione-obbligatoria-v1`,
  `test-righe-esclusione-solo-non-si-vende-v1`.
* **Corretti con lettura statica**, perché prendono gli articoli dai dati di dbdev e su
  `zeroerp_ci` non costruiscono il fixture (§C.6.5): `test-fn-contratto-righe-preview-nuovi-campi-v1`
  (le due AGGIUNTE MANUALE nascono senza quantità; i test 7-8 leggono la fonte) e
  `test-fn-resolve-prezzo-listino-v2-v1` (l'OVERRIDE eredita: quantità solo se FISSA). **Sono i
  due da guardare per primi nella corsa su dbdev.**
* Censimento statico degli altri: ogni INSERT che scrive una quantità con erogazione UNA_TANTUM o
  CANONE e fonte vuota eredita FISSA per costruzione (il seed non ammette altra fonte di default
  per quelle erogazioni); `step24` lascia vuota anche l'erogazione, ma sceglie articoli senza
  tipologia che ammettono UNA_TANTUM/FISSA, e quelle nature hanno proprio quel default. Quindi
  `step22`, `step23`, `step24`, `overlap-draft`, `guard-pending`, `bozza-non-operativa`,
  `lock-fuori-bozza` e i test delle offerte non si muovono.

⚠️ Non provati: l'apply vero (loader del CSV, `preCondition` su dbdev), la corsa come app e i
fixture presi dai dati di dbdev.

### E.5 Richieste al BE/FE (l'apply è fatto: §E.6)

* **BE, D.4.2**: ritirare la parte di `_apply_fonte_quantita_logic` che azzera
  `quantita`/`qta_operativa` sulle fonti a valle (e `_FONTI_QUANTITA_DOWNSTREAM`): ora il DB
  rifiuta, col campo. Il ramo FISSA («quantità diversa da zero») è già del DB (`E_QTA_MISSING`,
  `chk_*_qta_operativa_nonzero`): si ritira anche quello, e con lui il metodo. Policy del codice
  1210 (ripiego senza `%s`, canale COLUMN).
* **FE, D.4.2**: il form delle righe non manda la quantità quando la fonte scelta è a valle, e
  al cambio di fonte (o d'erogazione, se la fonte si riallinea) la svuota.
* **FE, D.4.1**: al cambio d'erogazione il form può proporre la **prima fonte** di
  quell'erogazione nella lista di `…/righe/erogazioni/`: coincide con quella che il DB eredita
  per costruzione.
* **BE, D.4.3**: ritirare `_guard_listino_ha_versione_attiva` (`contratti_service`, create e
  update), `ListiniRepository.has_versione_attiva` se non ha altri lettori, e il filtro «almeno
  una versione ATTIVA» del lookup `lookup/listini-selezionabili-contratto/` (o il lookup intero,
  se torna uguale a quello generico dei listini). Togliere `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA`
  dal ripiego e dalle policy (la rigenerazione lo marca «RITIRATO»). Commento in
  `ContrattoDrawer.vue` (riga 180) da aggiornare.
* **BE, test Django sul DB** che scrivono una quantità su righe che ereditano una fonte a valle
  (rossi attesi dopo l'apply, lato BE): da guardare `test_righe_erogazione_obbligatoria_db`,
  `test_ricerca_liste_db`, `test_scritture_dinamiche_vendite_db`. Stessa ricetta dei pgTAP:
  quantità solo se la fonte di default è FISSA.
* Doc: `api_contratti.md` e `api_offerte.md` (righe: quantità per fonte; codice 1210),
  `modello-contratti.md`. La guida `gestione-contratti.md` è già aggiornata (§2.2 e tabella dei
  codici).

### E.6 Chiusura del secondo giro DB (2026-10-08)

**Applicati da Tid, pgTAP verdi su dbdev**: `20261007-28 → -30` e `-66 → -68`, letti dal
`databasechangelog` (EXECUTED il 2026-10-08), più i CSV (codice 1210 nuovo, 632 ritirato). La
`preCondition` del `-28` è passata: su dbdev, al momento dell'apply, nessuna riga violava il CHECK.

| Domanda | Esito |
| --- | --- |
| D.4.1 l'ordine della lista e quello dell'eredità | ✅ `ordine` in `vendite.fn_articolo_erogazioni`, letto da trigger e lettura per il form |
| D.4.2 la quantità per fonte | ✅ `chk_*_quantita_per_fonte` (la rete) + `script.trgfn_righe_guard_quantita_per_fonte` (`E_RIGA_QUANTITA_CON_FONTE_A_VALLE`, col campo), su contratto e offerta |
| D.4.3 il listino senza versione ATTIVA | ✅ lato DB: codice ritirato (`obsoleto_dal`); ⏳ il BE ritira il guard Python e il filtro del lookup |

**Cosa resta, tutto fuori dal DB**: le richieste del §E.5 (BE: `_apply_fonte_quantita_logic`,
`_guard_listino_ha_versione_attiva`, lookup dei listini, policy del 1210, i tre test Django sul
DB; FE: niente quantità con una fonte a valle, la prima fonte dell'erogazione preselezionata;
doc `api_contratti.md`, `api_offerte.md`, `modello-contratti.md`), il collaudo a video del §D.5
e l'archiviazione del brief in `work-done/`.


## F. Terzo giro DB: ciò che il secondo giro BE/FE non può chiudere (`dev/backend-tid`, 2026-10-08)

> **Chi scrive:** sessione BE/FE, dopo l'analisi completa del §E.5. **A chi:** team DB.
> **Decisioni:** di Tid, 2026-10-08: F-1 come proposto; F-2 con utility **ed** emittente.
> Il resto del §E.5 il BE/FE lo fa senza aspettare (§F.3). Le due voci sono indipendenti.

### F.1 La quantità calcolata segue la fonte (D.4.2)

**Il difetto.** Una riga ha due quantità: `qta_operativa`, che scrive l'operatore, e `quantita`,
che il DB calcola dalla prima (`script.trgfn_qta_from_operativa`). Quando la riga passa a una fonte a
valle (MANUALE, LETTURE, TIMESHEET) vanno vuote tutte e due. Il form manda `qta_operativa = NULL`
(non manda mai `quantita`), ma `trgfn_qta_from_operativa`, con `qta_operativa` NULL e fonte ≠ FISSA,
esce senza toccare `quantita`. Il guard `trgfn_righe_guard_quantita_per_fonte` trova la `quantita`
rimasta e rifiuta `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` sul campo `quantita`, che il form non ha.

* Sul **contratto** oggi non si vede: `_apply_fonte_quantita_logic` (BE) svuota ancora `quantita`, ed
  è la copia che il §E.5 chiede di ritirare. Ritirata, il difetto compare.
* Sull'**offerta** si vede già (dedotto dal codice e dal pgTAP 9 di
  `test-righe-quantita-per-fonte-v1`, che svuota le due colonne a mano; non provato a video): il BE
  dell'offerta non ha mai svuotato niente, quindi FISSA → MANUALE sul drawer va in errore dal
  2026-10-08.
* Stesso caso, più nascosto: DERIVATA_COMPONENTI → fonte a valle. `qta_operativa` era già NULL,
  `trgfn_qta_from_operativa` esce al corto circuito, `quantita` (scritta dai componenti) resta.

**Decisione (Tid, F-1).** `quantita` è una colonna **calcolata**: la scrive solo il DB. Con una fonte
a valle è vuota per costruzione, e la svuota il DB; il rifiuto resta sull'**input**.

| # | Richiesta |
| --- | --- |
| F-1.1 | Su contratto e offerta, con una fonte a valle, il DB porta `quantita` a NULL (all'INSERT e a ogni UPDATE che cambia fonte o quantità). La forma (in `trgfn_qta_from_operativa` col suo argomento di fonte, o in un trigger a sé) la sceglie il team DB. ⚠️ Vale anche quando `qta_operativa` è già NULL (il caso DERIVATA → MANUALE): oggi lì il trigger esce prima |
| F-1.2 | `trgfn_righe_guard_quantita_per_fonte` rifiuta solo `qta_operativa` valorizzata (campo `qta_operativa`). `quantita` non è più materia del rifiuto: non la scrive nessun client. Il CHECK `chk_*_quantita_per_fonte` resta la rete, invariato |
| F-1.3 | L'elenco «fonti che portano la quantità» resta uno: quello del guard e del CHECK. Se F-1.1 ne fa una terza lettura, meglio farlo diventare un dato (per esempio una colonna su un vocabolario delle fonti) che le tre sedi leggono |
| F-1.4 | pgTAP: FISSA → MANUALE mandando la sola `qta_operativa = NULL` passa e lascia `quantita` NULL; DERIVATA_COMPONENTI → MANUALE senza toccare quantità passa; MANUALE con `qta_operativa` valorizzata rifiutato col campo `qta_operativa`; le stesse prove sull'offerta |

**Ricadute BE/FE a consegna fatta:** il BE ritira `_apply_fonte_quantita_logic` e
`_FONTI_QUANTITA_DOWNSTREAM` (§E.5) e valuta di togliere `quantita` dalle chiavi ammesse del payload di
riga (contratto e offerta), visto che è calcolata. Il FE non cambia: manda già `qta_operativa = NULL`
fuori dalla FISSA.

### F.2 Il listino di un documento è della sua utility e del suo emittente

**Il difetto (trovato nell'analisi del D.4.3).** Nessuna sede impedisce a un contratto o a
un'offerta di riferirsi a un listino di un'altra utility o di un altro emittente:

* a DB, su `vendite.contratti` e `vendite.offerte_commerciali` per `listino_id` c'è solo il
  `require_attivo` (letto dall'elenco dei trigger nella doc auto-generata);
* nel BE nessun controllo (`contratti_service`, `offerte_service`);
* la RLS di `vendite.listini` filtra sugli emittenti **dell'operatore**, non su quello del documento
  (un operatore con più emittenti, o il SUPER_ADMIN su «Tutti», li vede tutti).

Oggi lo nasconde in parte il lookup `lookup/listini-selezionabili-contratto/` (SQL in Python, usato
anche dall'**offerta**: la frase del §E.1 «come sull'offerta» non è esatta), che propone i soli
listini con una versione ATTIVA. Con il D.4.3 quel filtro si ritira, e la tendina proporrebbe ogni
listino attivo, di ogni utility. Un listino di un'altra utility porta righe che il perimetro poi
rifiuta (`E_RIGA_TIPOLOGIA_FUORI_UTILITY`) o, peggio, prezzi di un altro emittente.

**Decisione (Tid, F-2):** il listino di un documento ha la **stessa utility e lo stesso emittente**
del documento.

| # | Richiesta |
| --- | --- |
| F-2.1 | Una check pura sui valori (§12.5.1 delle linee guida), sede unica del predicato: listino, utility ed emittente del documento → i motivi (utility diversa; emittente diverso). ⚠️ Il documento porta `emittente_fiscale_id` (PK), il listino `emittente_soggetto_ruolo_id`: la traduzione sta nella check |
| F-2.2 | Un guard su `vendite.contratti` e `vendite.offerte_commerciali` che la chiama all'INSERT e quando cambiano listino, utility o emittente, col campo `listino_id`. Codici nuovi (DATO_ERRATO, frase chiusa) |
| F-2.3 | **La lettura per il form**: i listini sceglibili per un documento (utility, emittente), dalla stessa check, nella forma `{id, codice, descrizione}`. Prende il posto dell'SQL di `ListiniRepository.list_lookup_selezionabili_contratti`, che col D.4.3 perde il filtro sulla versione ATTIVA. ⚠️ In creazione il documento non esiste: la lettura prende i **valori** (utility, emittente), non l'id |
| F-2.4 | Le righe già scritte: proposta come B-D6, i documenti esistenti restano come sono (dati di test); il guard scatta solo sui cambi. Se il team DB preferisce una `preCondition` che li conti, la scrive lui |
| F-2.5 | pgTAP: listino della stessa utility ed emittente ammesso; utility diversa e emittente diverso rifiutati col campo; la lettura che propone solo i primi; il push offerta → contratto che porta un listino coerente per costruzione |

**Ricadute BE/FE a consegna fatta:** il lookup dei listini (contratto **e** offerta) espone la
lettura F-2.3 con utility ed emittente del form; si ritira `list_lookup_selezionabili_contratti`;
le policy dei codici nuovi.

### F.3 Il secondo giro BE/FE senza aspettare (§E.5)

Fatto il 2026-10-08 su `dev/backend-tid`, salvo dove scritto: ritiro di
`_guard_listino_ha_versione_attiva` e `ListiniRepository.has_versione_attiva` (D.4.3; il lookup
aspetta F-2.3); policy rigenerate (1210 nuovo, 632 ritirato) e ripiego del 1210; D.4.1 nel form (la
prima fonte dell'erogazione); il fixture di `test_ricerca_liste_db` (quantità solo se la fonte di
default è FISSA). Restano dopo il terzo giro DB: il ritiro di `_apply_fonte_quantita_logic` (F-1),
il lookup dei listini (F-2), la doc e il collaudo a video.

### F.4 Consegna del terzo giro DB (`dev/db-tid`, 2026-10-08)

> Numerazione da `20261008-10` (il `-01` è di un altro cantiere). **✅ Applicato da Tid** su
> `zeroerp_ci` (16:33) e su dbdev; pgTAP verdi su dbdev il 2026-10-08, dopo le due correzioni di
> fixture in coda al §F.4.6.

#### F.4.1 ChangeSet

| ChangeSet | Oggetto | Cosa |
| --- | --- | --- |
| `20_code/script/20261008-10` | `script.fn_fonte_porta_quantita(fonte)` (nuova) | **l'elenco delle fonti che portano la quantità** (FISSA, DERIVATA_COMPONENTI), `LANGUAGE sql IMMUTABLE`, parametro `%TYPE` (F-1.3) |
| `20_code/script/20261008-11` | `script.trgfn_righe_guard_quantita_per_fonte` | rifiuta **solo** `qta_operativa` (campo `qta_operativa`); l'elenco lo legge da `-10`; il contesto perde `colonne` (F-1.2) |
| `20_code/script/20261008-12` | `script.trgfn_qta_from_operativa` | con una fonte a valle `quantita := NULL` a **ogni** INSERT e UPDATE, prima del short-circuit (il caso DERIVATA → MANUALE); `DECLARE` ancorati `%TYPE` (F-1.1) |
| `20_code/script/20261008-13` | `script.fn_check_listino_documento(listino, utility, emittente_fiscale_id)` (nuova) | check pura sui valori, due motivi col campo `listino_id`: `LISTINO_UTILITY_DIVERSA`, `LISTINO_EMITTENTE_DIVERSO`. La traduzione PK → `soggetto_ruolo_id` sta qui (F-2.1) |
| `20_code/script/20261008-14` | `script.trgfn_doc_guard_listino_documento()` (nuova) | solleva il primo motivo con `fn_raise_primo_motivo_se_presente`, una funzione per le due testate (F-2.2) |
| `20_code/vendite/20261008-15` | 4 trigger su `vendite.contratti` e `vendite.offerte_commerciali` | `…_a10_guard_listino_documento_ins` (ogni INSERT, anche push e revisione) e `…_upd` (`WHEN` cambiano listino, utility o emittente: F-2.4). Dopo `a10_default_emittente` e `a10_guard_emittente_ba` |
| `20_code/vendite/20261008-16` | `vendite.fn_listini_selezionabili(utility, emittente_fiscale_id)` (nuova) | la lettura per il form, `{id, codice, descrizione}` ordinata per descrizione e id: i listini attivi senza motivi della **stessa** check. Utility o emittente NULL: nessuno (F-2.3) |

**Codici** (CSV): `E_DOC_LISTINO_UTILITY_DIVERSA` (**1222**) ed `E_DOC_LISTINO_EMITTENTE_DIVERSO`
(**1223**), DATO_ERRATO, frase chiusa. Gli id 1211-1221 li ha già presi il cantiere dei codici
email e permessi, non ancora committato. La nota di `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` (1210) è
riscritta: il campo è sempre `qta_operativa`.

#### F.4.2 Le scelte, e perché

* **F-1.3, l'elenco come funzione e non come dato.** Un CHECK non legge tabelle: con una colonna su
  un vocabolario delle fonti, la rete avrebbe tenuto comunque un elenco suo, e il dato avrebbe tolto
  una copia per aggiungerne un'altra. Un vocabolario delle sole fonti oggi non c'è
  (`config.erogazioni_fonti` è per coppia). Il CHECK resta invariato, come chiede F-1.2. Il pgTAP
  confronta i suoi letterali con le fonti del vocabolario per cui la funzione dice `true`, e
  verifica che guard e calcolo la **chiamino**.
* **F-1.1 in `trgfn_qta_from_operativa`.** È l'unico scrittore di `quantita`, e conosceva già la
  colonna della fonte. Le altre quattro tabelle (preventivi, ordini, DDT, resi) non passano
  l'argomento della fonte, quindi per loro non cambia niente. L'ordine regge per nome: il guard
  (`a10_guard_q…`) gira prima del calcolo (`a10_qta…`), quindi giudica l'input e lascia al calcolo
  lo svuotamento; il CHECK vede la riga finale.
* **I componenti del kit.** Quando il DB svuota la quantità del padre, `z90_propaga_qta_componenti`
  riscrive i figli. `trgfn_componenti_calcola_quantita` usa `COALESCE(qta_padre, 1)`, quindi il
  `NOT NULL` di `*_componenti.quantita` regge. Era già il percorso del BE che azzerava.
* **F-2, il listino che non si legge.** Sotto RLS un listino di un emittente fuori dal perimetro di
  chi agisce non si legge. Il documento invece sta nel perimetro (guard `emittente_scope`), quindi
  quel listino è di un altro emittente: motivo `LISTINO_EMITTENTE_DIVERSO`, senza dire altro. Da
  owner si legge, e il motivo è lo stesso.
* **F-2.3, `attivo`.** La lettura propone solo listini attivi: un listino spento lo rifiuta il
  `require_attivo` del framework. Non filtra sulla versione (D.4.3).
* **F-2.4.** Nessuna `preCondition` che conti i documenti incoerenti già scritti: il guard scatta
  solo all'INSERT e sui cambi, come B-D6.

#### F.4.3 Trovati scrivendo, non toccati (da decidere)

* **DERIVATA_COMPONENTI: chi scrive la quantità del padre?** Il commento del CHECK
  `chk_*_quantita_per_fonte`, il manuale di `contratti_righe` e la nota del 1210 dicono «la scrive
  il DB dai componenti (`z90_propaga_qta_componenti`)». **È falso**: quel trigger propaga dal padre
  **ai** figli. Su una riga DERIVATA nessuno calcola `quantita`: resta quella che il client manda,
  oppure quella rimasta da una FISSA (FISSA → DERIVATA con `qta_operativa = NULL`). La decisione F-1
  («`quantita` la scrive solo il DB») su DERIVATA oggi non vale. Domanda per Tid: la riga DERIVATA
  deve portare una quantità (e allora chi la calcola), o è «a valle» anche lei? Nel secondo caso
  basta toglierla da `fn_fonte_porta_quantita` e dai due CHECK.
* **FISSA, `quantita` scritta a mano.** Un UPDATE che scrive la sola `quantita` su una riga FISSA
  passa dal short-circuit e resta. È la migliorìa 2 del manuale di `trgfn_qta_from_operativa`,
  aperta da prima; tocca anche le altre quattro tabelle. Non chiesta.
* **Ordine fra il guard del listino e il lock del contratto attivo.** Su un contratto ATTIVO un
  cambio di listino incoerente risponde «listino di un'altra utility/azienda» prima di «campi
  bloccati» (`a10_guard_listino…` < `a10_lock_post_attivazione`). L'operatore corregge il listino
  e poi trova il lock. Se conta, il lock va in `_a05_` (linee-guida-trigger), cantiere a sé.
  ➡️ **Passato** (2026-10-10) a [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md)
  §5: quel giro rimonta il lock del contratto nella forma per stato, e lì se ne sceglie il posto.

#### F.4.4 pgTAP e prova (2026-10-08, prima dell'apply)

* **Nuovo** `vendite/test-doc-listino-documento-v1` (12, tutto costruito: due aziende con
  `fn_pgtap_crea_emittente_operatore`, tre listini). Copre la check sui valori, i rifiuti col campo
  su offerta e contratto, l'UPDATE del listino, la `WHEN` (un altro campo non giudica), la lettura
  per il form, il push offerta → contratto, la forma dei trigger, i codici a catalogo.
* **Aggiornato** `vendite/test-righe-quantita-per-fonte-v1` (12 → 15): il 2 ora è «la sola
  `quantita` con una fonte a valle passa e la svuota il DB»; il 9 manda la sola
  `qta_operativa = NULL`, come il form (F-1.4); il 10 confronta i CHECK con
  `fn_fonte_porta_quantita` e pretende che guard e calcolo la chiamino; nuovi 13 (DERIVATA →
  MANUALE), 14 (l'offerta), 15 (rifiuto sull'input all'UPDATE).
* `script/test-rubinetto-primo-motivo-v1` test 5: da 34 a 35 (il guard del listino è un sito nuovo
  dell'helper). ⚠️ Se il cantiere del `20261008-01` aggiunge anche lui un sito, i due numeri vanno
  sommati al merge.

**Prova** su `zeroerp_ci`, come owner, in transazione annullata con l'SQL **estratto** dai sette
YAML:

* compila tutto; `plpgsql_check` sulle funzioni toccate dà solo l'avviso già esistente
  `v_max_dec` mai letto; una firma sola per funzione (i `%TYPE` non creano overload);
* i corpi vivi sullo scratch coincidono con quelli dei rollback (md5 / diff);
* cancelli statici della CI verdi (letterali, `runOnChange`, preCondition/seed, trigger
  d'automazione, timestamp, GRANT batch);
* **regressione su 61 pgTAP**, prima e dopo: si muovono solo i tre file del giro, rossi senza i
  changeSet e verdi con (il 12 del file nuovo legge il catalogo: verde solo dopo l'apply del CSV).
  ⚠️ **Cieca sui fixture presi dai dati** (lezione del §C.6.5): 25 file muoiono sullo scratch
  identici prima e dopo, perché scelgono listino e cliente fra i dati della macchina. Sono quelli
  che il guard F-2 colpisce su dbdev se il primo listino per id non è della utility e
  dell'emittente del primo BA: censiti e corretti al §F.4.6.

⚠️ Non provati: l'apply vero (loader del CSV), la corsa come app (il ramo «listino che non si
legge» lo vede solo l'app; da owner il motivo è lo stesso).

#### F.4.5 Richieste al BE/FE, a apply fatto

* **BE, F-1**: ritirare `_apply_fonte_quantita_logic` e `_FONTI_QUANTITA_DOWNSTREAM` (§E.5).
  Valutare di togliere `quantita` dalle chiavi ammesse del payload di riga (contratto e offerta):
  è calcolata, e il DB la svuota comunque con una fonte a valle. Il contesto di
  `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` non porta più `colonne`, e il campo è sempre `qta_operativa`.
* **BE, F-2**: il lookup dei listini di contratto **e** offerta legge
  `SELECT id, codice, descrizione FROM vendite.fn_listini_selezionabili(%s, %s)` con utility ed
  emittente del form; si ritira `ListiniRepository.list_lookup_selezionabili_contratti`. Policy dei
  codici 1222 e 1223 (DATO_ERRATO, campo `listino_id` nel canale COLUMN, ripieghi senza `%s`):
  finché mancano, il guardrail dei codici del DB senza policy è rosso, per il lato BE.
* **FE**: il form manda utility ed emittente al lookup (cambiano la tendina); niente da cambiare per
  F-1 (manda già `qta_operativa = NULL` fuori dalla FISSA).
* Test Django sul DB: `test_ricerca_liste_db` e `test_righe_erogazione_obbligatoria_db` costruiscono
  listino e cliente coi builder, quindi sono coerenti per costruzione.

#### F.4.6 I 25 pgTAP che pescavano listino e cliente dai dati (2026-10-08)

Censiti da tre letture statiche in parallelo (43 file che scrivono testate con un listino): **18
coerenti per costruzione** (builder, o listino NULL), **25 presi dai dati** («primo BA», «primo
emittente», «primo listino per id», «prima versione ATTIVA di un listino qualsiasi»), nessuno
rotto per costruzione e nessuno che volesse un documento incoerente. Tutti gli INSERT presi dai dati
stavano nel **fixture**: su dbdev il guard F-2 avrebbe fatto morire il file. Correzioni, autorizzate
da Tid:

| Forma | File |
| --- | --- |
| **Costruiti** (cliente `fn_pgtap_crea_cliente_ba` dopo il contesto, legato dal z90 a chi agisce; listino `fn_pgtap_crea_listino` sulla stessa utility; emittente dell'operatore; versione del builder) | offerte: `codice-lock`, `rientro-padre-revisione-annullata`, `revisione-guard-config`, `lista-superata-vs-abortito`, `crea_revisione_offerta`, `push_offerta_a_contratto`, `push_offerta_successione`, `commerciali_codice`, `end_to_end`, `revisione_trigger`, `state_machine` (slot B: la versione CHIUSA si costruisce chiudendo quella del listino scaduto), `eccezioni_guard_pending`, `eccezioni_qta_from_operativa` (utility che ammette la tipologia dell'articolo f6), `push_offerta_fissa_qta_operativa`; contratti: `schema-step21`, `step23` |
| **Cliente costruito, listino copiato** sulla sua utility e col suo emittente | `bozza-non-operativa-e-preview-contratto`, `fn-contratto-righe-preview-nuovi-campi`, `guard-esclusione-figlio-bundle` (cliente sulla utility del listino del bundle, bundle dell'emittente di chi agisce) |
| **Filtrati** (articoli, prezzi o emittente A dei dati sono il soggetto): listino della utility e dell'emittente del BA, versione di QUEL listino | `schema-step22`, `resolve-prezzo-listino-v2` e `…-classe-da-contratto` (emittente dal BA anche per la matrice, e il BA scelto solo se il listino coerente esiste), `eccezioni_componenti` (salta senza listino), `vw-dash-backlog`, `vw-dash-fatturazione` |

⚠️ `step23` test 7 aggiorna il listino di un contratto ATTIVO per provare il lock: ora usa il listino
coerente del fixture. Con uno qualunque dei dati lo avrebbe rifiutato prima il guard del listino
(stesso `P0001`, e `throws_ok` col messaggio NULL): verde per il motivo sbagliato. Restano
`throws_ok(..., NULL)` anche in `revisione-guard-config` (3-4) e in `push_offerta_successione`:
non distinguono il codice. Non toccati, da stringere se servirà.

**Esito su `zeroerp_ci`, col giro applicato da Tid** (come owner):

* **15 file passano da morti nel fixture (o rossi) a verdi pieni**: i 14 qui sopra che stanno in
  `baseline-rossi-ci.tsv` / `baseline-rossi-scratch.tsv` come `ERRORE_FIXTURE` o `ASSERZIONE`
  (`codice-lock`, `rientro-padre`, `revisione-guard-config`, `lista-superata`, `crea_revisione`,
  `push_a_contratto`, `push_successione`, `commerciali_codice`, `end_to_end`, `revisione_trigger`,
  `state_machine`, `qta_from_operativa`, `push_fissa`, `step23`) più il test nuovo. ⏳ Escono dai
  registri dopo la corsa di Tid come app.
* I sei filtrati restano rossi sullo scratch **come prima**: lì i dati che filtrano non ci sono. Su
  dbdev il filtro li tiene coerenti; se un giorno svuotasse i candidati lo dice la loro
  precondizione, non un errore nel fixture.
* Regressione larga (61 file) sullo stato applicato contro la prova pre-apply: **nessun altro file
  si muove**.
* Una regressione mia trovata e corretta nel giro: `eccezioni_componenti`, senza BA nei dati,
  chiamava `fn_get_emittente_fiscale_pk(NULL)` e moriva (era 27/27 in skip): ora l'aggiornamento
  dell'emittente salta senza BA, e torna 27/27.

**Corsa di Tid su dbdev (2026-10-08, sera): tre regressioni, mie.** Erano tre dei file
**filtrati**: su dbdev il filtro non trovava un listino della utility e dell'emittente del BA.
`classe-da-contratto` restava senza candidati (resolver coi parametri NULL), e i due cruscotti
scrivevano l'offerta con il listino NULL. ⚠️ La lezione: un filtro sui dati scambia «la fixture
è coerente» con «la fixture c'è», e la prova sullo scratch, senza dati, non vede la differenza.
Corretti costruendo il listino invece di cercarlo:

* `resolve-prezzo-listino-v2-classe-da-contratto` (runner app): il listino si scrive con la
  tipologia dell'articolo, la utility e l'emittente del BA (che sotto RLS è nel perimetro di chi
  agisce). Il BA si sceglie solo se la sua utility ammette quella tipologia;
* `vw-dash-backlog` (runner app): `fn_pgtap_crea_listino` sulla utility del BA, **dopo** il
  passaggio all'operatore whitelistato su A, quindi con l'emittente A;
* `vw-dash-fatturazione` (runner owner): le offerte nascono prima del passaggio d'operatore, quindi
  listino e versione si scrivono a mano con A e con la utility del BA, in due istruzioni (i trigger
  della versione rileggono il listino).

Sullo scratch i tre danno gli stessi conteggi della baseline (mancano i dati che scelgono). Il
verdetto è la prossima corsa su dbdev. Gli altri tre filtrati (`schema-step22`,
`resolve-prezzo-listino-v2`, `eccezioni_componenti`) non sono fra le regressioni della corsa.

**Seconda corsa di Tid (stessa sera): `classe-da-contratto` ancora rosso**, precondizione 1 a 0
candidati. Il secondo criterio («un articolo dei dati con una tipologia che la utility del BA
ammette») su dbdev non trova niente insieme a un cliente con dimensione. L'articolo non è il
soggetto del test: lo è la classe letta dal contratto. Ora il cliente si sceglie come in origine
(dimensione e categoria) più «la sua utility ammette almeno una tipologia di listino»; articolo e
listino si costruiscono con la prima tipologia ammessa. Letto su dbdev come app col contesto del
runner, in sola lettura, solo per escludere un altro insieme vuoto: candidati presenti in tutti e
due i blocchi (con e senza dimensione). Stessa lettura per `vw-dash-backlog`: la utility del primo
cliente ammette una tipologia, quindi il builder del listino non si ferma.

#### F.4.7 Chiusura del terzo giro DB (2026-10-08)

**Applicato da Tid su dbdev, pgTAP verdi.**

| Richiesta | Esito |
| --- | --- |
| F-1.1 con una fonte a valle il DB porta `quantita` a NULL | ✅ `trgfn_qta_from_operativa`, a ogni INSERT e UPDATE (anche DERIVATA → MANUALE) |
| F-1.2 il rifiuto sulla sola `qta_operativa` | ✅ `trgfn_righe_guard_quantita_per_fonte`; i CHECK invariati |
| F-1.3 l'elenco delle fonti in un posto | ✅ `script.fn_fonte_porta_quantita`, letto da guard e calcolo; il pgTAP confronta i CHECK |
| F-1.4 pgTAP | ✅ `test-righe-quantita-per-fonte-v1` (15) |
| F-2.1 check pura sui valori | ✅ `script.fn_check_listino_documento` |
| F-2.2 il guard su contratto e offerta | ✅ `script.trgfn_doc_guard_listino_documento`, 4 trigger, codici 1222-1223 |
| F-2.3 la lettura per il form | ✅ `vendite.fn_listini_selezionabili(utility, emittente_fiscale_id)` |
| F-2.4 le righe già scritte | ✅ nessuna bonifica: il guard scatta all'INSERT e sui cambi |
| F-2.5 pgTAP | ✅ `test-doc-listino-documento-v1` (12) |

**Cosa resta**: il giro BE/FE del §F.4.5 (ritiro di `_apply_fonte_quantita_logic`, lookup dei
listini su `vendite.fn_listini_selezionabili`, policy dei codici 1222-1223); i tre trovati del
§F.4.3, da decidere; l'uscita dei 14 file dai registri dei rossi di CI dopo la corsa come app; il
collaudo a video e l'archiviazione.

## G. Terzo giro BE/FE (`dev/backend-tid`, 2026-10-08)

> Esegue il §F.4.5 (e con lui il resto del §E.5). Committato (`67a0cac2e`, in `Tito-dev`).

### G.1 F-1, la quantità

* **Ritirati** `ContrattiService._apply_fonte_quantita_logic` e `_FONTI_QUANTITA_DOWNSTREAM`: il
  service trasporta `quantita`/`qta_operativa` come arrivano. Con una fonte a valle il DB svuota
  `quantita` e rifiuta `qta_operativa` col campo (1210); la FISSA senza quantità la rifiuta il DB
  (`E_QTA_MISSING`). Il ramo FISSA del metodo era un 400 `E_VENDITE_VALIDATION` nostro: non c'è più.
* La suite `ContrattiServiceFonteQuantitaTests` è riscritta sul verso nuovo: con una fonte a valle
  la `qta_operativa` arriva al DB com'è (nessuno svuota in silenzio), la FISSA senza quantità non è
  un rifiuto Python, la coppia non la giudica il service.
* **`quantita` resta fra le chiavi ammesse del payload di riga** (decisione di Tid, 2026-10-08):
  si toglie quando è deciso il primo trovato del §F.4.3. Su DERIVATA_COMPONENTI oggi nessuno la
  calcola, quindi toglierla prima lascerebbe quelle righe senza quantità.
* FE: niente da cambiare (manda già `qta_operativa = null` fuori dalla FISSA, §F.4.5).

### G.2 F-2, il listino del documento

* **BE**: il lookup è `GET /vendite/lookup/listini-selezionabili/?utility_id=&emittente_fiscale_id=`
  (`ApiListiniSelezionabiliLookup`), che legge `vendite.fn_listini_selezionabili` dal BB
  `ListiniRepository.list_lookup_selezionabili`. Ritirati `list_lookup_selezionabili_contratti`,
  `fn_list_listini_selezionabili_contratti` e la rotta `listini-selezionabili-contratto/` (il nome
  diceva «contratto» e la serviva anche l'offerta). ⭐ Envelope dei lookup `{"results": [...]}`: la
  vecchia rotta tornava la lista nuda, e i due drawer passavano il transform a mano (api.md
  §«L'ENVELOPE DI UN LOOKUP»). Parametri `qp_int_optional`: assenti → nessun listino (lo dice il
  DB), non numerici → 400.
* **Policy**: `genera_error_policies` rigenerato, 1222 e 1223 `DATO_ERRATO` col loro ripiego senza
  `%s`. Nessun override di `ui_action`, come i codici gemelli del perimetro di riga (il campo lo
  accende `campiErrati`). La rigenerazione porta anche gli 11 codici di
  `brief-db-codici-non-trovato-email-e-permessi` (1211-1221, già nel CSV committato): i loro
  ripieghi li ho scritti qui (§G.3); i punti che li sollevano restano il giro BE di quel brief.
* **FE — regola del 2 (ok Tid, 2026-10-08)**: la tendina era scritta due volte, identica, in
  `ContrattoDrawer` e `OffertaDrawer`. Ora è il BB `ListinoDocumentoSelect`
  (`src/vendite/components/`): chiede i listini per utility ed emittente **del form**, si ricarica
  quando cambiano (guard di versione), senza uno dei due non chiede e il segnaposto lo dice. Riceve
  il dettaglio (`:record="detail"`): il listino già scritto sul documento resta fra le opzioni
  (F-2.4). Quando utility o emittente cambiano, un listino già scelto che il DB non propone più si
  **azzera** (resterebbe nel form senza vedersi, e il salvataggio lo rifiuterebbe su un campo vuoto
  a video); su una risposta in errore no, perché la lista vuota allora non è un «no». Registrato
  nel catalogo BB frontend.
* i18n: chiave nuova `vendite.listini.selezionabili_utility_emittente_first`; il segnaposto
  dell'offerta non dice più «con versione attiva».

### G.3 Test

* **BE unitari**: `test_lookups_api` (envelope `results`, parametri al service, assenti → `None`,
  non numerici → 400), `test_vendite_lookups_service`, la suite della fonte riscritta.
* **BE sul DB vero**, nuovo `tests/db/test_listini_selezionabili_db.py` (mondo costruito: azienda
  e operatore, due utility, un listino per utility, un cliente): il binding della lettura (ordine
  dei parametri provato **per mutazione**: scambiati, il test va rosso) e il **trasporto** del
  rifiuto 1222 col campo `listino_id` dal PATCH di contratto **e** di offerta.
* **FE**: `ListinoDocumentoSelect.spec.js` (montato, 6 test: anche l'azzeramento al cambio di
  utility e la scelta che resta su una risposta in errore), provato per mutazione su tre punti
  (guard di versione, listino corrente fra le opzioni, contesto incompleto); vitest 734/734,
  `npm run guards`, eslint, `check_i18n_keys`, build verdi.
* **Suite BE completa** con i presidi su DB: 6285 test, un solo rosso
  (`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`, gli 11 codici email/accessi), chiuso
  scrivendo i loro ripieghi dalle frasi del catalogo (richiesta di Tid, 2026-10-08).

### G.4 Collaudo a video (Tid), in aggiunta al §D.5

* **Contratto e offerta nuovi**: la tendina del listino è vuota finché utility ed emittente non
  ci sono, col segnaposto che lo dice; scelti, propone i soli listini di quella utility e di
  quell'azienda; cambiata la utility (o il cliente), la tendina si ricarica.
* **Un documento esistente** con un listino che oggi non si sceglierebbe: in modifica il listino
  si legge ancora.
* **Una riga d'offerta FISSA → MANUALE** dal drawer: si salva, e la quantità sparisce (prima del
  §F era un errore sul campo `quantita`, che il form non ha). Lo stesso sul contratto.


## H. Quarto giro DB: l'offerta accettata che non si trasforma (`dev/backend-tid`, 2026-10-11)

> **Chi scrive:** sessione BE/FE, dal collaudo a video di Tid del 2026-10-11. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§H.5), che **attende** la consegna DB.
> **Decisione:** di Tid, 2026-10-11: il giro sta in questo brief, perché rivede la sua B-D6.
> Due difetti con una causa sola, un'offerta ACCETTATA che non diventa né contratto né ordine:
> **H-A** fa sì che non ci si arrivi, **H-B** dà l'uscita quando ci si arriva lo stesso.

### H.1 Il caso (fatto datato, non il motivo)

Il 2026-10-11, su dbdev, l'offerta `OFC-0001064` (id 1070) è ACCETTATA. «Genera contratto» va in
errore `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` («Questo articolo non si eroga così…»), e l'offerta non
ha più uscite. Tre righe attive su quattro sono fuori dal perimetro di
`vendite.fn_articolo_erogazioni` (lo dice `script.fn_check_riga_erogazione('OFFERTA', 1070, …)`):

| Articolo | Riga | Erogazione / fonte | Il perimetro dell'articolo |
| --- | --- | --- | --- |
| `titoart0001` | OVERRIDE | CONSUMO / MANUALE | UNA_TANTUM, FISSA (default) o MANUALE |
| `art 100` | OVERRIDE | CONSUMO / LETTURE | UNA_TANTUM, FISSA (default) o MANUALE |
| `ARC005474` | AGGIUNTA | CONSUMO / MANUALE | UNA_TANTUM, FISSA (default) o MANUALE, dalla natura |

Le righe sono del 2026-10-07 mattina, prima del guard del perimetro (`20261007-63/-64`, applicati
la notte). `ARC005474` è stata modificata il 2026-10-11 in altri campi, e il guard `…_upd` non
scatta perché non sono cambiati né l'articolo né l'erogazione né la fonte (B-D6). Il push scrive
righe **nuove** sul contratto, e lì il guard all'INSERT le rifiuta.

### H.2 Il difetto, sul modello

**H-A. Il perimetro si controlla solo quando si scrive la riga, ma dipende da dati che stanno
fuori dalla riga.** La regola dipende dalla tipologia dell'articolo, e senza tipologia dalla
natura, dentro la utility del documento. `catalogo.articoli.listino_tipologia_id` si può cambiare
dopo, e nessun trigger lo blocca. Quindi una riga che era nel perimetro quando è stata scritta può
non esserlo più quando l'offerta si emette, si accetta o si trasforma. Le righe vecchie sono solo
il caso più evidente. ⛔ Per questo **B-D6 («senza presidio: sono solo dati di test») è superata**.
Il difetto non sta nei dati di test ma nel fatto che il controllo c'è solo al momento della
scrittura. Sul listino lo schema giusto esiste già (A-R2): l'emissione riverifica, e il pulsante
si spegne con lo stesso controllo (`script.fn_check_listino_congelabile`).

**H-B. Da ACCETTATA si esce solo trasformando l'offerta.** Le transizioni
(`config.stati_doc_offerte_transizioni`) prevedono l'annullo solo da BOZZA e la revisione solo da
EMESSA. Se la trasformazione è rifiutata, l'offerta resta bloccata per sempre. La guida
([gestione-offerte-commerciali](../../guide/gestione-offerte-commerciali.md) §3) dice che
ACCETTATA non è terminale, ma non dice che cosa si fa quando non si può trasformare. Il preventivo,
che è il documento gemello, prevede `ACCETTATO → ANNULLATO`
([gestione-preventivi](../../guide/gestione-preventivi.md)): manca la simmetria.

### H.3 Richiesta

| # | Cosa | Dettaglio |
| --- | --- | --- |
| **H-R1** | **Emissione: le righe nel perimetro** | il guard `BOZZA → EMESSA` rifiuta col primo motivo di `script.fn_check_riga_erogazione` su ogni riga attiva non ESCLUSIONE, col riferimento alla riga (id o articolo) nel contesto. La capability spegne «Emetti» con **lo stesso** controllo (`reason_key` nuova): pulsante e guard non possono dissentire, come per il listino |
| **H-R2** | **Trasformazione: il motivo prima del clic** | `can_push_contratto` e `can_genera_ordine` di `script.fn_available_actions_offerta` falsi, con `reason_key`, se una riga è fuori perimetro: lo stesso controllo dell'H-R1, letto al momento (la tipologia può essere cambiata dopo l'emissione). Il guard all'INSERT su `contratti_righe` resta come rete. ⚠️ Da verificare **dal percorso**: il ramo `genera_ordine` passa da un controllo del perimetro? Se l'ordine non ha erogazione, H-R2 vale solo per il contratto, e va scritto |
| **H-R3** | **Annullo da ACCETTATA** | transizione `ACCETTATA → ANNULLATA`, motivazione obbligatoria (`motivazione_rifiuto`, come da BOZZA), ammessa solo se l'offerta non ha documenti **vivi** a valle: `vendite.fn_offerta_documenti_vivi` (sede unica, da `brief-db-annullo-documento-con-legami` §7), non un secondo controllo. Esposta in `available_actions` |
| **H-R4** | **La stessa regola sul contratto** (simmetria) | anche la riga di contratto può uscire dal perimetro dopo essere stata scritta. L'attivazione (`DRAFT → ATTIVO`) verifica le righe con la stessa `fn_check_riga_erogazione`, nel guard e nella capability. In DRAFT le righe si possono correggere, quindi qui non serve un'uscita nuova |
| **H-R5** | Guide e manual | `gestione-offerte-commerciali` §3 (la transizione nuova, il controllo all'emissione), `api_offerte.md` (state machine, «Stati terminali»), `stati_doc_offerte_transizioni` (il commento: «5 transizioni») |
| **H-R6** | pgTAP | riga fuori perimetro → «Emetti» rifiutato col motivo e capability spenta; tipologia cambiata dopo l'accettazione → push spento col motivo; annullo da ACCETTATA senza documenti vivi ammesso, con un contratto vivo rifiutato, con un contratto annullato ammesso; attivazione del contratto con una riga fuori perimetro rifiutata |

### H.4 Da decidere (team DB, poi Tid)

* **H-D1, il controllo all'accettazione.** Proposta: **no**. Il «sì» del cliente si registra in
  ogni caso. Un'offerta che non si può più trasformare la fermano H-R2, con il motivo, e H-R3,
  con l'uscita.
* **H-D2, la revisione da ACCETTATA.** Proposta: **no**. Una revisione è una proposta nuova al
  cliente, e lui ha già accettato. Per riproporla si annulla (H-R3) e si crea un'offerta nuova,
  come per una rifiutata.
* **H-D3, le righe già scritte fuori perimetro.** Proposta: **nessuna bonifica**. Con H-R1, H-R2
  e H-R4 le righe le intercetta il primo passo che le usa, con il motivo. Se il team DB vuole un
  conteggio a catalogo per sapere quante sono, lo scrive lui: è un dato per trovare gli errori,
  non serve a decidere.

### H.5 Lato BE/FE, a consegna DB fatta

* **Offerta**: il pulsante «Annulla» da ACCETTATA arriva da `available_actions` e va gestito come
  l'annullo da BOZZA (dialog con motivazione). «Emetti», «Genera contratto» e «Genera ordine»
  spenti con il tooltip del motivo (frontend-standards, «stato ⇒ disabilita col motivo»).
  Verificare che l'endpoint `/annulla/` non abbia un controllo «solo da BOZZA» suo, che farebbe
  da specchio del DB.
* **Contratto**: «Attiva» spento con il motivo (H-R4).
* Policy e ripieghi per i codici nuovi (`genera_error_policies`, ripiego senza `%s`).
* Collaudo a video (Tid): `OFC-0001064` mostra «Genera contratto» spento con il motivo, e si
  annulla da ACCETTATA.


## I. Analisi del team DB per il giro unico (`dev/db-tid`, 2026-10-21)

> Rilegge il §F.4.3 e il §H sul codice vivo (doc auto-generata del 2026-10-21) e su ciò che è
> cambiato dopo il 2026-10-11. Siamo in sviluppo, senza produzione: niente bonifiche né
> compatibilità all'indietro; i dati di dbdev che non tornano si correggono a mano (AGENTS.md,
> «Bug di dati in sviluppo»).

### I.1 La quantità della riga DERIVATA_COMPONENTI: il modello va in un verso solo

Il nome dice «la quantità del padre viene dai componenti». Il modello fa il contrario, in tre sedi:

* `vendite.fn_offerta_eccezione_componenti_init` e `vendite.fn_contratto_riga_componenti_init`
  scrivono ogni componente come `coeff_qta × quantità del padre`, e **non creano nessun
  componente** se il padre non ha quantità («No-op su quantita IS NULL»);
* `script.trgfn_componenti_propaga_qta` propaga dal padre **ai** figli quando cambia la
  quantità del padre;
* sui componenti `quantita` è NOT NULL e non c'è una fonte: un componente non ha una quantità
  sua da cui il padre possa derivare.

Quindi una riga DERIVATA ha due sole forme possibili, ed entrambe sono sbagliate:

| Forma | Che cosa succede |
| --- | --- |
| senza quantità (quella che il form manda: `qta_operativa = null` fuori dalla FISSA) | il composito **non ha componenti**: il contrario di ciò che la fonte promette |
| con una quantità (mandata dal client o rimasta da una FISSA) | la quantità la scrive qualcuno a mano, e i componenti la seguono: è una FISSA con un altro nome, e il calcolo da `qta_operativa` (F-1) non vale |

Nessun lettore a valle distingue la DERIVATA: `fonte_quantita_attesa` la leggono solo i trigger
della riga, le letture del form e il push, che la copia. Opzioni:

* **(a) Ritirare DERIVATA_COMPONENTI.** Il composito prende le combinazioni della sua tipologia
  (o natura) come ogni articolo; la quantità del padre la porta la fonte (FISSA: dall'operatore),
  e i componenti la seguono. Si tolgono le quattro righe del vocabolario, il ramo «distinta» di
  `vendite.fn_articolo_erogazioni` (e il suo ordine), il nome in `script.fn_fonte_porta_quantita`
  e nei due CHECK, il ramo di `trgfn_qta_from_operativa`; il FE toglie la costante e il tag.
  Le righe di dbdev con DERIVATA si correggono a mano prima dell'apply.
* **(b) DERIVATA = quantità obbligatoria come la FISSA.** Un doppione della FISSA: due nomi per
  la stessa regola.
* **(c) Componenti con una fonte propria** (il padre somma i componenti). È un modello nuovo
  (fonte ed erogazione sul componente, fatturazione per componente): un cantiere a sé.

Proposta: **(a)**.

### I.2 Il §H dopo il 2026-10-11: che cosa resta da fare

**La causa principale di H-A è chiusa dal lato articolo.** Dal 2026-10-13 (A-10 di
[brief-db-articoli-ammessi-per-documento](brief-db-articoli-ammessi-per-documento.md)) un
articolo **usato** non cambia `listino_tipologia_id`, `natura_vendita_id`, `is_composito`
(`catalogo.trgfn_articoli_guard_struttura_se_usato`). Restano quattro strade per una riga che
esce dal perimetro dopo essere stata scritta:

1. il **listino operativo** cambia versione (OVERRIDE/ESCLUSIONE fuori listino, A-5);
2. il **vocabolario** del perimetro cambia (`config.listini_tipologie_erogazioni`,
   `nature_vendita_erogazioni`, `listini_tipologie_utilities`);
3. la porta SUPER_ADMIN `catalogo.fn_articolo_correggi_struttura`: confronta le righe vive con
   `script.fn_check_articolo_riga`, che **non** giudica erogazione e fonte. ⚠️ Una correzione
   della tipologia può quindi rendere una riga fuori perimetro senza essere fermata: è un buco;
4. le righe scritte **prima** dei guard (`OFC-0001064`): dati di sviluppo, si correggono a mano.

**H-R1, H-R2 (contratto) e H-R4 sono già decisi.** Sono l'R-6 di quel brief («le righe già
scritte le intercetta il primo passo che le usa») e la A-5 di Tid («le intercetta
l'emissione»). Forma proposta, una regola sola:

* **una check di riga composta**: `script.fn_check_articolo_riga` seguita da
  `script.fn_check_riga_erogazione` con erogazione e fonte della riga. È «questa riga può stare
  in questo documento», intera;
* **una lettura per documento**: le righe vive di un'offerta o di un contratto che quella check
  non ammette, col primo motivo. È la gemella di `catalogo.fn_articolo_righe_vive_non_ammesse`
  (che legge per articolo), e le due condividono la check composta;
* la chiamano **il guard e la capability** di BOZZA→EMESSA dell'offerta, `can_push_contratto` e
  DRAFT→ATTIVO del contratto (guard e capability), come già fanno listino, prezzi e indirizzi;
* `catalogo.fn_articolo_righe_vive_non_ammesse` passa alla check composta: chiude il buco del
  punto 3.

**Genera ordine non passa dal DB.** «Genera ordine» dall'offerta è orchestrato in Python
(`ordini_service.crea_ordine_da_offerta`: crea l'ordine, scrive l'origine, copia le righe
espanse), mentre il push al contratto è un verbo DB (`vendite.fn_push_offerta_a_contratto`). Le
righe dell'ordine le giudica il guard dell'ordine (solo merce, solo componente, kit senza
componenti), non il perimetro d'erogazione: l'ordine non ha erogazione. Da decidere (§I.3).

**H-R3** resta com'è scritto: riga nuova in `config.stati_doc_offerte_transizioni`
(ACCETTATA → ANNULLATA, motivazione obbligatoria) e il guard di transizione che la ammette solo
senza documenti vivi (`vendite.fn_offerta_documenti_vivi`).

### I.3 Decisioni di Tid (2026-10-21)

| # | Domanda | Decisione |
| --- | --- | --- |
| I-D1 | La DERIVATA_COMPONENTI (§I.1) | ✅ **(a) si ritira**: il composito prende le combinazioni della tipologia o della natura, i componenti seguono la quantità del padre |
| I-D2 | «Genera ordine» dall'offerta (§I.2) | ✅ **verbo DB** (`vendite.fn_genera_ordine_da_offerta`, gemello del push al contratto: una transazione, documenti vivi, origine, righe espanse) **e motivo prima del clic**: `can_genera_ordine` spento con la check delle righe dell'ordine, la stessa che il verbo incontra. Il BE ritira `ordini_service.crea_ordine_da_offerta` e chiama il verbo |
| I-D3 | = H-D1, controllo all'accettazione | ✅ no |
| I-D4 | = H-D2, revisione da ACCETTATA | ✅ no |
| I-D5 | = H-D3, righe già scritte fuori perimetro (e righe DERIVATA) | ✅ a mano su dbdev prima dell'apply, con una query preparata dal team DB; nessuna bonifica nei changeSet |
| I-D6 | (emersa scrivendo, §I.5.2) un kit si vende «a consumo»? | ✅ **no, solo a quantità fissa**: sul composito il perimetro tiene le sole combinazioni FISSA |
| I-D7 | le 9 righe fuori perimetro di dbdev (§I.5.4) | ✅ **restano per il collaudo** del §H.5; dopo, le offerte si annullano dall'app e i contratti in bozza si correggono o si annullano |

Supera B-D5 (la DERIVATA sul composito) e chiude il primo trovato del §F.4.3. Con I-D1 cade anche
la riserva del §G.1: `quantita` esce dalle chiavi ammesse del payload di riga.

### I.4 Il giro DB, in ordine

1. **Query per dbdev** (I-D5): righe DERIVATA → FISSA con la loro quantità, o la riga si toglie;
   righe d'offerta e di contratto fuori perimetro corrette o tolte. La lancia Tid prima dell'apply.
2. **Ritiro della DERIVATA** (I-D1): vocabolario `config.erogazioni_fonti` (righe 3, 6, 10, 13),
   ramo «distinta» e ordine di `vendite.fn_articolo_erogazioni`, `script.fn_fonte_porta_quantita`,
   i due CHECK `chk_*_quantita_per_fonte`, il ramo di `script.trgfn_qta_from_operativa`, commenti
   e manual che la nominano (`contratti_righe`, `trgfn_qta_from_operativa`, `erogazioni_fonti`).
3. **La check di riga composta** e la **lettura per documento** (§I.2); passa alla check composta
   anche `catalogo.fn_articolo_righe_vive_non_ammesse`.
4. **Guard e capability**: BOZZA→EMESSA dell'offerta, `can_push_contratto`, DRAFT→ATTIVO del
   contratto (H-R1, H-R2, H-R4).
5. **Genera ordine** (I-D2): il verbo e `can_genera_ordine`.
6. **Annullo da ACCETTATA** (H-R3).
7. Codici d'errore, guide e manual (H-R5), pgTAP (H-R6, più il ritiro della DERIVATA e il verbo).

### I.5 Consegna del giro DB (`dev/db-tid`, 2026-10-21)

#### I.5.1 ChangeSet (`20261021-44` → `-61`, non applicati)

| ChangeSet | Oggetto | Che cosa |
| --- | --- | --- |
| `00_schema/vendite/-44` | `chk_contrighe_quantita_per_fonte`, `chk_offerte_eccezioni_quantita_per_fonte` | solo FISSA porta la quantità; COMMENT dei CHECK, delle due colonne `fonte_quantita_attesa` e di `config.erogazioni_fonti`. preCondition HALT sulle righe che il CHECK rifiuterebbe |
| `20_code/script/-45` | `script.fn_fonte_porta_quantita` | `p_fonte = 'FISSA'` |
| `20_code/script/-46` | `script.trgfn_qta_from_operativa` | tolto il ramo «NULL ammesso se non FISSA» (era la DERIVATA) |
| `20_code/script/-47`, `20_code/vendite/-49`, `20_code/script/-50` | `trgfn_righe_guard_quantita_per_fonte`, `fn_documento_riga_erogazioni`, `trgfn_righe_default_erogazione_da_articolo` | solo commenti e COMMENT che nominavano la DERIVATA |
| `20_code/vendite/-48` | `vendite.fn_articolo_erogazioni` | via il ramo «distinta»; **I-D6**: sul composito le sole combinazioni FISSA, e se il default della base non è FISSA il default del kit è la prima FISSA |
| `80_data/changelog/-51` + CSV | `config.erogazioni_fonti` | DELETE delle 4 combinazioni DERIVATA (il mirror non cancella); preCondition HALT se una riga di documento la usa ancora |
| `20_code/script/-52` | `script.fn_check_riga_documento_su_contesto` (nuova) | la riga INTERA: articolo, poi (offerta e contratto) erogazione e fonte |
| `20_code/script/-53` | `script.fn_check_righe_documento` (nuova) | le righe non ammesse di un'offerta o di un contratto: un motivo `E_DOC_RIGA_NON_AMMESSA` per riga, contesto letto una volta |
| `20_code/script/-54` | `script.fn_check_righe_offerta_in_ordine` (nuova) | le righe espanse dell'offerta giudicate come righe d'ordine |
| `20_code/catalogo/-55` | `catalogo.fn_articolo_righe_vive_non_ammesse` | passa alla riga intera: chiude il buco della porta SUPER_ADMIN (§I.2 punto 3) |
| `20_code/script/-56` | `script.fn_check_offerta_annullabile` (nuova) | `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI` col bersaglio, se dall'offerta vive un contratto o un ordine |
| `20_code/vendite/-57` | `vendite.trgfn_offerte_commerciali_guard_transizione` | BOZZA→EMESSA: per ultime le righe (H-R1); verso ANNULLATA: `fn_check_offerta_annullabile` (H-R3) |
| `20_code/script/-58` | `script.fn_available_actions_offerta` | righe verso EMESSA (solo da BOZZA); push e genera ordine **proposti e spenti** col motivo delle righe (H-R2, I-D2); motivo dell'annullo |
| `20_code/vendite/-59`, `20_code/script/-60` | guard di transizione e capability del contratto | verso ATTIVO, dopo gli indirizzi e prima del sovrapposto, le righe (H-R4) |
| `20_code/vendite/-61` | `vendite.fn_genera_ordine_da_offerta` (nuova) | il verbo (I-D2): offerta `FOR UPDATE`, stato, documenti vivi, righe, testata con la provenienza, indirizzo di default, righe espanse coi prezzi negoziati e i componenti |

CSV: `stati_doc_offerte_transizioni` (id 7, ACCETTATA → ANNULLATA, come la 2), `erogazioni_fonti`
(senza le 4 DERIVATA), `codici_errore` e `messaggi_errore` (1381 `E_DOC_RIGA_NON_AMMESSA`, 1382
`E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`; `E_OFFERTA_NON_TROVATA` non nomina più il contratto, la legge
anche il verbo dell'ordine; `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` e tre note che citavano la DERIVATA o
il Python).

Manual e guide: `contratti_righe`, `contratti`, `offerte_commerciali`, `offerte_commerciali_eccezioni`,
`fn_contratto_righe_preview`, `fn_push_offerta_a_contratto`, `trgfn_qta_from_operativa`;
`gestione-offerte-commerciali` (§3, §7, §8.bis, §11.6, §12), `gestione-ordini` §2.2.

#### I.5.2 Trovato scrivendo, deciso: il kit «a consumo» (I-D6)

La fixture di `test_offerte_eccezioni_componenti` aveva un kit di una tipologia solo a consumo,
con le componenti grazie alla DERIVATA e a una quantità scritta a mano. Tolta la DERIVATA, un kit a
consumo nasce senza quantità, quindi **senza componenti e con prezzo 0** (il prezzo del padre è la
somma dei componenti): il buco c'era già per i kit con MANUALE o LETTURE. Decisione di Tid: un kit si
vende solo a quantità fissa (`-48`). Un kit di una tipologia solo a consumo non ha erogazioni, e
non entra in offerte e contratti (motivo SENZA_EROGAZIONE di `script.fn_check_articolo_riga`).

⚠️ Sui fixture: `dbops.fn_pgtap_crea_listino` sceglie la prima tipologia della utility, che può
essere solo a consumo. Due pgTAP con un kit nel listino ora scelgono una tipologia con la FISSA
(`test_offerte_eccezioni_componenti`, `test-righe-eccezioni-articolo-ammesso-v1`).

#### I.5.3 La prova (scratch `zeroerp_ruoli`, 2026-10-21, prima dell'apply)

* SQL estratto di `-44` → `-61` più gli effetti dei CSV, in una transazione annullata: compila, una
  funzione per nome (nessun overload), `plpgsql_check` senza errori (un avviso STABLE/VOLATILE su
  `fn_check_righe_documento`, lo stesso delle check esistenti).
* pgTAP con l'SQL estratto dopo il `BEGIN;`, uno per file: 141 file censiti (oggetti toccati,
  erogazioni, compositi, transizioni) e 55 presidi trasversali su `pg_proc`. I rossi «dopo» si
  confrontano coi «prima» degli stessi file: le **regressioni erano 8 file**, tutte attese e corrette.
  * `test-fn-available-actions-offerta-v1` (8, 12): da ACCETTATA c'è «annulla», spenta con
    DOCUMENTI_VIVI;
  * `test-rubinetto-primo-motivo-v1` (5): da 40 a 41, il verbo è un sito nuovo dell'helper;
  * `test-erogazioni-vocabolario-v1` (1): 9 combinazioni;
  * `test-righe-quantita-per-fonte-v1` (5, 10, 13): composito FISSA, CHECK e funzione dicono la sola
    FISSA, la DERIVATA è fuori perimetro;
  * `test_offerte_eccezioni_componenti` (fixture, 16): il kit FISSA; il 16 prova il rifiuto del kit
    a consumo (prima si saltava);
  * `test-righe-erogazione-da-articolo-v1` (3, 14-15, 21, 22): il 14-15 costruiva la riga fuori
    perimetro con la porta SUPER_ADMIN, che il `-55` chiude: ora ne prova la chiusura;
  * `test-indirizzi-documento-seguono-cliente-v1` (3): il verbo legge `fn_doc_indirizzo_default`;
  * `test-righe-eccezioni-articolo-ammesso-v1` (20): fixture, tipologia con la FISSA.
  Gli altri rossi sono identici prima e dopo (scratch con pochi dati).
* pgTAP nuovo `vendite/offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1` (runner owner:
  la fixture toglie una combinazione dal vocabolario della natura): **25/25**. Emissione, push,
  genera ordine (rifiuto, ordine generato, idempotenza, XOR, stato), annullo da ACCETTATA con e
  senza documento vivo, attivazione del contratto, lettura per articolo, seed.
* La query per dbdev (§I.5.4) provata su dbdev in transazione annullata: 1 riga, nessuna DERIVATA
  residua, trigger riacceso.

#### I.5.4 dbdev, prima dell'apply (Tid)

Una sola riga usa la DERIVATA (2026-10-21): `vendite.contratti_righe` 39, contratto 34 CESSATO,
articolo «composito». Diventa CANONE/FISSA con `qta_operativa` 1 (nel perimetro dell'articolo anche
dopo la I-D6); il contratto è chiuso, quindi si spegne il solo lock delle righe fuori bozza, dentro la
transazione. Come owner: `psql -X -1 -v ON_ERROR_STOP=1 -f <file>`.

```sql
ALTER TABLE vendite.contratti_righe DISABLE TRIGGER trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt;
UPDATE vendite.contratti_righe
   SET fonte_quantita_attesa = 'FISSA', qta_operativa = 1
 WHERE id = 39 AND fonte_quantita_attesa = 'DERIVATA_COMPONENTI';
ALTER TABLE vendite.contratti_righe ENABLE TRIGGER trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt;
```

✅ **Le righe fuori perimetro non si correggono** (I-D7 di Tid, 2026-10-21, che precisa I-D5):
il 2026-10-21 su dbdev sono 9 righe vive in 2 contratti DRAFT e 3 offerte ACCETTATE, fra cui le tre
di `OFC-0001064` (id 1070). Non fermano l'apply, e sono il materiale del collaudo del §H.5: «Genera
contratto» spento col motivo, poi l'annullo da ACCETTATA. Dopo il collaudo si annullano dall'app.

#### I.5.5 Richieste al BE/FE, a apply fatto

* **Genera ordine** (I-D2): `ordini_service.crea_ordine_da_offerta` chiama
  `vendite.fn_genera_ordine_da_offerta(offerta_id)` (ritorna l'id dell'ordine) e ritira
  l'orchestrazione Python (stato, documenti vivi, testata, provenienza, righe, componenti) e i
  suoi specchi. Codici: `E_OFFERTA_NON_TROVATA`, `E_ORD_ORIGINE_NON_CONVERTIBILE`,
  `E_ORD_OFFERTA_GIA_CONVERTITA` e `E_OFFERTA_CONTRATTO_GIA_GENERATO` (col bersaglio),
  `E_DOC_RIGA_NON_AMMESSA`.
* **Pulsanti** (frontend-standards, «stato ⇒ disabilita col motivo»): `push_contratto` e
  `genera_ordine` ora arrivano anche **spenti**, con `reasons`; «Emetti» e «Attiva» possono avere il
  motivo `RIGA_NON_AMMESSA`, con l'articolo nei valori e il motivo della riga in
  `dettaglio.motivo_riga`; «Annulla» da ACCETTATA, spenta con `DOCUMENTI_VIVI`.
* **Annullo da ACCETTATA** (H-R3): il dialog con la motivazione come da BOZZA; l'endpoint non deve
  avere un «solo da BOZZA» suo.
* **Codici nuovi**: policy e ripieghi di `E_DOC_RIGA_NON_AMMESSA` (DATO_ERRATO, campo `articolo_id`,
  due valori) e `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI` (CONFLITTO_STATO, bersaglio). Chiavi i18n:
  `common.azione_reason.riga_non_ammessa`, `vendite.offerte.azione_reason.documenti_vivi`
  (`scripts/check_i18n_keys.py` le vede: rosso finché il FE non le semina).
* **DERIVATA**: via dal FE (`constants.js`, `erogazioniRiga.js` e il tag «Derivata dai
  componenti») e dalle pagine `docs/it/backend` (`api_offerte`, `api_contratti`,
  `modello-contratti`); `quantita` esce dalle chiavi ammesse del payload di riga (§G.1). Il kit nel
  form propone le sole combinazioni FISSA: arrivano dal DB.
* Doc del BE: `api_offerte.md` (state machine con ACCETTATA → ANNULLATA, genera ordine come verbo).

#### I.5.6 Chiusura del lato DB (2026-10-21)

La query del §I.5.4 è stata lanciata su dbdev (la riga 39 è CANONE/FISSA; nessuna DERIVATA
residua). Il primo apply su dbdev si era fermato, come previsto, sulla preCondition del `-44`, che
aveva trovato quella riga. Dopo la correzione Tid ha applicato `20261021-44` → `-61` su dbdev e
scratch, e la corsa pgTAP è verde: nessuna regressione, ogni rosso era già noto. Al DB non resta
niente; riparte il BE/FE (§I.5.5).
