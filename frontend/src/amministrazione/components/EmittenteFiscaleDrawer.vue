<script setup>
// Scopo: Drawer creazione/modifica anagrafica emittente fiscale (admin only).
// Solo Dati fiscali base + Soggetto (resolver in crea, banner in modifica).
// Billing Account e Utilities sono drawer dedicati separati (vedi
// EmittenteFiscaleBillingAccountDrawer / EmittenteFiscaleUtilitiesDrawer),
// richiamati dai pulsanti azione della lista.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, TIPO_RUOLO } from '../../core/constants'
import { getEmittenteFormDefaults } from '../api/amministrazione'
import { paramBool, paramNumber, paramString } from '../../core/utils/parameterCast'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import EmittenteRoundingModeSelect from './EmittenteRoundingModeSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import Button from 'primevue/button'

// Valori del campo rounding_policy: 4 codici (UP/DOWN/HALF_UP/HALF_DOWN)
// allineati al CHECK chk_emittenti_fiscali_rounding_policy. Single source of
// truth lato BE; il FE consuma via EmittenteRoundingModeSelect (Fase 3 — A6).

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  emittenteId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Dati dettaglio caricato dal backend (sostituisce store.currentEmittente per evitare
// race condition tra drawer aperti consecutivamente).
const detail = ref(null)

// Titolo drawer: in modifica mostra "Modifica EF — <ragione sociale>".
// Il codice tecnico e' visibile dentro al form (campo Codice), nel titolo
// usiamo solo la ragione sociale per leggibilita'.
const drawerTitle = computed(() => {
  if (!isEdit.value) return t('amm_emittenti_fiscali.create_title')
  const base = t('amm_emittenti_fiscali.edit_title')
  const rs = detail.value?.ragione_sociale_completa
  return rs ? `${base} — ${rs}` : base
})

// Resolver soggetto (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Stato form neutro. I valori dei campi fiscali (`bollo_auto`, `bollo_soglia`,
// `rounding_policy`) vengono popolati via `applyFormDefaults()` da
// `config.parameters` con cascata user->group->default (Fase 3 — A5).
// Il campo `attivo` ha sempre `true` lato FE: la colonna DB ha gia' DEFAULT
// true, non passa per parameters (vedi note brief DB 2026-04-29).
function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    attivo: true,
    regime_fiscale_rf: '',
    bollo_auto: false,
    bollo_soglia: null,
    rounding_policy: null,
    // valuta_id: livello 3 della catena resolve_valuta_default (vedi
    // backend/apps/anagrafiche/services/valuta_resolver.py). Se non
    // valorizzata, i form-defaults preventivi/contratti senza BA partono
    // con valuta vuota.
    valuta_id: null
  }
}

const form = ref(defaultForm())

// Carica defaults da BE (cast tipi gia' applicato lato server) e li applica
// al form. Best-effort: errori di rete non bloccano il form (l'utente compila
// manualmente). Chiamata solo in modalita' `create` (in `edit` il populate
// arriva dal detail dell'emittente esistente).
//
// Cast defensive via parameterCast.js (pattern catalogo Fase 1):
// se il BE in futuro cambiasse la serializzazione (es. bool come stringa, Decimal
// non parsabile), gli helper proteggono il form da NaN/leak di stringhe sporche.
//
// Race cancellation: se l'utente chiude e riapre il drawer in edit prima che la
// fetch completi, la mutazione post-await si applicherebbe a un'istanza in edit,
// sovrascrivendo i valori del detail. Il guard `!props.visible || isEdit.value`
// blocca l'update se il contesto non e' piu' "create con drawer aperto".
async function applyFormDefaults() {
  try {
    const res = await getEmittenteFormDefaults()
    if (!props.visible || isEdit.value) return  // race guard
    const d = res?.data?.data?.defaults || {}
    form.value.bollo_auto = paramBool(d.bollo_auto, false)
    // bollo_soglia: BE serializza Decimal come stringa (es. "100.00") o null.
    form.value.bollo_soglia = paramNumber(d.bollo_soglia, null)
    form.value.rounding_policy = paramString(d.rounding_policy, null)
  } catch (err) {
    // Best-effort: in caso di errore l'utente compila manualmente.
    // Console warning aiuta il debug senza disturbare l'utente.
    console.warn('[EmittenteFiscaleDrawer] form-defaults non disponibili', err)
  }
}

