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

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
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
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['changed', 'state'])

const { t } = useI18n()
const { execute } = useApiHandler()
const parentReadonly = useInjectReadonly()
const isReadonlyEffective = computed(() => props.readonly || parentReadonly.value)

const apiClient = makeIndirizziDocumentoApi(`/vendite/${props.dominio}`)

const tipiAmmessi = ref([])
const indirizzi = ref([])

async function load() {
  if (!props.docId) return
  const res = await execute(() => apiClient.list(props.docId))
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
  <div v-if="docId && tipoDefault" class="app-drawer-section indirizzi-section">
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
