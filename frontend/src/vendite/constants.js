// Costanti dominio vendite condivise FE.
// Mantenere allineate con `apps/vendite/services/_approvazioni_prezzo_constants.py`
// (BE) e con i seed DB (`config.stati_doc_preventivi`,
// `config.azioni_processo`).

import { aspettoAzione } from '../core/aspettoAzioni'
import { SORGENTE_CODES } from '../documenti/constants'

// Stati di workflow approvazione prezzo applicabili al campo
// `vendite.preventivi_righe.stato_approvazione_prezzo` (ENUM nativo
// `config.stato_approvazione_prezzo`).
export const STATO_APPROVAZIONE = Object.freeze({
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
})

// Stato di emissione di una riga di commessa
// (`vendite.commesse_attivita.stato_emissione`, CHECK
// `chk_commesse_attivita_stato_emissione` — verificato sul DB 2026-07-29).
// NON_EMESSA = ancora lavorabile; EMESSA = ha generato la sua
// `attivita_fatturabili` ed e' in viaggio verso la fattura; ANNULLATA = riga
// manuale tolta dal giro senza cancellarla (il valore che TUTTE le porte verso
// fattura e cockpit gia' filtrano, cfr. brief-annullamento-righe-manuali-commessa).
// ⚠️ Gemello cromatico in `core/utils/severity.js` (`STATO_EMISSIONE_ATTIVITA_MAP`):
// le due liste vanno tenute allineate a mano — `core/` non puo' importare da un
// dominio, quindi la derivazione automatica non e' praticabile.
export const STATO_EMISSIONE_ATTIVITA = Object.freeze({
  NON_EMESSA: 'NON_EMESSA',
  EMESSA: 'EMESSA',
  ANNULLATA: 'ANNULLATA',
})

// Esito di esecuzione dentro un lotto di fatturazione. UN vocabolario per DUE
// livelli — `fatturazione_lotti_fatture.stato_esecuzione` (la fattura prodotta)
// e `fatturazione_lotti_gruppi.stato_esecuzione` (il documento preso in carico,
// che una fattura può non essere mai diventata): la D-2 di
// `brief-db-esito-gruppo-lotto` tiene i due CHECK identici, perché «due colonne
// che rispondono alla stessa domanda a due livelli non possono parlare due
// lingue».
// ⚠️ Specchio, non autorità: a enforcare sono `chk_lotti_gruppi_stato_esecuzione`
// e `chk_fatturazione_lf_stato_esecuzione`. Vive qui per la stessa ragione degli
// altri enum del file — un typo non romperebbe niente a runtime: la riga
// smetterebbe di accendersi e la lista sembrerebbe semplicemente sana.
// ⛔ `null` NON è un valore di questo vocabolario: significa «nessuno l'ha
// detto» — il documento non è stato tentato in quel lotto — e NON «è andata
// bene». Chi rende deve tenere distinti i due casi.
// ⚠️ Gemello cromatico in `core/utils/severity.js`
// (`STATO_ESECUZIONE_LOTTO_MAP`), da tenere allineato a mano: `core/` non può
// importare da un dominio.
export const STATO_ESECUZIONE_LOTTO = Object.freeze({
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  ERRORE: 'ERRORE',
  // ⭐ Solo sul livello DOCUMENTO (2026-09-08): l'operatore ha tolto questo
  // documento dal giro. Una FATTURA non lo può avere — quando un documento
  // esce, la sua bozza viene cancellata e la riga di ponte sparisce.
  ESCLUSO: 'ESCLUSO',
})

// Le schede del drawer del lotto (`LottoDrawer`), per `value` dei `Tabs`.
// ⭐ Vivono qui e non nel template perché sono un CONTRATTO fra due sedi: il
// template le dichiara, e `scegliRamoBanner` (la funzione pura del banner)
// decide su QUALE atterra il link del lotto fermo. Scritte a mano in entrambe,
// una rinomina lascerebbe la pagina SENZA PANNELLO e senza errore — il caso
// dei tab condizionali di frontend-standards §Pattern Tab-View.
export const LOTTO_SCHEDE = Object.freeze({
  DOCUMENTI: 'fatture',
  PRESI_IN_CARICO: 'gruppi',
  TASK: 'task',
  SEGNALAZIONI: 'segnalazioni',
  STORIA: 'storia',
})

