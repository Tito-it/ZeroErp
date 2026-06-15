// Scopo: registry FE delle attività UI lanciabili da un flusso di pratica.
// Specchio frontend di pratiche.handler_flussi/HANDLER_MAP (automazione server),
// qui per le attività INTERATTIVE: una chiave `azione_ui_key` (catalogo DB
// pratiche.azioni_ui, esposta sul flusso come `template_azione_ui_key`) risolve
// al drawer di dominio da aprire dal flusso, ai campi che eredita/blocca dal
// contesto pratica e al gancio post-salvataggio.
//
// Aggiungere un documento = aggiungere una voce qui + seedare la chiave sul
// template DB. Nessun `if` per tipo_prestazione nel codice: l'asimmetria tra
// documenti (chi richiede il cliente attivo, cosa blocca) vive nei DATI di
// questa mappa. Import del componente LAZY (loadComponent → import dinamico) per
// non accoppiare il modulo pratiche ai domini (vendite, ...). L'host attende la
// risoluzione PRIMA di montare/mostrare il drawer, così il suo watch(visible)
// (non immediate) scatta sulla transizione false→true (vedi PraticheDashboard).

export const UI_ACTIVITY_REGISTRY = {
  APRI_PREVENTIVO: {
    // Loader del drawer di dominio (import dinamico): risolto all'apertura.
    loadComponent: () => import('../vendite/preventivi/components/PreventiviDrawer.vue'),
    // Props passate al drawer, costruite dal contesto pratica.
    buildProps: (ctx) => ({
      mode: 'create',
      praticaId: ctx.praticaId,
      // Contesto cliente ereditato dalla pratica: il drawer pre-compila e blocca
      // istanza (+ BA se cliente attivo). billingAccountId NULL = prospect.
      praticaContext: {
        billingAccountId: ctx.billingAccountId ?? null,
        istanzaUtilityId: ctx.istanzaUtilityId ?? null,
      },
    }),
    // Gancio post-salvataggio: aggancia il documento alla pratica come ROOT.
    // Ritorna la RESPONSE axios di collegaPratica (l'host la passa a
    // useApiHandler.execute → toast/errore uniformi). Import lazy dell'API di
    // dominio (coerente con la cautela di accoppiamento). L'host garantisce
    // result.id valorizzato prima di chiamare.
    onSaved: (result, ctx) =>
      import('../vendite/preventivi/api/preventiviApi')
        .then(({ collegaPratica }) => collegaPratica(result.id, { pratica_id: ctx.praticaId })),
    // Il preventivo ammette il prospect (BA opzionale) → nessun gating cliente.
    requiresActiveClient: false,
    label: 'pratiche.flusso_apri_preventivo',
    icon: 'pi pi-file-edit',
    // Toast i18n al primo aggancio documento↔pratica.
    linkedMessage: 'pratiche.preventivo_collegato',
  },
  // APRI_OFFERTA / APRI_CONTRATTO: da aggiungere quando nasceranno i loro
  // template_flussi (oggi non esistono → nessun seed DB li referenzia). Stessa
  // forma; `requiresActiveClient: true` (BA obbligatorio) e onSaved sul rispettivo
  // endpoint collega-pratica. Gli ORDINI restano fuori (push a valle, non drawer).
}

// Scopo: risolve la voce registry da una chiave `azione_ui_key`; null se assente
// o non registrata (fail-safe: nessun pulsante invece di un errore).
export function getUiActivity(key) {
  return key ? (UI_ACTIVITY_REGISTRY[key] ?? null) : null
}
