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

// Props comuni per aprire il PreventiviDrawer da un flusso pratica (riuso fra
// APRI_PREVENTIVO e SMISTAMENTO): existingId valorizzato → EDIT dell'esistente,
// null → CREATE con eredita'+lock cliente/istanza dal contesto pratica.
function preventivoDrawerProps(ctx, existingId = null) {
  return {
    mode: existingId ? 'edit' : 'create',
    preventivoId: existingId ?? null,
    praticaId: ctx.praticaId,
    // Contesto cliente ereditato dalla pratica: il drawer pre-compila e blocca
    // istanza (+ BA se cliente attivo). billingAccountId NULL = prospect.
    praticaContext: {
      billingAccountId: ctx.billingAccountId ?? null,
      istanzaUtilityId: ctx.istanzaUtilityId ?? null,
    },
  }
}

// Props per aprire l'OrdiniDrawer da un flusso pratica a valle (CONFERMA_ORDINE,
// INVIO_COMMESSA): l'ordine esiste gia' (agganciato dallo smistamento) → sempre EDIT.
function ordineDrawerProps(_ctx, existingId = null) {
  return { mode: 'edit', ordineId: existingId ?? null }
}

// Risolve l'ordine COLLEGATO della pratica (import lazy del dominio vendite).
function resolveOrdinePerPratica(ctx) {
  return import('../vendite/ordini/api/ordiniApi')
    .then(({ getOrdinePerPratica }) => getOrdinePerPratica(ctx.praticaId))
    .then(res => res?.data?.data?.ordine_id ?? null)
    .catch(() => null)
}