// Natura della riga di commessa (`commesse_attivita.tipo_movimento`): filtro
// della lista attivita' e colonna «Movimento».
// ⚠️ Specchio, non autorita': a enforcare e' il CHECK
// `chk_commesse_attivita_tipo_movimento`. Vive qui per la stessa ragione degli
// altri enum di questo file — un typo in un literal non romperebbe niente a
// runtime: filtrerebbe zero righe e la lista sembrerebbe semplicemente vuota.
export const TIPO_MOVIMENTO_ATTIVITA = Object.freeze({
  NORMALE: 'NORMALE',
  RETTIFICA: 'RETTIFICA',
  ONERE: 'ONERE',
})

// Stato di approvazione di una riga di commessa
// (`vendite.commesse_attivita.stato_approvazione`). Gemello dell'asse
// emissione qui sopra — stessa avvertenza: la mappa cromatica vive in
// `core/utils/severity.js` (`STATO_APPROVAZIONE_ATTIVITA_MAP`) e va tenuta
// allineata a mano. ⚠️ NON confondere con `STATO_APPROVAZIONE` (PENDING/
// APPROVED/REJECTED): quello e' il workflow di approvazione PREZZO.
export const STATO_APPROVAZIONE_ATTIVITA = Object.freeze({
  BOZZA: 'BOZZA',
  APPROVATA: 'APPROVATA',
  RIFIUTATA: 'RIFIUTATA',
})

// Stato di una versione di listino: il codice del vocabolario
// `config.stati_doc_listino_versioni` (`stato` nella risposta del backend).
// La mappa cromatica vive in `core/utils/severity.js`
// (`STATO_VERSIONE_LISTINO_MAP`) e va tenuta allineata a mano.
export const STATO_VERSIONE_LISTINO = Object.freeze({
  BOZZA: 'BOZZA',
  ATTIVA: 'ATTIVA',
  CHIUSA: 'CHIUSA',
})

// Le `action_key` dei passaggi manuali della versione di listino (meta della
// matrice `config.transizioni_stati_listino_versioni`), come arrivano in
// `azioni_permesse`. Oggi uno solo: BOZZA -> ATTIVA.
export const PASSAGGI_VERSIONE_LISTINO = Object.freeze({
  ATTIVA: 'attiva',
})

// I codici del registro delle azioni di riga (`useAzioneRiga`) per i verbi
// della versione di listino: il registro dice QUALI colonne della riga portano
// il motivo del verbo spento. ⚠️ Non sono le `action_key` di
// `PASSAGGI_VERSIONE_LISTINO` qui sopra (quelle dicono se il passaggio e'
// permesso): due vocabolari, due costanti.
export const AZIONE_RIGA_VERSIONE_LISTINO = Object.freeze({
  ATTIVA: 'ATTIVA_VERSIONE_LISTINO',
  ELIMINA: 'ELIMINA_VERSIONE_LISTINO',
  CHIUDI: 'CHIUDI_VERSIONE_LISTINO',
})

// Codici azione di processo (`config.azioni_processo.permission_codename`).
// Usati con `auth.isActionAllowed(...)` per gating UI lato FE.
export const PRICING_ACTIONS = Object.freeze({
  OVERRIDE: 'prezzo_override_manuale',
  APPROVE: 'approva_prezzo_override',
})

// Azione «Invia a commessa» quando il blob la NEGA (`can_push_commessa` false
// + motivo): la forma del pulsante, uguale per DDT e ordine — cambia solo la
// `label_key` del dominio. Si passa a `useEntityCapabilities().azioneNegata`.
// ⭐ Icona e colore dalla mappa del verbo: negato o no, e' lo stesso pulsante.
export const AZIONE_PUSH_COMMESSA = Object.freeze({
  key: 'push_commessa',
  severity: aspettoAzione('push_commessa').severity,
  icon: aspettoAzione('push_commessa').icona,
})

