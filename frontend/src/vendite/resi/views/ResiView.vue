<script setup>
// Scopo: Vista principale gestione resi di vendita. Tre tab: lista resi
//        (configurabile) + le due code di lavoro "da accreditare" (righe a
//        credito CONFERMATE, predisposizione slice nota di credito) e "da
//        ri-consegnare" (righe per ri-consegna con copertura pendente).
//        Host del drawer reso. Il reso NASCE solo dal DDT (pannello nel
//        drawer DDT): nessuna azione "Nuovo" qui. Clone ridotto di DdtView.
import { onActivated, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'

import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../../core/constants'
import { TAB_RESI } from '../constants'
import { useResiStore } from '../stores/resi'
import { useResiCodaAccreditareStore } from '../stores/resiCoda'
import ResiSearchTable from '../components/ResiSearchTable.vue'
import ResiCodaTable from '../components/ResiCodaTable.vue'
import ResoDrawer from '../components/ResoDrawer.vue'

const { t } = useI18n()
const drawer = useDrawerState()
const store = useResiStore()
const activeTab = ref(TAB_RESI.LISTA)

// Permessi: livello area `vendite` + livello oggetto `reso` (fallback ad
// area se il model non e' catalogato, vedi frontend-standards).
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.RESO)

// Su 'saved' (patch testata / conferma / annullo / ri-consegna): refresh
// lista + chiude drawer.
// Handler standard, dal BB: `saved` ricarica e chiude, `changed` ricarica e
// LASCIA APERTO (il drawer ha generato un documento e il lavoro continua).
// `riapriDopoCreate: false` — la transizione CREATE → "edit-evolved" e' interna
// al drawer (auto-save bozza) e non passa di qui.
const {
  onDrawerSaved: ricaricaListaEChiudi,
  onDrawerChanged: ricaricaLista,
} = useDrawerSavedListRefresh(
  store, drawer, { riapriDopoCreate: false, soloSeCercata: true },
)

// ⭐ QUI LE LISTE SONO TRE, non una — ed e' la ragione per cui questa vista non
// puo' usare gli handler del BB cosi' come sono. Il drawer reso si apre anche
// DALLE CODE (`@apri-reso`), e da li' un accredito o una ri-consegna cambiano
// la coda che sta dietro: senza questo giro l'operatore chiudeva il drawer e
// ritrovava la riga che aveva appena lavorato, immutata.
// ⚠️ Il `?.` non e' prudenza: i TabPanel sono `lazy`, quindi la coda non attiva
// non e' montata e il suo ref e' `null`. Il ref E' il test di montaggio — la
// coda non montata ricarichera' al proprio mount, e chiamare `fetchList` sul
// suo store da qui produrrebbe la doppia chiamata gia' pagata in
// `applicaDeepLinkCoda`.
const codaAccreditareRef = ref(null)
const codaRiconsegnareRef = ref(null)

// ⚠️ BEST-EFFORT DICHIARATO: `fetchList` propaga (try/finally, nessun catch) e
// qui non si attende — senza il `catch` un errore di rete su una coda
// diventerebbe una unhandled rejection. E il silenzio e' voluto: questo e' un
// riallineamento di CONTORNO, l'atto e' gia' riuscito e ha gia' il suo toast.
// Una coda che non si ricarica si ricarica al prossimo giro; un secondo toast
// rosso su un'operazione andata bene direbbe una cosa falsa.
function ricaricaCode() {
  codaAccreditareRef.value?.reload()?.catch(() => {})
  codaRiconsegnareRef.value?.reload()?.catch(() => {})
}

async function onDrawerSaved(result) {
  ricaricaCode()
  await ricaricaListaEChiudi(result)
}

async function onDrawerChanged() {
  ricaricaCode()
  await ricaricaLista()
}

// Dalle code si apre lo stesso drawer reso (riga -> reso_id).
function openReso(resoId) {
  drawer.editRow({ id: resoId }, 'id')
}

// --- Deep-link dal pannello situazione merce (FE-2) --------------------------
// `?tab=da-accreditare&ddt_id=…` (oppure `ordine_id`): apre la coda GIA'
// filtrata sul documento da cui si arriva.
//
// ⚠️ In `onActivated`, non solo in `setup`/`onMounted`: la vista vive sotto
//    KeepAlive (AppLayout, `:key="$route.path"`), quindi un deep-link su una
//    vista gia' in cache non rimonta niente e un'applicazione fatta al mount
//    non scatterebbe mai (memoria feedback_keepalive_onactivated).
// ⚠️ Idempotente, e la query si PULISCE dopo averla applicata: lasciarla
//    significherebbe ri-filtrare la coda ogni volta che si torna su questa
//    vista, anche dopo che l'operatore ha tolto il filtro a mano.
const route = useRoute()
const router = useRouter()
const codaAccrediti = useResiCodaAccreditareStore()

function numeroQuery(chiave) {
  const raw = route.query[chiave]
  const n = Number(raw)
  return raw != null && raw !== '' && Number.isInteger(n) && n > 0 ? n : null
}

function applicaDeepLinkCoda() {
  const ddtId = numeroQuery('ddt_id')
  const ordineId = numeroQuery('ordine_id')
  if (ddtId == null && ordineId == null) return

  // I due filtri sono ALTERNATIVI (il backend rifiuta la coppia): vince il DDT,
  // che e' il piu' specifico dei due.
  codaAccrediti.filters.ddt_id = ddtId
  codaAccrediti.filters.ordine_id = ddtId != null ? null : ordineId
  codaAccrediti.filters.offset = 0
  activeTab.value = route.query.tab === TAB_RESI.DA_RICONSEGNARE
    ? TAB_RESI.DA_RICONSEGNARE
    : TAB_RESI.DA_ACCREDITARE

  // ⛔ Nessuna fetch qui: la decide il pannello della coda, che e' l'unico a
  //    sapere se e' montato — se lo e', osserva i filtri e ricarica; se non lo
  //    e' ancora, li trova gia' impostati al proprio mount. Provare a
  //    indovinarlo da qui produceva una doppia chiamata.
  const resto = { ...route.query }
  delete resto.tab
  delete resto.ddt_id
  delete resto.ordine_id
  router.replace({ query: resto })
}

onActivated(applicaDeepLinkCoda)
</script>

<template>
  <div class="app-page">
    <!-- `lazy`: i pannelli montano solo alla prima attivazione — senza, le
         due code fetcherebbero al load pagina anche se l'utente resta sulla
         lista (PrimeVue 4 monta tutti i TabPanel eager con v-show). -->
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab :value="TAB_RESI.LISTA">{{ t('vendite.resi.tab_lista') }}</Tab>
        <Tab :value="TAB_RESI.DA_ACCREDITARE">{{ t('vendite.resi.tab_da_accreditare') }}</Tab>
        <Tab :value="TAB_RESI.DA_RICONSEGNARE">{{ t('vendite.resi.tab_da_riconsegnare') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel :value="TAB_RESI.LISTA">
          <ResiSearchTable
            @row-click="(data) => drawer.editRow(data, 'id')"
          />
        </TabPanel>
        <TabPanel :value="TAB_RESI.DA_ACCREDITARE">
          <ResiCodaTable ref="codaAccreditareRef" coda="accreditare" @apri-reso="openReso" />
        </TabPanel>
        <TabPanel :value="TAB_RESI.DA_RICONSEGNARE">
          <ResiCodaTable ref="codaRiconsegnareRef" coda="riconsegnare" @apri-reso="openReso" />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <ResoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :reso-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @changed="onDrawerChanged"
      @cancelled="drawer.close"
    />
  </div>
</template>
