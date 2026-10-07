# Brief DB — Offerta, dal collaudo del drawer: l'emissione e l'erogazione

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-07. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§A.5, §B.5), che **attende** la consegna DB.
> **Origine:** il collaudo a video di Tid del drawer dell'offerta
> (`brief-db-righe-esclusione-solo-non-si-vende` §13). Due difetti di modello, in un brief solo
> (richiesta di Tid): **A** blocca l'emissione e va per primo; **B** è la forma delle righe.
> **Decisione:** di Tid, 2026-10-07, su B: il default dell'erogazione (e della fonte) si
> **eredita dall'articolo**, dalla sua tipologia; il perimetro delle scelte segue la utility.
> **Stato:** ⏳ da fare lato DB. 🔴 **A blocca l'emissione di ogni offerta nuova.**
> **Da decidere:** A-D1, A-D2 (§A.3); B-D1…B-D3 (§B.3).

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
