// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ LE ISCRIZIONI DI VENDITE — cio' che il dominio vendite aggiunge ai
//        registri di `core` e dei motori, senza che quelli lo nominino
//        (decisione Tid, 2026-09-26, frontend-standards §«Confini fra
//        domini»). Lo carica `main.js` all'avvio, come ogni `iscrizioni.js`.
//
//        Tre famiglie:
//          · i drawer di DETTAGLIO per tipo di entita' (`core/drawerEntita`):
//            li aprono le tappe dei Passaggi, i cruscotti, i bersagli d'errore;
//          · i contributi alle schermate di altri domini (`core/estensioni`);
//          · le attivita' dei FLUSSI DI PRATICA (i tre registri di `pratiche`):
//            quale drawer apre uno step, quale dialog lo completa.
//
// ⚠️ Ogni componente si iscrive con un import DINAMICO: questo file entra nel
//    bundle d'avvio, i drawer no.
// Note: fino al 2026-09-26 queste voci stavano scritte DENTRO i registri
//       (`vendite/_shared/documenti/documentoDrawers.js`, e i tre di
//       `pratiche/`), e il motore delle pratiche importava vendite.
// ------------------------------------------------------------
import { DOCUMENTO_DRAWER_TIPI as T, iscriviDrawerEntita } from '../core/drawerEntita'
import { MANAGE_ICONS, STATO_PREVENTIVO } from '../core/constants'
import { contribuisci, PUNTI_ESTENSIONE } from '../core/estensioni'
import { iscriviAttivitaUi } from '../pratiche/uiActivityRegistry'
import { iscriviDialogCompletamento } from '../pratiche/flussoCompletionRegistry'
import { iscriviCompletamentoDominio } from '../pratiche/flussoDomainCompletionRegistry'
import { NAV_ICONS } from '../core/navigation'

// ===== Drawer di dettaglio per tipo di entita' =====

iscriviDrawerEntita(T.PREVENTIVO, { load: () => import('./preventivi/components/PreventiviDrawer.vue'), idProp: 'preventivoId', hasMode: true })
iscriviDrawerEntita(T.OFFERTA_COMMERCIALE, { load: () => import('./offerte/components/OffertaDrawer.vue'), idProp: 'offertaId', hasMode: true })
iscriviDrawerEntita(T.ORDINE_VENDITA, { load: () => import('./ordini/components/OrdiniDrawer.vue'), idProp: 'ordineId', hasMode: true })
iscriviDrawerEntita(T.CONTRATTO, { load: () => import('./components/ContrattoDrawer.vue'), idProp: 'contrattoId', hasMode: true })
iscriviDrawerEntita(T.DDT_VENDITA, { load: () => import('./ddt/components/DdtDrawer.vue'), idProp: 'ddtId', hasMode: true })
iscriviDrawerEntita(T.RESO_VENDITA, { load: () => import('./resi/components/ResoDrawer.vue'), idProp: 'resoId' })
// Drawer di CONSULTAZIONE della fattura (2026-07-29): sola lettura per
// costruzione, nessun `mode`. Chiude l'ultimo buco del grafo lineage — le
// tappe FATTURA dei "Passaggi" e le righe dei drill-down diventano apribili.
iscriviDrawerEntita(T.FATTURA, { load: () => import('./components/FatturaDrawer.vue'), idProp: 'fatturaId' })
// Fase C: la commessa non ha lista/CRUD, ma il suo nodo lineage è
// consultabile in un drawer leggero (genealogia inversa). Read-only:
// nessun `mode`.
iscriviDrawerEntita(T.COMMESSA, { load: () => import('./_shared/lineage/CommessaDrawer.vue'), idProp: 'commessaId' })
// Drawer di GESTIONE commessa (lo stesso montato da DashboardCompetenzaView):
// apre le righe COMMESSE del drill-down Backlog, che prima non avevano alcuna
// azione (l'area non ha una view lista). Distinto dal drawer leggero
// `COMMESSA` dei passaggi: qui servono le azioni di governo.
iscriviDrawerEntita(T.COMMESSA_GESTIONE, { load: () => import('./components/CommessaGestioneDrawer.vue'), idProp: 'commessaId' })

// ===== Contributi alle schermate degli altri domini (core/estensioni.js) =====