// Codici stato preventivo (`config.stati_doc_preventivi.codice_interno`).
// NB: 'Bozza' e' la descrizione it-IT, il codice tecnico stabile e' DRAFT.
// EVASO e' lo stato terminale post-push commessa: transizione automatica
// ACCETTATO -> EVASO scatenata dal BE (preventivi_service.push_a_commessa)
// quando tutte le righe pushable sono in commessa.
export const STATO_PREVENTIVO = Object.freeze({
  DRAFT: 'DRAFT',
  EMESSO: 'EMESSO',
  ACCETTATO: 'ACCETTATO',
  EVASO: 'EVASO',
  RIFIUTATO: 'RIFIUTATO',
  SCADUTO: 'SCADUTO',
  ANNULLATO: 'ANNULLATO',
})

// Destinazione effettiva di smistamento riga preventivo
// (`config.nature_vendita.destinazione_tipo`, natura NULL = pregresso →
// COMMESSA lato DB). Guida il ROUTING di "Smista selezionate" nel
// PreventiviSmistamentoDialog: merce → ordine, servizi → commessa.
// ⭐ I valori sono codici di `config.sorgenti` (FK dal 2026-10-19,
//    brief-db-grammatica-unica-documenti lotto 2b): si leggono da
//    `SORGENTE_CODES`, non si riscrivono. Le chiavi dicono il ramo.
export const DESTINAZIONE_SMISTAMENTO = Object.freeze({
  ORDINE: SORGENTE_CODES.ORDINE_VENDITA,
  COMMESSA: SORGENTE_CODES.COMMESSA,
})

// Stato autorevole di smistamento riga preventivo (colonna derivata
// `stato_smistamento` di `vw_preventivi_smistamento_righe`). RESIDUA = non
// smistata (unica selezionabile); A_ORDINE = stato finale ramo merce;
// IN_COMMESSA/EMESSA_AF/FATTURATA = progressivi ramo commessa.
export const STATO_SMISTAMENTO = Object.freeze({
  RESIDUA: 'RESIDUA',
  A_ORDINE: 'A_ORDINE',
  IN_COMMESSA: 'IN_COMMESSA',
  EMESSA_AF: 'EMESSA_AF',
  FATTURATA: 'FATTURATA',
})

// Codici stato contratto (`config.stati_doc_contratti.codice_interno`).
// DRAFT = bozza pre-attivazione; ATTIVO = contratto in vigore; CESSATO =
// terminato (data fine raggiunta o cessazione manuale anticipata);
// ANNULLATO = chiuso dalla bozza senza essere mai entrato in vigore.
export const STATO_CONTRATTO = Object.freeze({
  DRAFT: 'DRAFT',
  ATTIVO: 'ATTIVO',
  CESSATO: 'CESSATO',
  ANNULLATO: 'ANNULLATO',
})

// Stati della testata di commessa (`vendite.stati_commessa.codice_interno`)
// che il frontend NOMINA: solo l'annullo, che passa dalla conferma dei legami
// (brief-db-annullo-a-valle-riapre-a-monte). Le altre azioni di stato
// arrivano data-driven dalle capability e non si nominano qui.
// ⚠️ Femminile, a differenza dei documenti (ANNULLATO): e' il codice del DB.
export const STATO_COMMESSA = Object.freeze({
  ANNULLATA: 'ANNULLATA',
})

// La natura del legame del lettore dei legami (`vendite.fn_documento_legami`),
// che la finestra di conferma dell'annullo distingue: CONSUMO e PROVENIENZA si
// riaprono, ANNULLO si annulla con il documento (gli oneri della commessa).
// ⛔ Il documento che si annulla e l'origine del legame NON si nominano qui:
// sono codici di `config.sorgenti`, cioe' `SORGENTE_CODES` di
// `documenti/constants` (dal 2026-10-19, grammatica unica: lotto 2a il
// documento, `DOCUMENTO_LEGAMI` ritirato; lotto 2b l'origine, `ORIGINE_LEGAME`
// ritirato).
export const NATURA_LEGAME = Object.freeze({
  CONSUMO: 'CONSUMO',
  PROVENIENZA: 'PROVENIENZA',
  ANNULLO: 'ANNULLO',
})

