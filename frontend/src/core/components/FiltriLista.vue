<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: i FILTRI di una lista — in linea su desktop, in un drawer dal basso
//        in modalita' compatta, con il segno di quanti ne sono attivi.
//        Building block unico: una lista non scrive piu' `app-page-filters` a
//        mano (decisione di Tid, 2026-09-22).
//
// ⭐ LA REGOLA: un filtro e' STATO DELLA LISTA, non decorazione della view.
//    Ne discende che *dove* i filtri si rendono — e il segno che sono attivi —
//    appartengono al building block della lista, come il paginator, il ritiro
//    delle colonne e le azioni di testata.
//
// Uso:
//   <FiltriLista :store="store" :inert="perimetroBloccato">
//     <template #sempre>
//       <InputText v-model="searchText" :placeholder="…" />
//     </template>
//     <LookupSelect … @change="onStatoChange" />
//     <FiltroPeriodo :periodo="periodo" />
//   </FiltriLista>
//
// ⚠️ L'esempio NON mostra due `<DatePicker>` con `@date-select`, e non e' una
//    svista: quel cablaggio e' il difetto che `<FiltroPeriodo>` esiste per
//    togliere — una data DIGITATA nella casella non applica il filtro. La
//    coppia `data_da`/`data_a` passa da `bindPeriodo()`; un DatePicker SOLO
//    (un filtro a se', non un periodo) resta legittimo, con
//    `@update:model-value`.
//
// I due slot, e la differenza e' una decisione (D2):
//   #sempre    la RICERCA — sempre a video, anche in compatta. Non e' un
//              filtro: e' il gesto principale della lista, e gli altri la
//              restringono. Nasconderla dietro due tocchi proprio sul
//              dispositivo dove digitare costa di piu' e' il contrario di
//              cio' che serve.
//   default    i filtri: in linea su desktop, dentro il drawer in compatta.
//
// ⛔ IL BB UNIFICA IL CONTENITORE, NON I FILTRI (`feedback_bb_legge_non_trasporta`):
//    i widget restano quelli che sono, con i loro `@change`. Qui non passa
//    nessun valore.
//
// ⚠️ I filtri si applicano SUBITO, anche col drawer aperto (D3): i binder di
//    `useStoreFilterBindings` scrivono diretti sullo store, che e' la sede del
//    filtro. Un «Applica» vorrebbe una copia temporanea dei filtri accanto a
//    quella vera, e quella copia diverge alla prima cosa che la tocca da fuori
//    (un deep-link `?search=`, un `reset()`, un cambio di emittente). Col
//    drawer aperto ogni cambio fa una fetch dietro le quinte: alla chiusura la
//    lista e' gia' pronta.
//
// Brief: docs/it/dev/work-in-progress/brief-fe-filtri-lista-su-schermo-compatto.md
import { computed, getCurrentInstance, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import OverlayBadge from 'primevue/overlaybadge'
import DrawerTitle from './DrawerTitle.vue'
import { MANAGE_ICONS } from '../constants'
import { useUiStore } from '../../stores/ui'
import { registraDrawerChiudibile } from '../composables/useDrawerChiusuraGlobale'
import {
  SEGNO_DEFAULT,
  SEGNO_MODIFICATO,
  SEGNO_VUOTO,
  segnoFiltri,
} from '../utils/segnoFiltri'

const props = defineProps({
  // Lo store-lista (`useListaStoreCore` e le due factory). Da lui arrivano le
  // tre cose che il segno richiede — `filters`, `chiaviFiltro`, `filtriDefault`
  // — e il verbo di «Pulisci filtri» (`azzeraFiltri`).
  // ⚠️ Non e' obbligatorio solo perche' esistono superfici con filtri e senza
  //    store-lista (i cruscotti, il giornale): quelle passano `segno`.
  store: { type: Object, default: null },
  // Via d'uscita dichiarata per chi non ha uno store-lista: il segno gia'
  // calcolato, nella forma che `segnoFiltri` restituisce.
  // ⛔ Non e' un'alternativa di comodo: chi HA lo store passa lo store, o il
  //    conteggio diventa una seconda sede che diverge al primo filtro aggiunto.
  segno: { type: Object, default: null },
  // Spegne i filtri senza toglierli (oggi: il cancello di perimetro emittente,
  // che vive in `useListaConfigurabilePage`). Vale su entrambe le rese.
  inert: { type: Boolean, default: false },
  // Titolo del drawer. Default: «Filtri».
  titolo: { type: String, default: null },
})

// `pulisci` serve SOLO alle superfici senza store (con lo store il BB agisce
// da se'): e' il motivo per cui il pulsante si mostra anche quando qualcuno lo
// ascolta.
const emit = defineEmits(['pulisci'])

// ⛔ IL LISTENER SI CERCA NEL VNODE, NON IN `useAttrs()`, e la prima stesura
//    usava `attrs.onPulisci`. Vue TOGLIE da `$attrs` gli handler degli eventi
//    DICHIARATI in `defineEmits` (`isEmitListener` in `setFullProps`): avendo
//    dichiarato `pulisci`, `attrs.onPulisci` e' `undefined` SEMPRE, anche
//    quando il chiamante ha scritto `@pulisci`. Effetto: sulle superfici senza
//    store — cruscotti, giornale, cioe' l'unica ragione per cui questo ramo
//    esiste — «Pulisci filtri» non compariva mai. Nessun errore, e da desktop
//    non si vede affatto, perche' il pulsante vive solo nel drawer.
//    ⭐ E' il caso di `feedback_contratto_dichiarato_provalo_intero`: il ramo
//    che il contratto dichiara ammesso va provato, non dedotto.
const istanza = getCurrentInstance()

const { t } = useI18n()
const ui = useUiStore()

const drawerVisibile = ref(false)

// La soglia NON si decide qui: `isCompatto` e' la sede unica (larghezza sotto
// il tablet OPPURE assenza di hover, D1). Scriverla di nuovo significherebbe
// avere una schermata mezza compatta e mezza no su un iPad Pro.
const compatto = computed(() => ui.isCompatto)

// Uscendo dalla modalita' compatta (rotazione, resize, schermo esterno) il
// drawer non ha piu' senso: i filtri sono tornati in linea. Lasciarlo aperto
// mostrerebbe gli stessi filtri due volte.
watch(compatto, (ora) => { if (!ora) drawerVisibile.value = false })

// ⭐ Il drawer entra nella CHIUSURA GLOBALE, come ogni altro drawer di questo
//    software (`useDrawerState`, `useDocumentoDrawer`). La ragione e' la stessa:
//    un `Drawer` e' teleportato sul `body` e la view che lo ospita vive sotto
//    `KeepAlive`, quindi un cambio di rotta la DISATTIVA senza smontarla — il
//    pannello resterebbe davanti alla pagina d'arrivo, che e' un'altra lista.
//    La de-registrazione e' automatica (scope del setup).
registraDrawerChiudibile(() => { drawerVisibile.value = false })

// ⛔ FAIL-VISIBLE, e ha due destinatari. Uno store che non dichiara le chiavi
//    dei filtri non fa fallire niente: il segno direbbe «nessun filtro» su una
//    lista che filtra — cioe' esattamente la cosa che questo componente esiste
//    per impedire. L'operatore non puo' accorgersene; lo sviluppatore si', se
//    glielo si dice.
const storeSenzaChiavi = computed(
  () => !!props.store && !props.segno && !Array.isArray(props.store.chiaviFiltro),
)

watch(storeSenzaChiavi, (rotto) => {
  if (!rotto) return
  console.error(
    '[FiltriLista] lo store passato non dichiara `chiaviFiltro`/`filtriDefault`: '
    + 'il segno dei filtri attivi resterebbe spento mentre la lista filtra. '
    + 'Lo store va costruito con `useListaStoreCore` (o `createListaStore` / '
    + '`createCrudStore`), oppure la superficie passa la prop `segno`.',
  )
}, { immediate: true })

const segnoRisolto = computed(() => {
  if (props.segno) return props.segno
  if (storeSenzaChiavi.value || !props.store) return { stato: SEGNO_VUOTO, conteggio: 0 }
  return segnoFiltri(props.store.filters, props.store.chiaviFiltro, props.store.filtriDefault)
})

const haSegno = computed(() => segnoRisolto.value.stato !== SEGNO_VUOTO)
const soloDefault = computed(() => segnoRisolto.value.stato === SEGNO_DEFAULT)
const modificato = computed(() => segnoRisolto.value.stato === SEGNO_MODIFICATO)

// Il tooltip dice a parole cio' che il segno dice con un colore: su touch il
// tooltip non c'e', ma resta l'etichetta accessibile del pulsante.
const tooltipFiltri = computed(() => {
  if (modificato.value) return t('common.filtri_attivi', { n: segnoRisolto.value.conteggio })
  if (soloDefault.value) return t('common.filtri_default_attivi')
  return t('common.filtri')
})

// «Pulisci filtri» c'e' solo se ha qualcosa da pulire e qualcuno che lo sappia
// fare: un pulsante che non fa nulla e' peggio della sua assenza.
const puoPulire = computed(
  () => haSegno.value
    && (typeof props.store?.azzeraFiltri === 'function'
      || !!istanza?.vnode.props?.onPulisci),
)

// Scopo: riportare i filtri al loro default. Col drawer APERTO, cosi' si vede
//        subito che cos'e' cambiato.
// ⛔ Non `store.reset()`: quello azzera anche il padre della lista, e dentro un
//    drawer scollegherebbe la lista dal documento che la ospita. Il verbo
//    giusto vive nello store (`azzeraFiltri`).
function pulisci() {
  if (typeof props.store?.azzeraFiltri === 'function') props.store.azzeraFiltri()
  emit('pulisci')
}
</script>

<template>
  <!-- Desktop: la forma di sempre. `app-page-filters` resta la classe del
       gruppo, cosi' la resa e il flex-wrap non cambiano di una riga. -->
  <div v-if="!compatto" class="app-page-filters" :inert="inert">
    <slot name="sempre" />
    <slot />
  </div>

  <!-- Compatta: la ricerca resta, i filtri diventano un gesto. -->
  <div v-else class="app-page-filters app-page-filters--compatta" :inert="inert">
    <slot name="sempre" />
    <!-- ⛔ IL BADGE NON VA NEL DEFAULT SLOT DEL BUTTON, e la prima stesura lo
         faceva: in PrimeVue lo slot di default SOSTITUISCE il rendering interno
         (icona, label, badge) — `<slot>` avvolge tutto in `Button.vue`. Il
         risultato e' un pulsante SENZA ICONA col solo badge dentro, e nessun
         errore da nessuna parte. Trovato in-app da Tid il 2026-09-22.
         ⭐ La posizione del segno la decide `OverlayBadge` (tema PrimeVue:
         `translate(50%, -50%)` + outline di contrasto), non un `position:
         absolute` scritto a mano qui: e' la stessa ragione per cui le
         larghezze dei filtri non stanno nei tag. -->
    <!-- ⛔ NIENTE `size="small"`, e toglierlo E' LA CORREZIONE del pallino che
         copriva l'icona (Tid, in-app). Quel `size` serviva a rimpicciolire il
         NUMERO — cosa che le misure in `main.css` fanno gia' da sole — ma il
         badge lo applica anche allo stato PALLINO, e li' fa danno: nel tema
         `.p-badge-dot` (0.5rem) e `.p-badge-sm` (1.25rem) hanno la STESSA
         specificita' e `sm` e' dichiarata DOPO, quindi vince lei su `min-width`
         e `height`. Il pallino diventava un cerchio da 1.25rem con 2px di
         outline appuntato nell'angolo del pulsante: a 2.5rem di pulsante e
         1rem di glifo, ci finisce sopra.
         ⭐ La correzione non e' un override piu' forte: e' non chiedere una
         taglia che uno dei due stati non sa onorare. Il segno ha due forme e
         una sola di esse ha una dimensione da dire. -->
    <OverlayBadge
      :value="modificato ? segnoRisolto.conteggio : null"
      :severity="modificato ? 'info' : 'secondary'"
      class="app-filtri-segno"
      :class="{ 'app-filtri-senza-segno': !haSegno }"
    >
      <Button
        class="app-filtri-btn"
        :class="{ 'app-filtri-btn--attivo': haSegno }"
        :icon="MANAGE_ICONS.FILTRI"
        :aria-label="tooltipFiltri"
        v-tooltip.bottom="tooltipFiltri"
        severity="secondary"
        text
        @click="drawerVisibile = true"
      />
    </OverlayBadge>
  </div>

  <!-- ⚠️ `v-if="compatto"`: il drawer esiste SOLO in modalita' compatta,
       altrimenti lo slot dei filtri sarebbe montato due volte — due DatePicker
       legati allo stesso store, e il secondo invisibile. -->
  <Drawer
    v-if="compatto"
    v-model:visible="drawerVisibile"
    position="bottom"
    class="app-filtri-drawer"
    :modal="true"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle :title="titolo || t('common.filtri')" :icon="MANAGE_ICONS.FILTRI" />
    </template>

    <!-- ⛔ QUI NON SI USA `useDrawerContentReady`, ED E' UNA DEROGA MOTIVATA al
         pattern `feedback_content_ready_after_show`. Quel pattern esiste per i
         drawer LATERALI, che hanno larghezza fissa e altezza piena: rimandare
         i widget pesanti alla fine dello slide evita il «blocco e ripartenza»
         senza cambiare la geometria del pannello.
         Qui la geometria la DECIDE il contenuto (altezza `auto`), quindi
         rimandarlo produce esattamente il difetto che dovrebbe evitare: il
         pannello sale vuoto, poi i filtri compaiono di scatto e l'altezza
         salta. 🔴 Visto in-app da Tid il 2026-09-22 — «il movimento sembra
         molto meccanico, non e' fluido». Coi filtri montati dallo start lo
         slide anima un pannello che ha gia' la sua altezza: si muove solo il
         `transform`, che e' la sola cosa che il browser anima senza ricalcoli.
         ⚠️ E il costo qui e' basso: un drawer di filtri porta due-sei widget,
         non un documento intero. -->
    <div class="app-filtri-drawer__corpo" :inert="inert">
      <slot />
    </div>

    <template #footer>
      <div class="app-filtri-drawer__footer">
        <Button
          v-if="puoPulire"
          severity="secondary"
          text
          :label="t('common.pulisci_filtri')"
          :icon="MANAGE_ICONS.FILTRI_PULISCI"
          @click="pulisci"
        />
      </div>
    </template>
  </Drawer>
</template>
