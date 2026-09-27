// Costanti dominio vendite condivise FE.
// Mantenere allineate con `apps/vendite/services/_approvazioni_prezzo_constants.py`
// (BE) e con i seed DB (`config.stati_doc_preventivi`,
// `config.azioni_processo`).

import { aspettoAzione } from '../core/aspettoAzioni'

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
export const DESTINAZIONE_SMISTAMENTO = Object.freeze({
  ORDINE: 'ORDINE',
  COMMESSA: 'COMMESSA',
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
// terminato (data fine raggiunta o cessazione manuale anticipata).
export const STATO_CONTRATTO = Object.freeze({
  DRAFT: 'DRAFT',
  ATTIVO: 'ATTIVO',
  CESSATO: 'CESSATO',
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
export const TIPO_ECCEZIONE = Object.freeze({
  OVERRIDE: 'OVERRIDE',
  ESCLUSIONE: 'ESCLUSIONE',
  AGGIUNTA: 'AGGIUNTA',
  DA_LISTINO: 'DA_LISTINO',
})

// Tipi erogazione su `vendite.contratti_righe.tipo_erogazione` (CHECK DB
// `chk_contrighe_tipo_erog`). `ORARIO` modellato ma non ancora esposto
// in UI (modulo timesheet futuro).
export const TIPO_EROGAZIONE = Object.freeze({
  CANONE: 'CANONE',
  UNA_TANTUM: 'UNA_TANTUM',
  ORARIO: 'ORARIO',
  CONSUMO: 'CONSUMO',
})

// Fonti quantita su `vendite.contratti_righe.fonte_quantita_attesa`
// (CHECK DB `chk_contrighe_fonte_qta`, NOT NULL dal 2026-05-19 via
// migration 20260519-05). Coerenza con la matrice
// `tipo_erogazione x fonte_quantita_attesa` vincolata dal CHECK
// `chk_contrighe_coerenza_fonte_erogazione` (migration 20260519-05):
// 7 combinazioni vietate, vedi `_FONTE_VIETATE_PER_TIPO_EROGAZIONE`
// in `apps/vendite/services/contratti_service.py` e il piano
// `docs/it/dev/work-done/refactor-contratti-fonte-quantita.md` §3.
export const FONTE_QUANTITA_ATTESA = Object.freeze({
  FISSA: 'FISSA',
  MANUALE: 'MANUALE',
  TIMESHEET: 'TIMESHEET',
  LETTURE: 'LETTURE',
  DERIVATA_COMPONENTI: 'DERIVATA_COMPONENTI',
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
