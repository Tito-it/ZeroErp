# Brief DB — Offerta, dal collaudo del drawer: l'emissione e l'erogazione

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-07. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§A.5, §B.5), che **attende** la consegna DB.
> **Origine:** il collaudo a video di Tid del drawer dell'offerta
> (`brief-db-righe-esclusione-solo-non-si-vende` §13). Due difetti di modello, in un brief solo
> (richiesta di Tid): **A** blocca l'emissione e va per primo; **B** è la forma delle righe.
> **Decisione:** di Tid, 2026-10-07, su B: il default dell'erogazione (e della fonte) si
> **eredita dall'articolo**, dalla sua tipologia; il perimetro delle scelte segue la utility.
> **Stato (2026-10-07, notte): ✅ LATO DB CHIUSO.** Parte A (`20261007-40 → -47`) e parte B
> (`-50 → -54`, `-60 → -65`) applicate da Tid; pgTAP verdi su dbdev. **Resta il giro BE/FE**:
> §C.6.4 per la parte A, §C.9.6 per la parte B (sostituiscono §A.5 e §B.5). Poi il collaudo a video
> e l'archiviazione in `work-done/`.
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
* **B-D6** ✅ le righe già scritte restano come sono, **senza presidio**: sono solo dati di test.
  Il guard scatta su INSERT e quando cambiano articolo, erogazione o fonte.

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