function resetForm() {
  soggettoSelezionato.value = null
  detail.value = null
  form.value = defaultForm()
}

function populateFormFromDetail(d) {
  form.value = {
    codice: d.codice || '',
    descrizione: d.descrizione || '',
    attivo: !!d.attivo,
    regime_fiscale_rf: d.regime_fiscale_rf || '',
    bollo_auto: !!d.bollo_auto,
    bollo_soglia: d.bollo_soglia,
    rounding_policy: d.rounding_policy || null,
    valuta_id: d.valuta_id ?? null
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
    // Fase 3: applica defaults form da config.parameters (best-effort).
    // Pattern allineato a catalogo Fase 8 (ArticoloDrawer).
    await applyFormDefaults()
  }
})

function onSoggettoSelezionato(data) { soggettoSelezionato.value = data }
function onSoggettoCreato(data) { soggettoSelezionato.value = data }
function clearSoggetto() { soggettoSelezionato.value = null }

// Vincolo bollo: se bollo automatico e' OFF, la soglia non e' applicabile
// e viene azzerata a null. L'input UI viene anche disabilitato.
watch(() => form.value.bollo_auto, (v) => {
  if (!v) form.value.bollo_soglia = null
})

const canSave = computed(() => {
  if (isEdit.value) return form.value.descrizione.trim().length > 0
  return !!soggettoSelezionato.value
      && soggettoHasPartitaIva.value
      && form.value.codice.trim().length > 0
      && form.value.descrizione.trim().length > 0
})

async function save() {
  if (!canSave.value) return
  const payload = {
    descrizione: form.value.descrizione.trim(),
    attivo: form.value.attivo,
    regime_fiscale_rf: form.value.regime_fiscale_rf || null,
    bollo_auto: form.value.bollo_auto,
    bollo_soglia: form.value.bollo_soglia,
    rounding_policy: form.value.rounding_policy || null,
    valuta_id: form.value.valuta_id || null
  }
  let result
  if (isEdit.value) {
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
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle
        :icon="isEdit ? 'pi pi-pencil' : 'pi pi-plus'"
        :title="drawerTitle"
      />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
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
                <!-- Editabile solo se bollo_auto = true; altrimenti azzerata via watch. -->
                <InputNumber
                  v-model="form.bollo_soglia"
                  :disabled="!form.bollo_auto"
                  :min-fraction-digits="2" :max-fraction-digits="2"
                  class="w-full"
                />
              </div>
            </div>

            <div class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_rounding_policy') }}</label>
              <EmittenteRoundingModeSelect
                v-model="form.rounding_policy"
                :placeholder="t('amm_emittenti_fiscali.field_rounding_policy')"
                show-clear
                class="w-full"
              />
            </div>

            <!-- Valuta di default: livello 3 della catena resolve_valuta_default
                 usata da preventivi/contratti senza BA. Senza questo valore i
                 form-defaults restituiscono valuta vuota. -->
            <div class="form-field">
              <label>{{ t('amm_emittenti_fiscali.field_valuta') }}</label>
              <LookupSelect
                v-model="form.valuta_id"
                rel="config.valute"
                :placeholder="t('amm_emittenti_fiscali.field_valuta')"
                show-clear
                class="w-full"
              />
              <small class="block mt-1 text-color-secondary">
                {{ t('amm_emittenti_fiscali.field_valuta_hint') }}
              </small>
            </div>

            <!-- Attivo: ultimo elemento del form (richiesta UX) -->
            <div class="form-field mt-3">
              <label>{{ t('amm_emittenti_fiscali.field_attivo') }}</label>
              <ToggleSwitch v-model="form.attivo" />
            </div>
          </template>
        </div>

        <!-- Footer Salva/Annulla -->
        <div class="flex justify-end mt-4">
          <DrawerFooter
            :loading="loading"
            :disabled="!canSave"
            :save-label="isEdit ? t('common.save') : t('common.create')"
            @save="save"
            @cancel="close"
          />
        </div>
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
