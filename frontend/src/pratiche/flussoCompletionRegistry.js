// Scopo: registry FE delle DIALOG DI COMPLETAMENTO di un flusso di pratica.
// Gemello di uiActivityRegistry, ma per il momento "completa flusso": alcuni
// step richiedono dati di processo all'esito (es. APPROVAZIONE_CLIENTE su
// POSITIVO richiede modalita'+competenza di fatturazione, che l'accettazione
// del preventivo persiste). La chiave e' il `template_flusso_codice` esposto sul
// flusso; il valore dichiara quale dialog aprire e per quale esito.
//
// Tenere FlussoDrawer GENERICO: nessun `if` per codice/dominio nel componente,
// l'accoppiamento ai domini (vendite, ...) vive QUI come dato + import LAZY.
// Il dialog deve: accettare v-model:visible, emettere `confirm` con un payload
// gia' BE-ready, che l'host inoltra come `meta` del completamento flusso.

import { STATO_PREVENTIVO } from '../core/constants'

// GUIDA (D4): mappa esito operatore → transizione del DOCUMENTO (preventivo).
// Const di modulo (niente auto-riferimento fragile al registry): usata sia da
// `esitoToStato` (restrizione picker) sia da `docAction` (chiamata). Stati dal
// catalogo `STATO_PREVENTIVO` (no literal hardcoded).
const APPROVAZIONE_ESITO_STATO = {
  POSITIVO: STATO_PREVENTIVO.ACCETTATO,
  NEGATIVO: STATO_PREVENTIVO.RIFIUTATO,
}

export const FLUSSO_COMPLETION_REGISTRY = {
  APPROVAZIONE_CLIENTE: {
    // Mostra la dialog solo se l'operatore sceglie questo esito (l'accettazione
    // avviene su POSITIVO; su esito negativo si completa senza dati di processo).
    esitoRichiesto: 'POSITIVO',
    // Import dinamico del dialog di dominio (no accoppiamento statico pratiche→vendite).
    loadComponent: () =>
      import('../vendite/preventivi/components/dialogs/PreventivoAccettazioneDialog.vue'),
    // GUIDA (D4): step PROJECTION-DRIVEN. L'azione non completa il flusso: agisce
    // sul DOCUMENTO (preventivo standalone) e il milestone avanza da solo via
    // trigger DB `fn_reconcile_sorgente`. `esitoToStato` mappa l'esito operatore
    // alla transizione del preventivo; `docAction` esegue la chiamata (import
    // LAZY per non accoppiare staticamente pratiche→vendite). Restituisce la
    // Promise axios (compatibile con useApiHandler.execute).
    esitoToStato: APPROVAZIONE_ESITO_STATO,
    docAction: async ({ praticaId, esito, meta }) => {
      const nuovoStato = APPROVAZIONE_ESITO_STATO[esito]
      if (!nuovoStato) return null
      const { cambiaStatoPreventivoDaPratica } = await import(
        '../vendite/preventivi/api/preventiviApi'
      )
      return cambiaStatoPreventivoDaPratica(praticaId, { nuovo_stato: nuovoStato, ...(meta || {}) })
    },
  },
  // OFFERTA/CONTRATTO: aggiungere qui quando i loro flussi di accettazione
  // richiederanno dati di processo. Stessa forma.
}

// Scopo: risolve la voce registry dal `template_flusso_codice`; null se assente
// (fail-safe: completamento generico senza dialog).
export function getCompletionDialog(codice) {
  return codice ? (FLUSSO_COMPLETION_REGISTRY[codice] ?? null) : null
}
