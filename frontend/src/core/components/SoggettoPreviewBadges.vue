<script setup>
// Scopo: badge compatti con conteggio indirizzi/contatti/conti bancari.
// Click su un badge apre il drawer corrispondente.
// Riutilizzabile per qualsiasi ruolo (cliente, fornitore, ecc.) e per soggetto.
//
// Context:
//   soggetto-ruolo-id valorizzato → context 'ruolo' (cascata ruolo + soggetto)
//   soggetto-id valorizzato (senza ruolo) → context 'soggetto' (lista piatta)
//   preview=true → drawer in sola lettura (creazione)
import { ref, computed, watch, provide, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import {
  listRuoloContatti, listRuoloIndirizzi, listRuoloContiBancari,
  listSoggettoContatti, listSoggettoIndirizzi, listSoggettoContiBancari
} from '../../anagrafiche/api/anagrafiche'
import ContattiSoggettoDrawer from './ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from './IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from './ContiBancariDrawer.vue'
import WebAccessiDrawer from '../../portale/components/WebAccessiDrawer.vue'
import { getStatoAccessiCliente, getStatoAccessiFornitore } from '../../portale/api/portaleAdminApi'
import Button from 'primevue/button'

const { t } = useI18n()

// Readonly per i sub-drawer aperti dai badge: OR fra parent (split o
// LETTURA area/oggetto, propagato da useReadonlyMode) e preview di
// creazione. Non sovrascrivere il parent: vedi useReadonlyMode.
const parentReadonly = inject(READONLY_KEY, ref(false))
provide(READONLY_KEY, computed(() => parentReadonly.value || props.preview))

const props = defineProps({
  soggettoRuoloId: { type: Number, default: null },
  soggettoId: { type: String, default: null },
  tipoSoggettoDettaglioId: { type: Number, default: null },
  istanzaUtilityId: { type: Number, default: null },
  tipoRuoloCodice: { type: String, default: null },
  preview: { type: Boolean, default: false },
  // §1.6: pulsante Web (accessi portale/shop) opzionale, richiede
  // entitaTipo+entitaId per aprire WebAccessiDrawer. Se entitaTipo non
  // e' valorizzato il pulsante non compare (retrocompat: SoggettoPreviewBadges
  // resta usabile in contesti dove Web non si applica).
  entitaTipoWeb: {
    type: String,
    default: null,
    validator: v => v === null || ['cliente', 'fornitore'].includes(v),
  },
  entitaIdWeb: { type: [Number, String], default: null },
  emailInizialeWeb: { type: String, default: '' },
})

// Scopo: determina il context in base alle prop valorizzate.
const isRuolo = computed(() => !!props.soggettoRuoloId)
const ownerId = computed(() => props.soggettoRuoloId || props.soggettoId)
const drawerContext = computed(() => isRuolo.value ? 'ruolo' : 'soggetto')

const counts = ref({ indirizzi: 0, contatti: 0, conti: 0, accessi: 0 })
const loading = ref(false)
const activeDrawer = ref(null) // 'contatti' | 'indirizzi' | 'conti' | 'web' | null

// Scopo: mostra il pulsante Web solo se entitaTipo+entitaId sono
// valorizzati (caller ha attivato esplicitamente la feature per cliente/fornitore).
const showWeb = computed(() => !!props.entitaTipoWeb && !!props.entitaIdWeb)

// Scopo: carica count degli accessi web (portale+shop) se la feature
// e' abilitata. Un accesso e' "attivo" se stato = ATTIVO (PENDING non
// conta perche' l'invito e' solo in volo, l'utente non ha ancora
// completato l'attivazione).
async function fetchAccessiCount() {
  if (!showWeb.value) return 0
  try {
    const fn = props.entitaTipoWeb === 'cliente'
      ? getStatoAccessiCliente
      : getStatoAccessiFornitore
    const res = await fn(props.entitaIdWeb)
    const data = res?.data?.data || {}
    let n = 0
    if (data.portale?.stato === 'ATTIVO') n++
    if (data.shop?.stato === 'ATTIVO') n++
    return n
  } catch {
    return 0
  }
}

// Scopo: carica conteggi da API ruolo o soggetto in base al context.
async function fetchCounts() {
  if (!ownerId.value) return
  loading.value = true
  try {
    if (isRuolo.value) {
      const params = props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId } : {}
      const [cont, ind, conti, accessi] = await Promise.all([
        listRuoloContatti(props.soggettoRuoloId, params),
        listRuoloIndirizzi(props.soggettoRuoloId, params),
        listRuoloContiBancari(props.soggettoRuoloId, params),
        fetchAccessiCount(),
      ])
      const contData = cont.data?.data || {}
      const indData = ind.data?.data || {}
      const contiData = conti.data?.data || {}
      counts.value = {
        contatti: (contData.contatti_ruolo?.length || 0) + (contData.contatti_soggetto?.length || 0),
        indirizzi: (indData.indirizzi_ruolo?.length || 0) + (indData.indirizzi_soggetto?.length || 0),
        conti: (contiData.conti_ruolo?.length || 0) + (contiData.conti_ereditati?.length || 0),
        accessi,
      }
    } else {
      const [cont, ind, conti, accessi] = await Promise.all([
        listSoggettoContatti(props.soggettoId),
        listSoggettoIndirizzi(props.soggettoId),
        listSoggettoContiBancari(props.soggettoId),
        fetchAccessiCount(),
      ])
      counts.value = {
        contatti: cont.data?.data?.results?.length || cont.data?.data?.length || 0,
        indirizzi: ind.data?.data?.results?.length || ind.data?.data?.length || 0,
        conti: conti.data?.data?.results?.length || conti.data?.data?.length || 0,
        accessi,
      }
    }
  } catch {
    counts.value = { indirizzi: 0, contatti: 0, conti: 0, accessi: 0 }
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
      :label="`${counts.indirizzi} ${t('anagrafiche.clienti.gestisci_indirizzi')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'indirizzi'"
    />
    <Button
      outlined icon="pi pi-wallet"
      :label="`${counts.conti} ${t('anagrafiche.clienti.gestisci_conti')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'conti'"
    />
    <Button
      outlined icon="pi pi-id-card"
      :label="`${counts.contatti} ${t('anagrafiche.clienti.gestisci_contatti')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'contatti'"
    />
    <!-- §1.6 accessi web: pulsante visibile solo per cliente/fornitore
         (showWeb). Count = vesti ATTIVE (portale + shop per cliente, solo
         portale per fornitore). -->
    <Button
      v-if="showWeb"
      outlined icon="pi pi-globe"
      :label="`${counts.accessi} ${t('portale.accessi_web.badge_label')}`"
      :loading="loading"
      class="preview-badge-btn"
      @click="activeDrawer = 'web'"
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
    <WebAccessiDrawer
      v-if="showWeb"
      :visible="activeDrawer === 'web'"
      @update:visible="v => { if (!v) { activeDrawer = null; fetchCounts() } }"
      :entita-tipo="entitaTipoWeb"
      :entita-id="entitaIdWeb"
      :email-iniziale="emailInizialeWeb"
      :readonly="preview"
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
