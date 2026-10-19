<script setup>
// Scopo: Sezione inline "Indirizzi" per i drawer documento vendite (UX v2,
//        brief design §7): mostra SOLO l'indirizzo di DEFAULT (slot CON —
//        Consegna, standard cross-dominio — o FATT dove CON non e' ammesso).
//        Se mancante: avviso (bloccante per l'emissione quando il tipo e'
//        obbligatorio) da cui scatta l'obbligo di scelta. Gli altri tipi
//        impostati NON compaiono come righe: solo il contatore "+N altri".
//        Il pulsante "Indirizzi" apre il drawer di gestione
//        (DocumentoIndirizziDrawer), montato qui: il caller aggiunge UNA
//        sezione e ha tutto.
//
// ⭐ QUANDO si cambiano lo dice il DB, non lo stato del drawer: il lock «solo
//    in bozza» dei satelliti, specchiato dalla capability `can_edit_indirizzi`
//    del documento (brief-db-testata-dopo-emissione §11, R-FE-5). Per questo
//    la sezione NON eredita la catena readonly: quella del corpo del drawer e'
//    il readonly di stato, cioe' una copia della regola. Il chiamante passa
//    due cose distinte: `readonly` (i SOLI permessi) e `capabilities` (il blob
//    del documento); la capability la legge QUI, in un posto solo — fino al
//    2026-10-11 ogni drawer ricomponeva lo stesso OR (cinque copie, regola
//    del 2). La sezione esce dal corpo protetto (`app-escape`, la
//    consultazione e' lecita anche fuori bozza) e ri-`provide` il suo
//    readonly al drawer di gestione (stessa deroga alla convenzione dell'OR
//    di `DocumentoCollegamentiBar`).

import { computed, provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TIPO_RUOLO } from '../../../core/constants'
import DocumentoIndirizziDrawer from './DocumentoIndirizziDrawer.vue'
import IndirizzoProvenienzaTags from './IndirizzoProvenienzaTags.vue'
import { formatSnapshotDisplay, makeIndirizziDocumentoApi, pickTipoDefault } from './documentoIndirizziApi'

const props = defineProps({
  // Vedi DocumentoIndirizziDrawer per la semantica dei prop condivisi.
  dominio: { type: String, required: true },
  docId: { type: [Number, null], default: null },
  soggettoRuoloId: { type: [Number, null], default: null },
  istanzaUtilityId: { type: [Number, null], default: null },
  tipoRuoloCodice: { type: String, default: TIPO_RUOLO.CLIENTE },
  // Readonly dei PERMESSI del chiamante (non quello di stato del drawer).
  readonly: { type: Boolean, default: false },
  // Il blob capability del documento (`useEntityCapabilities().capabilities`):
  // la sezione ne legge `can_edit_indirizzi`. Assente = fail-closed.
  capabilities: { type: [Object, null], default: null },
  // La linea in fondo alla sezione. `false` dove il drawer la fa seguire da un
  // `<Divider>` (preventivo, ordine, DDT, prima delle righe): le due linee
  // attaccate si leggevano come una doppia riga (rilievo di Tid, 2026-09-28).
  // Offerta e contratto non hanno il Divider: li' la linea e' il separatore.
  bordo: { type: Boolean, default: true },
  // Il cliente nel form non e' quello salvato (BB `clienteCambiato`): gli
  // indirizzi mostrati sono ancora del cliente salvato, e li rifa' il DB al
  // salvataggio (B-3 di Tid). La sezione lo dice, invece di sembrare indietro
  // (collaudo di Tid, 2026-10-19).
  clienteDaSalvare: { type: Boolean, default: false },
})
const emit = defineEmits(['changed', 'state'])

const { t } = useI18n()
const { execute } = useApiHandler()
// `=== true` come `useEntityCapabilities.flag`: un flag assente non apre.
const isReadonlyEffective = computed(
  () => props.readonly || props.capabilities?.can_edit_indirizzi !== true,
)
provide(READONLY_KEY, isReadonlyEffective)

const apiClient = makeIndirizziDocumentoApi(`/vendite/${props.dominio}`)

const tipiAmmessi = ref([])
const indirizzi = ref([])

// Guard anti-stale: le `load()` possono sovrapporsi (cambio documento, cambio
// cliente, `changed` dal drawer di gestione); vince l'ultima lanciata.
const listaFv = useFetchVersion()

async function load() {
  if (!props.docId) return
  const tag = listaFv.tag()
  const res = await execute(() => apiClient.list(props.docId))
  if (!listaFv.isCurrent(tag)) return
  tipiAmmessi.value = res?.tipi_ammessi ?? []
  indirizzi.value = res?.indirizzi ?? []
  // Stato del default per il caller (es. avviso nel dialog di emissione).
  emit('state', {
    defaultImpostato: Boolean(rigaDefault.value),
    obbligatorioMancante: Boolean(
      tipoDefault.value?.obbligatorio && !rigaDefault.value),
  })
}

