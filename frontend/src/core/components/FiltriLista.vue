<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
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
// ⭐ `#sempre` NON SI RENDE SE LA LISTA NON CERCA (`store.ricercaFull ===
//    false`, dalla configurazione: brief-be-ricerca-full-liste-residue §7-bis,
//    Tid 2026-09-23). Una casella su una lista senza colonne accese a catalogo
//    non troverebbe niente per costruzione, e la casella e il catalogo non
//    devono poter dire due cose diverse. ⚠️ Solo `false`: `null`/assente
//    («non si sa ancora», o superficie senza catalogo) lascia la casella —
//    niente lampeggio a ogni apertura.
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
// Brief: docs/it/dev/work-done/brief-fe-filtri-lista-su-schermo-compatto.md
import { computed, getCurrentInstance, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import OverlayBadge from 'primevue/overlaybadge'
import DrawerTitle from './DrawerTitle.vue'
import { MANAGE_ICONS } from '../constants'
import { useUiStore } from '../../stores/ui'
import { registraDrawerChiudibile } from '../composables/useDrawerChiusuraGlobale'
import { useDrawerInCima } from '../composables/useDrawerInCima'
import { conTastoDiAzione, useScorciatoie } from '../composables/useScorciatoie'
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

// ⛔ UNA LISTA CON LA SOLA RICERCA NON HA FILTRI, E NON DEVE AVERE L'IMBUTO
//    (2026-09-23, emerso convertendo le liste che hanno solo la casella —
//    `VersioneDrawer`, i template e-mail, le conversioni UoM, i pannelli di
//    configurazione). Senza il guard, in modalita' compatta comparivano il
//    pulsante e un drawer VUOTO: un gesto che non porta da nessuna parte, e per
//    giunta impossibile da vedere da desktop, dove il ramo compatto non si
//    rende affatto.
// ⚠️ Si guarda lo slot di DEFAULT, non `#sempre`: la ricerca non e' un filtro
//    (D2), quindi non ha segno da mostrare ne' niente da portare nel drawer.
// ⛔ E SI LEGGE `$slots` DAL TEMPLATE, non da una `computed` su `useSlots()`:
//    l'oggetto degli slot viene RIMPIAZZATO a ogni render e non notifica
//    nessuno, quindi una `computed` che lo legge non ha nessuna dipendenza
//    tracciata — si calcolerebbe una volta sola e non si aggiornerebbe piu'
//    (e' il difetto gia' scritto in `DrawerTabLista.slotInoltrati`).

const { t, te } = useI18n()
const ui = useUiStore()

const drawerVisibile = ref(false)
// Entra nella pila dei drawer (`useDrawerInCima`): aperto dentro un drawer con
// una lista, ne e' il figlio — ESC chiude questo, non anche quello sotto.
useDrawerInCima(() => drawerVisibile.value)

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
  return segnoFiltri(
    props.store.filters,
    props.store.chiaviFiltro,
    props.store.filtriDefault,
    // ⚠️ I valori che non restringono, quando non sono `null`: li dichiara lo
    //    store (`filtriNeutri`). Senza, il numero sale quando la lista si
    //    ALLARGA — v. `segnoFiltri`.
    props.store.filtriNeutri,
  )
})

// La casella di ricerca (`#sempre`) c'e' salvo che la lista dichiari di non
// cercare — vedi l'intestazione.
const conRicerca = computed(() => props.store?.ricercaFull !== false)

const haSegno = computed(() => segnoRisolto.value.stato !== SEGNO_VUOTO)
const soloDefault = computed(() => segnoRisolto.value.stato === SEGNO_DEFAULT)
const modificato = computed(() => segnoRisolto.value.stato === SEGNO_MODIFICATO)