// Forma di un contratto, DERIVATA (non persistita) da `contratti.listino_id`:
// con un listino di riferimento o interamente negoziato. La emette il backend
// nel contesto pricing (`ContrattiRepository.resolve_contesto_pricing_contratto`,
// campo `forma`) e la ricava allo stesso modo il form della testata. Una sede
// per i due drawer che la leggono (regola del 2, 2026-10-04).
export const FORMA_CONTRATTO = Object.freeze({
  CON_LISTINO: 'con_listino',
  SENZA_LISTINO: 'senza_listino',
})

// Mappa stato→modalita'-PDF di contratti e preventivi ora DATA-DRIVEN via
// capability `pdf` di `fn_available_actions_{contratto,preventivo}`
// (`config.stati_doc_{contratti,preventivi}.pdf_mode`), consumata da
// `EntityPdfButton`: niente piu' liste di stati hardcoded qui.

// Chiave nel meta della pratica APPROVAZIONE_PREZZO che linka la riga
// preventivo target. Coerente col BE
// `_approvazioni_prezzo_constants.META_KEY_RIGA_PREVENTIVO_ID`.
export const META_KEY_RIGA_PREVENTIVO_ID = 'riga_preventivo_id'

// Tipi eccezione su `vendite.contratti_righe.tipo_eccezione` (ENUM nativo
// `vendite.tipo_eccezione_contratto`). Refactor modalita 2026-05-15.
// `DA_LISTINO` non e' un valore della colonna ma una pseudo-origine
// derivata in `fn_contratto_righe_preview` per righe del listino senza
// eccezioni — usata lato FE come marker.
// `ADESIONE` (G-0-ter, 2026-10-29): l'articolo del listino al prezzo del
// listino, senza prezzo sulla riga; e' anche l'origine della sua riga di lista.
export const TIPO_ECCEZIONE = Object.freeze({
  OVERRIDE: 'OVERRIDE',
  ESCLUSIONE: 'ESCLUSIONE',
  AGGIUNTA: 'AGGIUNTA',
  ADESIONE: 'ADESIONE',
  DA_LISTINO: 'DA_LISTINO',
})

// I verbi che una riga del contratto ammette: la colonna `azioni` di
// `vendite.fn_contratto_righe_preview` (capability di riga, §12.5 delle linee
// guida SQL; brief-db-liste-righe-documento D-8.4). Il DB dice QUALI valgono
// per la riga, il drawer li rende: SOVRASCRIVI_PREZZO e MODIFICA sono il click
// sulla riga, gli altri voci del menu.
export const AZIONE_RIGA_CONTRATTO = Object.freeze({
  SOVRASCRIVI_PREZZO: 'SOVRASCRIVI_PREZZO',
  ESCLUDI: 'ESCLUDI',
  MODIFICA: 'MODIFICA',
  RIPRISTINA_LISTINO: 'RIPRISTINA_LISTINO',
  RIPRISTINA_ARTICOLO: 'RIPRISTINA_ARTICOLO',
  RIMUOVI: 'RIMUOVI',
  // L'ADESIONE (`20261029-39`): sulla riga del listino «aderisci», sulla riga
  // aderita «rimuovi adesione» (torna una riga del listino, non addebitata).
  ADERISCI: 'ADERISCI',
  RIMUOVI_ADESIONE: 'RIMUOVI_ADESIONE',
})

// Tipi erogazione su `vendite.contratti_righe.tipo_erogazione` (vocabolario
// `config.erogazioni_fonti`). Il form delle righe mostra quelli che il DB
// dichiara per l'articolo (`fn_documento_riga_erogazioni`), ORARIO compreso.
export const TIPO_EROGAZIONE = Object.freeze({
  CANONE: 'CANONE',
  UNA_TANTUM: 'UNA_TANTUM',
  ORARIO: 'ORARIO',
  CONSUMO: 'CONSUMO',
})