export const UI_ACTIVITY_REGISTRY = {
  APRI_PREVENTIVO: {
    // Loader del drawer di dominio (import dinamico): risolto all'apertura.
    loadComponent: () => import('../vendite/preventivi/components/PreventiviDrawer.vue'),
    // Riapertura: risolve il preventivo ROOT gia' agganciato al FLUSSO.
    // Ritorna l'id (→ apre in edit l'esistente) o null (→ create). Import lazy
    // dell'API di dominio, coerente con la cautela di accoppiamento. Best-effort:
    // un errore ricade su create senza rischio doppione (il lucchetto unico
    // per-flusso a DB impedisce comunque un secondo ROOT sullo stesso flusso).
    resolveExisting: (ctx) =>
      import('../vendite/preventivi/api/preventiviApi')
        .then(({ getRootPerFlusso }) => getRootPerFlusso(ctx.flussoId))
        .then(res => res?.data?.data?.preventivo_id ?? null)
        .catch(() => null),
    // Props passate al drawer (helper condiviso, vedi preventivoDrawerProps).
    buildProps: preventivoDrawerProps,
    // Estrae l'id preventivo dalle forme ETEROGENEE dell'evento 'saved' del
    // drawer (l'id non e' in una posizione fissa):
    //   create   → { id, ... }
    //   update   → { status, preventivo_id }
    //   emissione→ { preventivo: { preventivo_id, ... }, documento }
    //   cambio   → { preventivo_id, stato_precedente, stato_nuovo }
    // Senza questa normalizzazione il collegamento si reggeva solo sul ramo
    // create (l'unico con `.id`) → rotto da quando l'auto-save bozza manda il
    // salvataggio sul ramo update.
    savedId: (result) =>
      result?.id
      ?? result?.preventivo_id
      ?? result?.preventivo?.preventivo_id
      ?? result?.preventivo?.id
      ?? null,
    // Gancio post-salvataggio: aggancia il documento al flusso (ROOT). Riceve
    // l'id gia' risolto (vedi savedId). Ritorna la RESPONSE axios di collegaPratica
    // (l'host la passa a useApiHandler.execute → toast/errore uniformi). Import
    // lazy dell'API di dominio (coerente con la cautela di accoppiamento).
    onSaved: (preventivoId, ctx) =>
      import('../vendite/preventivi/api/preventiviApi')
        .then(({ collegaPratica }) => collegaPratica(
          preventivoId, { pratica_id: ctx.praticaId, flusso_id: ctx.flussoId },
        )),
    // Il preventivo ammette il prospect (BA opzionale) → nessun gating cliente.
    requiresActiveClient: false,
    label: 'pratiche.flusso_apri_preventivo',
    icon: 'pi pi-file-edit',
    // Toast i18n al primo aggancio documento↔pratica.
    linkedMessage: 'pratiche.preventivo_collegato',
  },
  SMISTAMENTO: {
    // Apre lo STESSO drawer preventivo, ma sul ROOT della PRATICA (lo step
    // SMISTAMENTO e' a valle: il preventivo e' agganciato al flusso
    // PREVENTIVAZIONE, non a questo). In stato ACCETTATO il drawer mostra il
    // Pannello Smistamento (selezione righe → ordine/commessa), uniforme allo
    // standalone. Niente onSaved: il ROOT e' gia' agganciato a monte.
    loadComponent: () => import('../vendite/preventivi/components/PreventiviDrawer.vue'),
    // ROOT per-pratica (non per-flusso): il preventivo lo ha agganciato il
    // flusso PREVENTIVAZIONE. Best-effort: errore → null (drawer in create, ma
    // non dovrebbe accadere a questo punto del percorso).
    resolveExisting: (ctx) =>
      import('../vendite/preventivi/api/preventiviApi')
        .then(({ getRootPerPratica }) => getRootPerPratica(ctx.praticaId))
        .then(res => res?.data?.data?.preventivo_id ?? null)
        .catch(() => null),
    buildProps: preventivoDrawerProps,
    requiresActiveClient: false,
    // Lo step e' a valle: il preventivo DEVE gia' esistere. Se il ROOT non si
    // risolve (errore/assente) NON si apre il drawer in create (eviterebbe un
    // preventivo orfano): l'host blocca con errore parlante.
    requiresExisting: true,
    label: 'pratiche.flusso_smistamento',
    icon: 'pi pi-send',
  },
  // Step a valle merce: aprono l'OrdiniDrawer sull'ordine COLLEGATO della pratica
  // (creato dallo smistamento, agganciato da PostSmistamentoHandler). Stesso
  // drawer per entrambi, ad azioni diverse secondo lo stato dell'ordine:
  //   CONFERMA_ORDINE → Emetti (DRAFT→CONFERMATO);
  //   INVIO_COMMESSA  → Push a commessa (CONFERMATO→EVASO).
  // requiresExisting: l'ordine DEVE esistere → niente fallback create.
  CONFERMA_ORDINE: {
    loadComponent: () => import('../vendite/ordini/components/OrdiniDrawer.vue'),
    resolveExisting: resolveOrdinePerPratica,
    buildProps: ordineDrawerProps,
    requiresExisting: true,
    label: 'pratiche.flusso_conferma_ordine',
    icon: 'pi pi-check-square',
  },
  INVIO_COMMESSA: {
    loadComponent: () => import('../vendite/ordini/components/OrdiniDrawer.vue'),
    resolveExisting: resolveOrdinePerPratica,
    buildProps: ordineDrawerProps,
    requiresExisting: true,
    label: 'pratiche.flusso_invio_commessa',
    icon: 'pi pi-send',
  },
  // APRI_OFFERTA / APRI_CONTRATTO: da aggiungere quando nasceranno i loro
  // template_flussi (oggi non esistono → nessun seed DB li referenzia). Stessa
  // forma; `requiresActiveClient: true` (BA obbligatorio) e onSaved sul rispettivo
  // endpoint collega-pratica.
}

// Scopo: risolve la voce registry da una chiave `azione_ui_key`; null se assente
// o non registrata (fail-safe: nessun pulsante invece di un errore).
export function getUiActivity(key) {
  return key ? (UI_ACTIVITY_REGISTRY[key] ?? null) : null
}
