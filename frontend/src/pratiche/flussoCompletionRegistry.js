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

export const FLUSSO_COMPLETION_REGISTRY = {
  APPROVAZIONE_CLIENTE: {
    // Mostra la dialog solo se l'operatore sceglie questo esito (l'accettazione
    // avviene su POSITIVO; su esito negativo si completa senza dati di processo).
    esitoRichiesto: 'POSITIVO',
    // Import dinamico del dialog di dominio (no accoppiamento statico pratiche→vendite).
    loadComponent: () =>
      import('../vendite/preventivi/components/dialogs/PreventivoAccettazioneDialog.vue'),
  },
  // OFFERTA/CONTRATTO: aggiungere qui quando i loro flussi di accettazione
  // richiederanno dati di processo. Stessa forma.
}

// Scopo: risolve la voce registry dal `template_flusso_codice`; null se assente
// (fail-safe: completamento generico senza dialog).
export function getCompletionDialog(codice) {
  return codice ? (FLUSSO_COMPLETION_REGISTRY[codice] ?? null) : null
}
