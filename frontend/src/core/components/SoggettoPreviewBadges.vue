<script setup>
// Scopo: badge compatti con conteggio indirizzi/contatti/conti bancari.
// Click su un badge apre il drawer corrispondente.
// Riutilizzabile per qualsiasi ruolo (cliente, fornitore, ecc.) e per soggetto.
//
// Context:
//   soggetto-ruolo-id valorizzato → context 'ruolo' (cascata ruolo + soggetto)
//   soggetto-id valorizzato (senza ruolo) → context 'soggetto' (lista piatta)
//   preview=true → drawer in sola lettura (creazione)
import { ref, computed, watch, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import {
  listRuoloContatti, listRuoloIndirizzi, listRuoloContiBancari,
  listSoggettoContatti, listSoggettoIndirizzi, listSoggettoContiBancari
} from '../../anagrafiche/api/anagrafiche'
import ContattiSoggettoDrawer from './ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from './IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from './ContiBancariDrawer.vue'
import Button from 'primevue/button'

const { t } = useI18n()

// In modalita' preview (creazione), forza sola lettura per i drawer figli
provide(READONLY_KEY, computed(() => props.preview))

const props = defineProps({
  soggettoRuoloId: { type: Number, default: null },
  soggettoId: { type: String, default: null },
  tipoSoggettoDettaglioId: { type: Number, default: null },
  istanzaUtilityId: { type: Number, default: null },
  tipoRuoloCodice: { type: String, default: null },
  preview: { type: Boolean, default: false },
})

// Scopo: determina il context in base alle prop valorizzate.
const isRuolo = computed(() => !!props.soggettoRuoloId)
const ownerId = computed(() => props.soggettoRuoloId || props.soggettoId)
const drawerContext = computed(() => isRuolo.value ? 'ruolo' : 'soggetto')

const counts = ref({ indirizzi: 0, contatti: 0, conti: 0 })
const loading = ref(false)
const activeDrawer = ref(null) // 'contatti' | 'indirizzi' | 'conti' | null

// Scopo: carica conteggi da API ruolo o soggetto in base al context.
async function fetchCounts() {
  if (!ownerId.value) return
  loading.value = true
  try {
    if (isRuolo.value) {
      const params = props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId } : {}
      const [cont, ind, conti] = await Promise.all([
        listRuoloContatti(props.soggettoRuoloId, params),
        listRuoloIndirizzi(props.soggettoRuoloId, params),
        listRuoloContiBancari(props.soggettoRuoloId, params),
      ])
      const contData = cont.data?.data || {}
      const indData = ind.data?.data || {}
      const contiData = conti.data?.data || {}
      counts.value = {
        contatti: (contData.contatti_ruolo?.length || 0) + (contData.contatti_soggetto?.length || 0),
        indirizzi: (indData.indirizzi_ruolo?.length || 0) + (indData.indirizzi_soggetto?.length || 0),
        conti: (contiData.conti_ruolo?.length || 0) + (contiData.conti_ereditati?.length || 0),
      }
    } else {
      const [cont, ind, conti] = await Promise.all([
        listSoggettoContatti(props.soggettoId),
        listSoggettoIndirizzi(props.soggettoId),
        listSoggettoContiBancari(props.soggettoId),
      ])
      counts.value = {
        contatti: cont.data?.data?.results?.length || cont.data?.data?.length || 0,
        indirizzi: ind.data?.data?.results?.length || ind.data?.data?.length || 0,
        conti: conti.data?.data?.results?.length || conti.data?.data?.length || 0,
      }
    }
  } catch {
    counts.value = { indirizzi: 0, contatti: 0, conti: 0 }
  } finally {
    loading.value = false
  }
}

watch([() => props.soggettoRuoloId, () => props.soggettoId], () => {
  if (ownerId.value) fetchCounts()
  else counts.value = { indirizzi: 0, contatti: 0, conti: 0 }
}, { immediate: true })

// Aggiorna conteggi quando un drawer si chiude (l'utente potrebbe aver creato/eliminato)
watch(activeDrawer, (newVal, oldVal) => {
  if (oldVal && !newVal) fetchCounts()
})
</script>

<template>
  <div v-if="ownerId" class="preview-badges">
    <Button
      outlined icon="pi pi-map-marker"
      :label="`${counts.indirizzi} ${t('clienti.gestisci_indirizzi')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'indirizzi'"
    />
    <Button
      outlined icon="pi pi-wallet"
      :label="`${counts.conti} ${t('clienti.gestisci_conti')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'conti'"
    />
    <Button
      outlined icon="pi pi-id-card"
      :label="`${counts.contatti} ${t('clienti.gestisci_contatti')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'contatti'"
    />

    <!-- Drawer: readonly se preview=true, editabile se preview=false -->
    <ContattiSoggettoDrawer
      :visible="activeDrawer === 'contatti'"
      @update:visible="v => { if (!v) { activeDrawer = null; fetchCounts() } }"
      :soggetto-id="ownerId"
      :istanza-utility-id="istanzaUtilityId"
      :context="drawerContext"
    />
    <IndirizziSoggettoDrawer
      :visible="activeDrawer === 'indirizzi'"
      @update:visible="v => { if (!v) { activeDrawer = null; fetchCounts() } }"
      :soggetto-id="ownerId"
      :istanza-utility-id="istanzaUtilityId"
      :tipo-soggetto-dettaglio-id="tipoSoggettoDettaglioId"
      :tipo-ruolo-codice="tipoRuoloCodice"
      :context="drawerContext"
    />
    <ContiBancariDrawer
      :visible="activeDrawer === 'conti'"
      @update:visible="v => { if (!v) { activeDrawer = null; fetchCounts() } }"
      :owner-id="ownerId"
      :istanza-utility-id="istanzaUtilityId"
      :context="drawerContext"
    />
  </div>
</template>

<style scoped>
.preview-badges {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  margin: 0.5rem 0;
}
.preview-badge-btn {
  font-size: 1.05rem;
}
</style>
