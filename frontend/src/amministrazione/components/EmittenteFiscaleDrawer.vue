<script setup>
// Scopo: Drawer unificato creazione/modifica emittente fiscale (admin only).
// Sezioni: Soggetto (resolver in crea, banner in modifica), Dati fiscali base.
// TabView: Dati + Billing Account + Utilities (gli ultimi 2 disponibili solo in modifica).
// Supporta apertura su tab specifico tramite prop initialTab (per pulsanti azioni riga).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, TIPO_RUOLO } from '../../core/constants'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import EmittenteFiscaleBillingAccountTab from './EmittenteFiscaleBillingAccountTab.vue'
import EmittenteFiscaleUtilitiesTab from './EmittenteFiscaleUtilitiesTab.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
import Message from 'primevue/message'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'

// Valori ammessi dal CHECK constraint DB su anagrafiche.emittenti_fiscali.rounding_policy
// (allineati ai metodi della matrice utility).
const ROUNDING_POLICY_VALUES = ['HALF_UP', 'HALF_DOWN', 'UP', 'DOWN']

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  emittenteId: { type: Number, default: null },
  initialTab: { type: Number, default: 0 }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Dati dettaglio caricato dal backend (sostituisce store.currentEmittente per evitare
// race condition tra drawer aperti consecutivamente).
const detail = ref(null)
const activeTabIndex = ref(0)

// Resolver soggetto (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

const FORM_DEFAULT = {
  codice: '',
  descrizione: '',
  attivo: false,
  regime_fiscale_rf: '',
  bollo_auto: false,
  bollo_soglia: null,
  rounding_policy: null
}

const form = ref({ ...FORM_DEFAULT })

function resetForm() {
  soggettoSelezionato.value = null
  detail.value = null
  form.value = { ...FORM_DEFAULT }
}

function populateFormFromDetail(d) {
  form.value = {
    codice: d.codice || '',
    descrizione: d.descrizione || '',
    attivo: !!d.attivo,
    regime_fiscale_rf: d.regime_fiscale_rf || '',
    bollo_auto: !!d.bollo_auto,
    bollo_soglia: d.bollo_soglia,
    rounding_policy: d.rounding_policy || null
  }
}

// Validazione P.IVA del soggetto selezionato (requisito legale per emittente fiscale).
// Il backend rifiuta comunque la creazione, qui blocchiamo lato UI per UX migliore.
const soggettoHasPartitaIva = computed(() => {
  const s = soggettoSelezionato.value
  if (!s) return false
  const piva = s.partita_iva || s.piva || ''
  return typeof piva === 'string' && piva.trim().length > 0
})

// Carica dati quando il drawer si apre.
// Pattern allineato a FornitoreDrawer: fetchDetail viene chiamato DIRETTAMENTE,
// senza wrapping in execute() — useApiHandler.execute si aspetta una response axios
// non un dato gia' unwrappato dallo store.
watch(() => props.visible, async (val) => {
  if (!val) return
  activeTabIndex.value = props.initialTab || 0
  if (isEdit.value && props.emittenteId) {
    try {
      const d = await store.fetchDetail(props.emittenteId)
      if (d) {
        detail.value = d
        populateFormFromDetail(d)
      }
    } catch (e) {
      // Errori di rete/API gestiti dall'interceptor axios globale
      detail.value = null
    }
  } else {
    resetForm()
  }
})

function onSoggettoSelezionato(data) { soggettoSelezionato.value = data }
function onSoggettoCreato(data) { soggettoSelezionato.value = data }
function clearSoggetto() { soggettoSelezionato.value = null }

const canSave = computed(() => {
  if (isEdit.value) return form.value.descrizione.trim().length > 0
  return !!soggettoSelezionato.value
      && soggettoHasPartitaIva.value
      && form.value.codice.trim().length > 0
      && form.value.descrizione.trim().length > 0
})

async function save() {
  if (!canSave.value) return
  // Payload comune (campi editabili). attivo NON e' incluso in create:
  // l'emittente nasce sempre disattivato (guard DB su utility).
  const payload = {
    descrizione: form.value.descrizione.trim(),
    regime_fiscale_rf: form.value.regime_fiscale_rf || null,
    bollo_auto: form.value.bollo_auto,
    bollo_soglia: form.value.bollo_soglia,
    rounding_policy: form.value.rounding_policy || null
  }
  let result
  if (isEdit.value) {
    payload.attivo = form.value.attivo
    result = await execute(
      () => store.update(props.emittenteId, payload),
      { successMessage: t('amm_emittenti_fiscali.updated') }
    )
  } else {
    payload.soggetto_id = soggettoSelezionato.value.id
    payload.codice = form.value.codice.trim()
    result = await execute(
      () => store.create(payload),
      { successMessage: t('amm_emittenti_fiscali.created') }
    )
  }
  if (result !== null) emit('saved', result)
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
  >
    <template #header>
      <DrawerTitle
        :icon="isEdit ? 'pi pi-pencil' : 'pi pi-plus'"
        :title="isEdit ? t('amm_emittenti_fiscali.edit_title') : t('amm_emittenti_fiscali.create_title')"
      />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
    <TabView v-model:activeIndex="activeTabIndex">
      <TabPanel :header="t('amm_emittenti_fiscali.tab_dati')">
        <!-- Avviso creazione: l'emittente nasce disattivato (guard DB su utility) -->
        <Message v-if="!isEdit" severity="info" :closable="false" class="mb-3">
          {{ t('amm_emittenti_fiscali.create_disabled_hint') }}
        </Message>

        <div class="form-grid">
          <!-- Soggetto -->
          <h4>{{ t('amm_emittenti_fiscali.field_soggetto') }}</h4>
          <template v-if="!isEdit">
            <div v-if="soggettoSelezionato" class="mb-3">
              <SoggettoMessageBanner
                :ragione-sociale="soggettoSelezionato.ragione_sociale || soggettoSelezionato.ragione_sociale_completa"
                :codice-fiscale="soggettoSelezionato.cf || soggettoSelezionato.codice_fiscale"
              />
              <!-- Validazione P.IVA: requisito legale per emittente fiscale -->
              <Message
                v-if="!soggettoHasPartitaIva"
                severity="warn"
                :closable="false"
                class="mt-2"
              >
                {{ t('amm_emittenti_fiscali.soggetto_no_piva') }}
              </Message>
              <Button :label="t('resolver.change')" icon="pi pi-pencil"
                text size="small" class="mt-1" @click="clearSoggetto" />
            </div>
            <div v-else>
              <Button :label="t('resolver.open')" icon="pi pi-search"
                outlined class="w-full" @click="resolverVisible = true" />
            </div>
          </template>
          <div v-if="isEdit && detail" class="mb-3">
            <SoggettoMessageBanner
              :ragione-sociale="detail.ragione_sociale_completa"
              :codice-fiscale="detail.codice_fiscale"
            />
          </div>

          <!-- Sezioni dati emittente: visibili solo dopo selezione soggetto (create) o sempre (edit) -->
          <template v-if="isEdit || (soggettoSelezionato && soggettoHasPartitaIva)">
            <h4 class="mt-3">{{ t('amm_emittenti_fiscali.section_anagrafica') }}</h4>

            <div class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_codice') }} *</label>
              <InputText
                v-model="form.codice"
                :disabled="isEdit"
                maxlength="40"
                class="w-full"
              />
            </div>

            <div class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_descrizione') }} *</label>
              <InputText v-model="form.descrizione" maxlength="200" class="w-full" />
            </div>

            <!-- Toggle attivo solo in edit: in create e' forzato false dal backend -->
            <div v-if="isEdit" class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_attivo') }}</label>
              <ToggleSwitch v-model="form.attivo" />
              <small class="block mt-1 text-color-secondary">
                {{ t('amm_emittenti_fiscali.attivo_hint') }}
              </small>
            </div>

            <h4 class="mt-3">{{ t('amm_emittenti_fiscali.section_fiscale') }}</h4>

            <div class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_regime_fiscale_rf') }}</label>
              <InputText v-model="form.regime_fiscale_rf" maxlength="10" class="w-full" />
              <small class="block mt-1 text-color-secondary">
                {{ t('amm_emittenti_fiscali.regime_fiscale_rf_hint') }}
              </small>
            </div>

            <h4 class="mt-3">{{ t('amm_emittenti_fiscali.section_bollo') }}</h4>

            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('amm_emittenti_fiscali.field_bollo_auto') }}</label>
                <ToggleSwitch v-model="form.bollo_auto" />
              </div>
              <div class="form-field">
                <label>{{ t('amm_emittenti_fiscali.field_bollo_soglia') }}</label>
                <InputNumber v-model="form.bollo_soglia" :min-fraction-digits="2" :max-fraction-digits="2" class="w-full" />
              </div>
            </div>

            <div class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_rounding_policy') }}</label>
              <Select
                v-model="form.rounding_policy"
                :options="ROUNDING_POLICY_VALUES"
                :placeholder="t('amm_emittenti_fiscali.field_rounding_policy')"
                show-clear
                class="w-full"
              />
            </div>
          </template>
        </div>

        <!-- Footer Salva/Annulla dentro al pannello Dati (pattern OperatoreDrawer) -->
        <div class="flex justify-end mt-4">
          <DrawerFooter
            :loading="loading"
            :disabled="!canSave"
            :save-label="isEdit ? t('common.save') : t('common.create')"
            @save="save"
            @cancel="close"
          />
        </div>
      </TabPanel>

      <TabPanel
        v-if="isEdit"
        :header="t('amm_emittenti_fiscali.tab_billing_account')"
      >
        <EmittenteFiscaleBillingAccountTab :emittente-id="emittenteId" />
      </TabPanel>

      <TabPanel
        v-if="isEdit"
        :header="t('amm_emittenti_fiscali.tab_utilities')"
      >
        <EmittenteFiscaleUtilitiesTab :emittente-id="emittenteId" />
      </TabPanel>
    </TabView>
    </div>

    <!-- Sotto-drawer SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      :tipo-ruolo-codice="TIPO_RUOLO.EMITTENTE_FISCALE"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
    />
  </Drawer>
</template>