// I contratti del conto di fatturazione, dal kebab della lista clienti:
// `vendite.contratti` punta a `billing_account`, quindi la lista clienti non
// conosce vendite e la voce arriva da qui.
contribuisci(PUNTI_ESTENSIONE.CLIENTE_AZIONI_RIGA, {
  chiave: 'contratti',
  label: 'vendite.contratti.gestisci_contratti',
  icon: MANAGE_ICONS.CONTRATTI,
  drawer: () => import('./components/ContrattiBillingAccountDrawer.vue'),
  props: (cliente, { t }) => {
    // Un conto CESSATO o CHIUSO non ammette contratti nuovi: il drawer li
    // mostra, ma il «nuovo» e' spento col motivo.
    const stato = (cliente?.stato_codice_interno || '').toUpperCase()
    const chiuso = stato === 'CESSATO' || stato === 'CHIUSO'
    return {
      billingAccountId: cliente.billing_account_id,
      billingAccountLabel: cliente.ragione_sociale_completa || cliente.ba_codice || '',
      billingAccountUtility: cliente.utility_descrizione || '',
      canCreate: !chiuso,
      disabledCreateReason: chiuso ? t('anagrafiche.clienti.ba_chiuso_no_contratti') : '',
    }
  },
})

// ===== Flussi di pratica — attivita' interattive (uiActivityRegistry) =====

