// Scopo: registry FE degli step il cui COMPLETAMENTO e' guidato dal DOMINIO —
// l'esito e' CALCOLATO dal backend (bivio), non scelto dall'operatore. Per questi
// step il FlussoDrawer SOPPRIME il picker esito e offre una singola azione che
// chiama l'endpoint di dominio: il BE calcola l'esito di RAMO, verifica gli
// invarianti e completa lo step nella stessa transazione.
//
// Differenza da flussoCompletionRegistry: la', l'esito resta un verdetto scelto
// dall'operatore e la dialog raccoglie solo dati di processo (meta). Qui l'esito
// stesso non e' scelto: e' un bivio calcolato (es. SMISTAMENTO →
// MERCE_PRESENTE/SOLO_SERVIZI, che decide se attivare i flussi merce 9013/9014).
//
// Tenere FlussoDrawer GENERICO: nessun `if` per codice/dominio nel componente;
// l'accoppiamento ai domini (vendite, ...) vive QUI come dato + import LAZY.
//
// Contratto voce:
//   label:    chiave i18n del bottone di completamento;
//   complete: async ({ praticaId, flusso }) => Promise<AxiosResponse> — esegue il
//             completamento di dominio. L'host la avvolge in useApiHandler.execute,
//             quindi DEVE risolvere in una response axios (envelope { data }); un
//             throw viene gestito da execute come errore (toast + null).

export const FLUSSO_DOMAIN_COMPLETION_REGISTRY = {
  SMISTAMENTO: {
    label: 'pratiche.flusso_completa_smistamento',
    // Lo step SMISTAMENTO opera sul preventivo ROOT agganciato a monte
    // (PREVENTIVAZIONE): risolviamo l'id e completiamo. Il BE calcola l'esito di
    // ramo (MERCE_PRESENTE ⟺ e' nato un ordine) e rifiuta se restano righe non
    // smistate (residuo merce/servizi) con errore parlante.
    complete: async ({ praticaId }) => {
      const { getRootPerPratica, completaSmistamento } = await import(
        '../vendite/preventivi/api/preventiviApi'
      )
      const res = await getRootPerPratica(praticaId)
      const preventivoId = res?.data?.data?.preventivo_id
      // ROOT non risolto: non dovrebbe accadere a questo punto del percorso (il
      // preventivo e' agganciato da PREVENTIVAZIONE). Throw → execute mostra il
      // fallback errorMessage e non completa (niente completamento cieco).
      if (!preventivoId) {
        throw new Error('E_PREVENTIVO_ROOT_NON_RISOLTO')
      }
      return completaSmistamento(preventivoId)
    },
  },
}

// Scopo: risolve la voce registry dal `template_flusso_codice`; null se assente
// (fail-safe: lo step usa il completamento generico con picker esito).
export function getDomainCompletion(codice) {
  return codice ? (FLUSSO_DOMAIN_COMPLETION_REGISTRY[codice] ?? null) : null
}
