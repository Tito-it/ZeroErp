// Costanti dominio vendite condivise FE.
// Mantenere allineate con `apps/vendite/services/_approvazioni_prezzo_constants.py`
// (BE) e con i seed DB (`config.stati_doc_preventivi`,
// `config.azioni_processo`).

// Stati di workflow approvazione prezzo applicabili al campo
// `vendite.preventivi_righe.stato_approvazione_prezzo` (ENUM nativo
// `config.stato_approvazione_prezzo`).
export const STATO_APPROVAZIONE = Object.freeze({
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
})

// Codici azione di processo (`config.azioni_processo.permission_codename`).
// Usati con `auth.isActionAllowed(...)` per gating UI lato FE.
export const PRICING_ACTIONS = Object.freeze({
  OVERRIDE: 'prezzo_override_manuale',
  APPROVE: 'approva_prezzo_override',
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
// PreventiviSmistamentoPanel: merce → ordine, servizi → commessa.
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

// Codici origine prezzo del pricing resolver v5 (6 valori, modello unificato
// componenti BoM 2026-05-13). Allineato al CHECK DB su
// `vendite.preventivi_righe_componenti.origine_prezzo` e su
// `vendite.preventivi_righe.origine_prezzo` (quando esteso).
// `LISTINO_BUNDLE`: nuovo STADIO 0 del resolver bundle-aware — prezzo
// componente in contesto padre composito, vince su CATEGORIA standalone.
export const ORIGINE_PREZZO = Object.freeze({
  PROMO: 'PROMO',
  CONTRATTO_OVERRIDE: 'CONTRATTO_OVERRIDE',
  CONTRATTO_LISTINO: 'CONTRATTO_LISTINO',
  CATEGORIA: 'CATEGORIA',
  LISTINO_BUNDLE: 'LISTINO_BUNDLE',
  MANUALE: 'MANUALE',
})

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