// Props comuni per aprire il PreventiviDrawer da un flusso pratica (riuso fra
// APRI_PREVENTIVO e SMISTAMENTO): existingId valorizzato → EDIT dell'esistente,
// null → CREATE con eredita'+lock cliente/istanza dal contesto pratica.
function preventivoDrawerProps(ctx, existingId = null) {
  return {
    mode: existingId ? 'edit' : 'create',
    preventivoId: existingId ?? null,
    praticaId: ctx.praticaId,
    // Contesto cliente ereditato dalla pratica: il drawer pre-compila e blocca
    // BA e istanza. billingAccountId NULL = pratica con la sola istanza (il BA
    // lo risolve il backend dalla coppia istanza+utility).
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

// Risolve l'ordine COLLEGATO della pratica (import lazy dell'API ordini).
function resolveOrdinePerPratica(ctx) {
  return import('./ordini/api/ordiniApi')
    .then(({ getOrdinePerPratica }) => getOrdinePerPratica(ctx.praticaId))
    .then(res => res?.data?.data?.ordine_id ?? null)
    .catch(() => null)
}

iscriviAttivitaUi('APRI_PREVENTIVO', {
  // Loader del drawer di dominio (import dinamico): risolto all'apertura.
  loadComponent: () => import('./preventivi/components/PreventiviDrawer.vue'),
  // Riapertura: risolve il preventivo ROOT gia' agganciato al FLUSSO.
  // Ritorna l'id (→ apre in edit l'esistente) o null (→ create). Import lazy
  // dell'API (questo file sta nel bundle d'avvio). Best-effort:
  // un errore ricade su create senza rischio doppione (il lucchetto unico
  // per-flusso a DB impedisce comunque un secondo ROOT sullo stesso flusso).
  resolveExisting: (ctx) =>
    import('./preventivi/api/preventiviApi')
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
  // lazy dell'API (questo file sta nel bundle d'avvio).
  onSaved: (preventivoId, ctx) =>
    import('./preventivi/api/preventiviApi')
      .then(({ collegaPratica }) => collegaPratica(
        preventivoId, { pratica_id: ctx.praticaId, flusso_id: ctx.flussoId },
      )),
  // Il preventivo nasce anche dalla sola istanza della pratica (il BA della
  // coppia lo risolve il backend) → nessun gating cliente.
  requiresActiveClient: false,
  label: 'pratiche.flusso_apri_preventivo',
  icon: NAV_ICONS.PREVENTIVI,
  // Toast i18n al primo aggancio documento↔pratica.
  linkedMessage: 'pratiche.preventivo_collegato',
})

iscriviAttivitaUi('SMISTAMENTO', {
  // Apre lo STESSO drawer preventivo, ma sul ROOT della PRATICA (lo step
  // SMISTAMENTO e' a valle: il preventivo e' agganciato al flusso
  // PREVENTIVAZIONE, non a questo). In stato ACCETTATO il drawer mostra il
  // Pannello Smistamento (selezione righe → ordine/commessa), uniforme allo
  // standalone. Niente onSaved: il ROOT e' gia' agganciato a monte.
  loadComponent: () => import('./preventivi/components/PreventiviDrawer.vue'),
  // ROOT per-pratica (non per-flusso): il preventivo lo ha agganciato il
  // flusso PREVENTIVAZIONE. Best-effort: errore → null (drawer in create, ma
  // non dovrebbe accadere a questo punto del percorso).
  resolveExisting: (ctx) =>
    import('./preventivi/api/preventiviApi')
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
  icon: MANAGE_ICONS.INVIA_A_COMMESSA,
})

// Step a valle merce: aprono l'OrdiniDrawer sull'ordine COLLEGATO della pratica
// (creato dallo smistamento, agganciato da PostSmistamentoHandler). Stesso
// drawer per entrambi, ad azioni diverse secondo lo stato dell'ordine:
//   CONFERMA_ORDINE → Emetti (DRAFT→CONFERMATO);
//   INVIO_COMMESSA  → Push a commessa (CONFERMATO→EVASO).
// requiresExisting: l'ordine DEVE esistere → niente fallback create.
iscriviAttivitaUi('CONFERMA_ORDINE', {
  loadComponent: () => import('./ordini/components/OrdiniDrawer.vue'),
  resolveExisting: resolveOrdinePerPratica,
  buildProps: ordineDrawerProps,
  requiresExisting: true,
  label: 'pratiche.flusso_conferma_ordine',
  icon: NAV_ICONS.ORDINI,
})

iscriviAttivitaUi('INVIO_COMMESSA', {
  loadComponent: () => import('./ordini/components/OrdiniDrawer.vue'),
  resolveExisting: resolveOrdinePerPratica,
  buildProps: ordineDrawerProps,
  requiresExisting: true,
  label: 'pratiche.flusso_invio_commessa',
  icon: MANAGE_ICONS.INVIA_A_COMMESSA,
})

// APRI_OFFERTA / APRI_CONTRATTO: da aggiungere quando nasceranno i loro
// template_flussi (oggi non esistono → nessun seed DB li referenzia). Stessa
// forma; `requiresActiveClient: true` (BA obbligatorio) e onSaved sul rispettivo
// endpoint collega-pratica.

// ===== Flussi di pratica — dialog di completamento (flussoCompletionRegistry) =====

// GUIDA (D4): mappa esito operatore → transizione del DOCUMENTO (preventivo).
// Const di modulo (niente auto-riferimento fragile al registry): usata sia da
// `esitoToStato` (restrizione picker) sia da `docAction` (chiamata). Stati dal
// catalogo `STATO_PREVENTIVO` (no literal hardcoded).
const APPROVAZIONE_ESITO_STATO = {
  POSITIVO: STATO_PREVENTIVO.ACCETTATO,
  NEGATIVO: STATO_PREVENTIVO.RIFIUTATO,
}

iscriviDialogCompletamento('APPROVAZIONE_CLIENTE', {
  // Mostra la dialog solo se l'operatore sceglie questo esito (l'accettazione
  // avviene su POSITIVO; su esito negativo si completa senza dati di processo).
  esitoRichiesto: 'POSITIVO',
  // Import dinamico del dialog (questo file sta nel bundle d'avvio).
  loadComponent: () =>
    import('./preventivi/components/dialogs/PreventivoAccettazioneDialog.vue'),
  // GUIDA (D4): step PROJECTION-DRIVEN. L'azione non completa il flusso: agisce
  // sul DOCUMENTO (preventivo standalone) e il milestone avanza da solo via
  // trigger DB `fn_reconcile_sorgente`. `esitoToStato` mappa l'esito operatore
  // alla transizione del preventivo; `docAction` esegue la chiamata (import
  // LAZY, come ogni voce di questo file). Restituisce la
  // Promise axios (compatibile con useApiHandler.execute).
  esitoToStato: APPROVAZIONE_ESITO_STATO,
  docAction: async ({ praticaId, esito, meta }) => {
    const nuovoStato = APPROVAZIONE_ESITO_STATO[esito]
    if (!nuovoStato) return null
    const { cambiaStatoPreventivoDaPratica } = await import(
      './preventivi/api/preventiviApi'
    )
    return cambiaStatoPreventivoDaPratica(praticaId, { nuovo_stato: nuovoStato, ...meta })
  },
})

// OFFERTA/CONTRATTO: iscrivere qui quando i loro flussi di accettazione
// richiederanno dati di processo. Stessa forma.

// ===== Flussi di pratica — completamento guidato dal dominio (flussoDomainCompletionRegistry) =====

iscriviCompletamentoDominio('SMISTAMENTO', {
  label: 'pratiche.flusso_completa_smistamento',
  // Lo step SMISTAMENTO opera sul preventivo ROOT agganciato a monte
  // (PREVENTIVAZIONE): risolviamo l'id e completiamo. Il BE calcola l'esito di
  // ramo (MERCE_PRESENTE ⟺ e' nato un ordine) e rifiuta se restano righe non
  // smistate (residuo merce/servizi) con errore parlante.
  complete: async ({ praticaId }) => {
    const { getRootPerPratica, completaSmistamento } = await import(
      './preventivi/api/preventiviApi'
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
})
