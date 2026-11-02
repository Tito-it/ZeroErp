// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: la MACCHINA del form inline (frontend-standards §«Pattern
//        Master-Detail inline»): un elenco sopra, il form di una sua voce
//        sotto, nello stesso contenitore. Possiede lo stato del form —
//        `formMode` null/'create'/'edit' e la riga in modifica — e le sue
//        regole: si apre «Nuova riga», si apre una riga solo se le righe si
//        scrivono, si chiude, e si CHIUDE DA SOLO al cambio di padre.
//        ⭐ SEDE UNICA di questa macchina (regola del 2, ok Tid 2026-09-28).
//        Nata in L1 del brief-db-liste-righe-documento come
//        `useRigheMasterDetail`; la verifica critica dello stesso giorno ha
//        trovato la stessa logica in due BB di dominio e in sette drawer.
//        Rinominata qui perche' non serve solo alle righe di un documento.
//        La usano, oltre ai contenitori diretti, i BB che ci costruiscono
//        sopra il loro mestiere: `useEditableCollection` (salva, elimina,
//        attivo) e `useSoggettoRuoloCollection` (caricamento soggetto/ruolo,
//        salvataggio, fotografia del form).
//
// ⭐ E' UN COMPOSABLE, NON UN COMPONENTE, e la ragione e' dove vive lo stato.
//    Il contenitore legge `formAperto` in piu' punti che l'elenco non
//    raggiunge: le azioni della barra (spente a form aperto), il `FormFooter`
//    (sparisce in form mode, regola 12 del pattern), la ricarica dopo un
//    gesto. E l'elenco lo monta il contenitore (`useDrawerTabLista`), i cui
//    valori servono agli slot dei filtri scritti da lui.
//
// ⛔ E' UNA FACTORY: ogni chiamata ha il suo stato. Due drawer aperti insieme
//    non si scrivono addosso il form (`feedback_estrarre_non_condividere_stato`).
//
// ⭐ IL CAMBIO DI PADRE CHIUDE IL FORM. Un drawer non si smonta quando si
//    apre un altro documento: cambia la prop. Senza questa regola il form
//    resterebbe aperto sulla riga del documento PRECEDENTE, e «Salva»
//    scriverebbe col padre nuovo — un difetto che non fallisce.
//
// ⭐ APRIRE IL FORM LO PORTA DAVANTI (2026-10-07, decisione di Tid). Il form
//    inline sta SOTTO l'elenco: su un elenco lungo il clic su una riga apriva
//    il form fuori vista, e sembrava non succedere nulla. Il contenitore lega
//    `ancoraForm` al primo elemento del form (`:ref="ancoraForm"`), e il BB lo
//    fa scorrere in vista a ogni apertura. ⛔ Solo dentro `nuovaRiga` e
//    `apriRiga`, cioe' dopo un GESTO: mai all'apertura del drawer, alla
//    chiusura o alla `risincronizza` (la pagina scenderebbe da sola mentre
//    l'operatore guarda altro — la stessa regola di `selezionaStadio` nella
//    dashboard di competenza). Senza ancora legata: non scorre, e basta.
//
// ⛔ I verbi che AGGIUNGONO qualcosa alla macchina (azzerare errori, popolare
//    il form, salvare) stanno nel BB o nel contenitore che li possiede, e
//    chiamano questi. Non si ricopia `formMode = 'edit'` altrove.
//
// Uso tipico:
//   const righe = useFormInline({
//     padre: () => (props.visible ? props.documentoId : null),
//     puoModificare: () => !isReadonly.value,
//   })
//   // barra della lista:
//   extraActions: () => [righe.azioneNuovaRiga({ label: t('...nuova') })]
//   // lista:   @row-click="righe.apriRiga"
//   // form:    <RigaForm v-if="righe.formAperto.value" :ref="righe.ancoraForm"
//   //                    :riga="righe.rigaInModifica.value" @annulla="righe.chiudiForm" />
//   // footer:  <FormFooter v-if="!righe.formAperto.value" close-only ... />

import { computed, nextTick, ref, toValue, watch } from 'vue'
import { MANAGE_ICONS } from '../constants'

// `Node.TEXT_NODE`, scritto a mano: il BB non legge globali del DOM al caricamento.
const TEXT_NODE = 3