// Il tooltip dice a parole cio' che il segno dice con un colore: su touch il
// tooltip non c'e', ma resta l'etichetta accessibile del pulsante.
const tooltipFiltri = computed(() => {
  if (modificato.value) return t('common.filtri_attivi', { n: segnoRisolto.value.conteggio })
  if (soloDefault.value) return t('common.filtri_default_attivi', { n: segnoRisolto.value.conteggio })
  return t('common.filtri')
})

// «Pulisci filtri» c'e' solo se ha qualcosa da pulire e qualcuno che lo sappia
// fare: un pulsante che non fa nulla e' peggio della sua assenza.
// ⛔ E «qualcosa da pulire» NON E' «c'e' un segno» (2026-09-23): le due domande
//    divergono da quando esistono i valori neutri. Un filtro portato al valore
//    che NON restringe — «mostra non attive» sulle conversioni, «tutte le
//    versioni» nel drawer BoM — o un default svuotato a mano lasciano la lista
//    intera, quindi nessun segno, ma i filtri NON sono al loro default: li'
//    «Pulisci» e' l'unico gesto che riporta indietro, e col solo `haSegno`
//    spariva proprio in quello stato. ⚠️ Nessun errore, e invisibile da
//    desktop: il pulsante vive nel drawer compatto.
const puoPulire = computed(
  () => (haSegno.value || segnoRisolto.value.modificato === true)
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

// ⭐ F2 = «Pulisci filtri» (2026-10-04, ok Tid): i filtri si iscrivono ai
//    tasti funzione delle liste come la barra (`useScorciatoie`), con la
//    STESSA condizione del pulsante — `$slots.default && puoPulire`. Lo slot
//    si legge al momento del tasto (non in una computed: vedi sopra).
const radiceFiltri = ref(null)
const AZIONE_PULISCI = Object.freeze({ key: 'pulisci-filtri', command: pulisci })
useScorciatoie({
  elemento: () => radiceFiltri.value,
  azioni: () => (istanza?.slots.default && puoPulire.value ? [AZIONE_PULISCI] : []),
  esegui: (a) => a.command(),
})
const tooltipPulisci = computed(() =>
  conTastoDiAzione(t, te, t('common.pulisci_filtri'), AZIONE_PULISCI.key),
)
</script>

<template>
  <!-- Desktop: la forma di sempre. `app-page-filters` resta la classe del
       gruppo, cosi' la resa e il flex-wrap non cambiano di una riga. -->
  <div v-if="!compatto" ref="radiceFiltri" class="app-page-filters" :inert="inert">
    <slot v-if="conRicerca" name="sempre" />
    <slot />
    <!-- ⭐ «PULISCI FILTRI» ANCHE SU DESKTOP (decisione A3 di Tid, 2026-09-23).
         Su desktop i filtri si vedono tutti, quindi il SEGNO sarebbe poco piu'
         che decorazione; il VERBO no — riportarli al default a mano vuole tanti
         gesti quanti sono i filtri, e su una lista con sei filtri l'operatore
         non sa nemmeno quali ha toccato.
         ⚠️ Stessa condizione del ramo compatto, e non e' una ripetizione: e'
         `puoPulire`, cioe' «c'e' qualcosa da riportare al default» — non «c'e'
         un segno». Le due domande divergono da quando esistono i valori neutri
         (§11.10 del brief).
         ⛔ E `$slots.default` come il badge: una lista che qui dentro non mette
         nessun filtro non ha niente da pulire, anche se il suo store dichiara
         dei `filterDefaults`.
         ⭐ Icona sola col tooltip, come ogni altro pulsante di questa toolbar
         (`PageActionsBar`): l'etichetta per esteso resta nel drawer, dove c'e' lo
         spazio e il gesto e' piu' lontano dai filtri. La classe e' quella del
         pulsante-imbuto perche' sono la stessa famiglia — i comandi dei filtri
         nella toolbar — e i colori vivono in una sede sola. -->
    <Button
      v-if="$slots.default && puoPulire"
      class="app-filtri-btn"
      :icon="MANAGE_ICONS.FILTRI_PULISCI"
      :aria-label="t('common.pulisci_filtri')"
      v-tooltip.bottom="tooltipPulisci"
      severity="secondary"
      text
      @click="pulisci"
    />
  </div>

  <!-- Compatta: la ricerca resta, i filtri diventano un gesto. -->
  <div v-else ref="radiceFiltri" class="app-page-filters app-page-filters--compatta" :inert="inert">
    <slot v-if="conRicerca" name="sempre" />
    <!-- ⛔ IL BADGE NON VA NEL DEFAULT SLOT DEL BUTTON, e la prima stesura lo
         faceva: in PrimeVue lo slot di default SOSTITUISCE il rendering interno
         (icona, label, badge) — `<slot>` avvolge tutto in `Button.vue`. Il
         risultato e' un pulsante SENZA ICONA col solo badge dentro, e nessun
         errore da nessuna parte. Trovato in-app da Tid il 2026-09-22.
         ⭐ La posizione del segno la decide `OverlayBadge` (tema PrimeVue:
         `translate(50%, -50%)` + outline di contrasto), non un `position:
         absolute` scritto a mano qui: e' la stessa ragione per cui le
         larghezze dei filtri non stanno nei tag. -->
    <!-- ⛔ IL NUMERO C'E' SEMPRE, E LA DIFFERENZA LA FA IL COLORE (rilievo in-app
         di Tid, 2026-09-23). Fino a quel giorno lo stato «tutti al default» era
         un PALLINO senza numero, e il numero compariva solo al primo filtro
         cambiato: a video si leggeva «0 → 2» toccando UNA cosa sola, perche' il
         filtro gia' attivo (`attivo = SI` su articoli) valeva zero un istante e
         uno quello dopo. ⚠️ Il conteggio non e' mai cambiato — era 1 anche col
         pallino — ma la forma lo NASCONDEVA, e un segno che nasconde cio' che
         conta fa sembrare sbagliato un conto giusto.
         ⭐ La regola di D4 resta intera: si contano sempre i filtri, default
         compresi. Cambia solo COME si distingue «ristretta come nasce» da
         «ristretta da te» — prima due FORME (pallino / numero), adesso due
         COLORI a parita' di forma (`secondary` grigio / `info` blu). ⚠️ Cosi'
         l'obiezione del §2.3 — «un segno sempre acceso smette di essere un
         segno» — continua a valere: a essere sempre acceso e' il numero, non
         l'allarme.
         ⛔ NIENTE `size="small"`: quel `size` serviva a rimpicciolire il numero
         — cosa che le misure in `main.css` fanno gia' da sole — ed era la causa
         del «pallino vuoto che copre l'icona» visto il 22-09. Il pallino non si
         rende piu', ma la trappola resta scritta perche' la lezione vale per
         ogni variante chiesta al tema: nel tema `.p-badge-dot` e `.p-badge-sm`
         hanno la stessa specificita' e vince l'ULTIMA dichiarata, che non
         decido io.
         ⭐ La posizione del segno la decide `OverlayBadge` (tema PrimeVue), non
         un `position: absolute` scritto a mano. -->
    <OverlayBadge
      v-if="$slots.default"
      :value="segnoRisolto.conteggio"
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
    v-if="compatto && $slots.default"
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

    <!-- ⚠️ `:inert` ANCHE QUI, e non e' ridondante: il corpo lo porta gia', ma
         «Pulisci filtri» vive nel footer e AZZERA i filtri sul serio. Con il
         perimetro bloccato l'imbuto non si puo' nemmeno premere, quindi oggi il
         pulsante e' irraggiungibile — ma basta che il drawer sia gia' aperto
         quando il perimetro si chiude (un cambio di emittente, una rotazione)
         perche' l'unico comando rimasto vivo sia proprio quello che scrive. -->
    <template #footer>
      <div class="app-filtri-drawer__footer" :inert="inert">
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