// Tipo di default: regola condivisa sezione/drawer (pickTipoDefault).
const tipoDefault = computed(() => pickTipoDefault(tipiAmmessi.value))

const rigaDefault = computed(() =>
  tipoDefault.value
    ? indirizzi.value.find(
        (r) => r.tipo_indirizzo_id === tipoDefault.value.tipo_indirizzo_id) ?? null
    : null)

// NB: il watch immediate DEVE seguire i computed usati da load() (TDZ,
// memoria feedback_vue_watch_immediate_tdz).
watch(() => props.docId, load, { immediate: true })

// Il cliente del documento cambiato in bozza (DDT: BA o destinatario;
// preventivo, offerta, contratto: BA o istanza): il DB toglie gli indirizzi
// del cliente di prima e riempie di nuovo lo slot di default
// (brief-db-indirizzi-documento-seguono-il-cliente, R-FE-2). I prop sono
// quelli del `detail` salvato, quindi si ricarica DOPO il salvataggio.
// ⚠️ Solo sullo STESSO documento e se un cliente c'era gia': all'apertura
//    l'identita' passa da vuota a valorizzata, e al cambio di documento il
//    drawer azzera `detail` mentre cambia `docId` — in entrambi i casi il
//    caricamento lo fa gia' il watch su `docId`, e una seconda `load()`
//    sarebbe una richiesta doppia in gara con la prima.
watch(
  () => [props.docId, props.soggettoRuoloId, props.istanzaUtilityId],
  ([doc], [docPrima, ...clientePrima]) => {
    if (doc === docPrima && clientePrima.some((v) => v != null)) load()
  },
)

// Altri tipi impostati oltre al default (visibili solo nel drawer gestione).
const altriCount = computed(() =>
  indirizzi.value.length - (rigaDefault.value ? 1 : 0))

const gestioneVisible = ref(false)

async function onChanged() {
  await load()
  emit('changed')
}
</script>

<template>
  <!-- ⚠️ La sezione avvolge anche il contenuto, quindi la linea di
       `app-drawer-section` cade SOTTO gli indirizzi: vedi la prop `bordo`. -->
  <div
    v-if="docId && tipoDefault"
    class="app-drawer-section app-escape"
    :class="{ 'app-drawer-section--senza-bordo': !bordo }">
    <h4>{{ t('vendite.indirizzi.titolo') }}</h4>

    <div class="indirizzi-section-row">
      <template v-if="rigaDefault">
        <Tag
          v-tooltip.bottom="t('vendite.indirizzi.tt_slot', { tipo: tipoDefault.tipo_indirizzo_descrizione })"
          :value="tipoDefault.tipo_indirizzo_descrizione"
          severity="info" />
        <span class="indirizzi-section-display">{{ formatSnapshotDisplay(rigaDefault) }}</span>
        <!-- Provenienza (da soggetto / una tantum / da <tipo>): BB condiviso
             col drawer di gestione. -->
        <IndirizzoProvenienzaTags :row="rigaDefault" />
        <Tag
          v-if="altriCount > 0"
          :value="t('vendite.indirizzi.altri_count', { n: altriCount })"
          severity="secondary" />
      </template>
      <Message
        v-else
        class="indirizzi-section-warn"
        :severity="tipoDefault.obbligatorio ? 'warn' : 'info'"
        :closable="false">
        {{ tipoDefault.obbligatorio
          ? t('vendite.indirizzi.mancante_obbligatorio')
          : t('vendite.indirizzi.non_impostato') }}
      </Message>
      <Button
        :label="t('vendite.indirizzi.titolo')"
        :icon="MANAGE_ICONS.INDIRIZZI"
        text
        size="small"
        class="app-action-btn indirizzi-section-btn"
        @click="gestioneVisible = true" />
    </div>

    <Message
      v-if="clienteDaSalvare"
      class="indirizzi-section-warn"
      severity="info"
      :closable="false">
      {{ t('vendite.indirizzi.cliente_da_salvare') }}
    </Message>

    <DocumentoIndirizziDrawer
      v-model:visible="gestioneVisible"
      :dominio="dominio"
      :doc-id="docId"
      :soggetto-ruolo-id="soggettoRuoloId"
      :istanza-utility-id="istanzaUtilityId"
      :tipo-ruolo-codice="tipoRuoloCodice"
      :readonly="isReadonlyEffective"
      :tipi-ammessi="tipiAmmessi"
      :indirizzi="indirizzi"
      @changed="onChanged" />
  </div>
</template>

<style scoped>
.indirizzi-section-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.indirizzi-section-display {
  min-width: 0;
}
.indirizzi-section-warn {
  flex: 1 1 auto;
}
.indirizzi-section-btn {
  flex: 0 0 auto;
}
.indirizzi-section-da-tipo {
  margin-left: auto;
  flex: 0 0 auto;
}
.indirizzi-section-da-tipo + .indirizzi-section-btn {
  margin-left: 0;
}
.indirizzi-section-row > :last-child.indirizzi-section-btn {
  margin-left: auto;
}
</style>