// Fonti quantita su `vendite.contratti_righe.fonte_quantita_attesa`
// (obbligatoria su ogni riga che non e' un'ESCLUSIONE). ⛔ Quali coppie
// (erogazione, fonte) una riga puo' avere NON si scrive qui: lo dice il DB
// dall'articolo (`vendite.fn_documento_riga_erogazioni`, letta dal form delle
// righe), dal 2026-10-07 (brief-db-offerta-emissione-ed-erogazione B-R4).
// ⛔ DERIVATA_COMPONENTI non c'e' piu' (I-D1, 2026-10-21): il vocabolario del DB
// (`config.erogazioni_fonti`) ha le quattro fonti qui sotto.
// `DURATA` (G-9, `20261029-32`): la quantita' la conta il sistema dai giorni o
// dai mesi del periodo; `CANONE/MANUALE` e' ritirata, MANUALE resta per ORARIO
// e CONSUMO.
export const FONTE_QUANTITA_ATTESA = Object.freeze({
  FISSA: 'FISSA',
  MANUALE: 'MANUALE',
  TIMESHEET: 'TIMESHEET',
  LETTURE: 'LETTURE',
  DURATA: 'DURATA',
})

// Come si addebitano i canoni (`generazione_canone`, CHECK del DB sulle due
// testate e sulle righe; F-7, 2026-10-29): anticipati, all'inizio del periodo,
// o normali, a periodo finito. Sulla riga vuota = «come la testata».
export const GENERAZIONE_CANONE = Object.freeze({
  INIZIO_PERIODO: 'INIZIO_PERIODO',
  FINE_PERIODO: 'FINE_PERIODO',
})

// I due modi del dialog della data documento (`NumerazioneDataDialog`).
// ⭐ Qui e non dentro il componente: `defineProps` non puo' riferire una
//    costante dichiarata nello scope di `<script setup>` (viene issata fuori),
//    e senza un `validator` un refuso nel valore ricadrebbe in SILENZIO sul
//    modo `NUMERA` — la direzione pericolosa, in cui il dialog di creazione
//    pretende una data e annuncia «niente da numerare» su lotti che non
//    esistono ancora.
export const MODO_DATA_DOCUMENTO = Object.freeze({
  // Si sta per numerare: data obbligatoria, e confermare puo' SPOSTARE le date
  // dei documenti (e rigenerarne le scadenze).
  NUMERA: 'numera',
  // Si stanno per creare i lotti: data FACOLTATIVA — vuota vuol dire «la
  // decide la politica del registro», che non e' «oggi».
  CREAZIONE: 'creazione',
})

// Le colonne della testata che `PreventiviForm` MOSTRA, per
// `useTestataDocumento` (brief-db-testata-dopo-emissione, R-FE-3): la testata
// e' modificabile se almeno una di queste e' aperta nella capability.
// ⚠️ Deve dire gli stessi campi del form: lo presidia
// `campiFormTestata.spec.js`. `competenza_mese` e `fatturazione_immediata` non
// ci sono: si scelgono accettando (dialog di accettazione), non dal form.
export const CAMPI_FORM_TESTATA_PREVENTIVO = Object.freeze([
  'emittente_fiscale_id',
  'billing_account_id',
  'istanza_utility_id',
  'utility_id',
  'valuta_id',
  'termine_pagamento_id',
  'validita_dal',
  'validita_al',
])

// Le colonne della testata del contratto che il form cambia DOPO la bozza,
// per `useTestataDocumento`: i tre riferimenti dell'atto (Q1). ⚠️ Scelta di
// interfaccia, dichiarata: `valido_al`, che il DB apre in ATTIVO, si cambia
// dal dialog «Cessa contratto» e non dal form; in bozza il form e' tutto
// aperto e i suoi campi leggono `isLocked` come prima.
export const CAMPI_FORM_TESTATA_CONTRATTO = Object.freeze([
  'codice_cig',
  'codice_cup',
  'codice_commessa',
])