export function useFormInline({
  // Getter dell'identita' del documento. Al suo cambio il form si chiude.
  // Il drawer ci mette dentro anche la visibilita' (`visible ? id : null`),
  // cosi' la chiusura del drawer lascia il form chiuso alla riapertura.
  padre = null,
  // Getter: le righe si scrivono? Governa il click sulla riga (che apre la
  // modifica). ⚠️ Non tocca «Nuova riga»: quella ha la sua condizione
  // (`azioneNuovaRiga({ visible })`), che spesso e' piu' stretta.
  puoModificare = () => true,
  // ⭐ CAMBIARE RIGA COL FORM MODIFICATO CHIEDE (2026-10-03, D-8 di
  //    work-done/analisi-fe-chrome-drawer.md, decisione di Tid). Fino a
  //    quel giorno il clic su un'altra riga sostituiva il form aperto, e le
  //    modifiche alla riga precedente si perdevano senza domanda.
  //    `confermaCambio(procedi)` e' di solito il `chiudiConConferma` della
  //    fotografia del form inline (useDrawerFormPreserve): chiede solo se c'e'
  //    davvero qualcosa da perdere. Senza, si cambia e basta (com'era).
  // ⚠️ Passarla come freccia, `(p) => fotografia.chiudiConConferma(p)`: la
  //    fotografia nasce di solito DOPO questo BB (la sua visibilita' legge
  //    `formAperto`), e la freccia la legge solo al clic.
  confermaCambio = null,
} = {}) {
  // `null` = nessun form · `'create'` · `'edit'`.
  const formMode = ref(null)
  const rigaInModifica = ref(null)
  const formAperto = computed(() => formMode.value !== null)

  // L'elemento del form, legato dal contenitore con `:ref="ancoraForm"`.
  // ⭐ Una ref-FUNZIONE, non una `ref()`: si lega uguale da `righe.ancoraForm`
  //    o destrutturata, e accetta sia un elemento sia un componente (`$el`).
  //    Non e' reattiva perche' nessuno la legge in un render.
  let nodoForm = null
  function ancoraForm(el) {
    nodoForm = el?.$el ?? el ?? null
  }

  // Scopo: l'elemento da portare in vista. ⚠️ Un componente MULTI-RADICE
  //    (Fragment: `DistintaRigaForm`, `DocumentoInternoRigaForm`) ha come `$el`
  //    l'ancora di TESTO vuota che apre il frammento, senza `scrollIntoView`:
  //    lo scorrimento taceva. Il primo elemento vero e' quello che la segue.
  //    Risolto al momento dello scorrimento, a DOM montato.
  function elementoForm() {
    return nodoForm?.nodeType === TEXT_NODE ? nodoForm.nextElementSibling : nodoForm
  }

  // Scopo: porta il form in vista dopo che il DOM l'ha montato (`v-if`).
  function scorriAlForm() {
    nextTick(() => {
      elementoForm()?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    })
  }

  // Scopo: apre il form vuoto per una riga nuova.
  function nuovaRiga() {
    rigaInModifica.value = null
    formMode.value = 'create'
    scorriAlForm()
  }

  // Scopo: apre la riga in modifica — solo se le righe si scrivono. Su un
  //        documento fermo il click non apre un form che il database
  //        rifiuterebbe.
  // ⭐ Riceve la RIGA, non l'evento PrimeVue: e' la firma di `row-click` di
  //    `ListaConfigurabile` / `DrawerTabLista`.
  // ⭐ `poi(riga)`: cio' che il contenitore fa ad apertura avvenuta (popolare il
  //    form, fissare la fotografia). ⛔ Va passato qui e non scritto DOPO la
  //    chiamata: con la conferma l'apertura puo' arrivare piu' tardi, o mai, e
  //    un form riempito subito butterebbe le modifiche prima della risposta.
  function apriRiga(riga, poi = null) {
    if (!riga || !toValue(puoModificare)) return
    const apri = () => {
      rigaInModifica.value = riga
      formMode.value = 'edit'
      poi?.(riga)
      scorriAlForm()
    }
    if (formAperto.value && confermaCambio) confermaCambio(apri)
    else apri()
  }

  // Scopo: chiude il form e dimentica la riga.
  function chiudiForm() {
    formMode.value = null
    rigaInModifica.value = null
  }

  // Scopo: dopo una ricarica delle righe a form APERTO in modifica, rimette
  //        nel form la versione fresca della stessa riga (per `id`). Serve
  //        quando un gesto dentro il form cambia la riga senza chiuderlo (un
  //        componente BoM che ne ricalcola il prezzo).
  // ⚠️ Se la riga non c'e' piu' nelle righe lette, il form resta com'e': la
  //    lista paginata puo' non contenerla, e chiudere il form perderebbe cio'
  //    che l'operatore sta scrivendo.
  function risincronizza(righe) {
    if (formMode.value !== 'edit' || rigaInModifica.value?.id == null) return
    const fresca = (righe || []).find((r) => r.id === rigaInModifica.value.id)
    if (fresca) rigaInModifica.value = fresca
  }

  // Scopo: l'azione «Nuova riga» per la barra della lista (`PageActionsBar`).
  // ⭐ Sparisce a form aperto: un secondo «Nuova riga» mentre si scrive una
  //    riga butterebbe via cio' che e' scritto, senza chiedere. E' la regola
  //    che due copie su tre avevano gia'.
  // ⚠️ `command` e' per il contenitore che all'apertura fa ANCHE altro
  //    (azzera il suo form, fissa la fotografia, precompila): il suo verbo
  //    deve chiamare `nuovaRiga()`, non riscrivere `formMode`.
  // ⭐ Chiave `new`, quella del «Nuovo» di ogni barra: e' la chiave che la
  //    scorciatoia F6 cerca (`useScorciatoie`, 2026-10-04). Fino a quel
  //    giorno era `nuova-riga`, e altre sedi avevano `nuova`/`new-uom`/…:
  //    stesso significato, cinque nomi.
  function azioneNuovaRiga({
    key = 'new',
    label,
    tooltip,
    icon = MANAGE_ICONS.ADD,
    visible = () => true,
    command = nuovaRiga,
  } = {}) {
    return {
      key,
      kind: 'primary',
      label,
      tooltip,
      icon,
      hideWhenReadonly: true,
      visible: toValue(visible) !== false && !formAperto.value,
      command,
    }
  }

  if (padre != null) watch(padre, chiudiForm)

  return {
    formMode,
    rigaInModifica,
    formAperto,
    ancoraForm,
    nuovaRiga,
    apriRiga,
    chiudiForm,
    risincronizza,
    azioneNuovaRiga,
  }
}
