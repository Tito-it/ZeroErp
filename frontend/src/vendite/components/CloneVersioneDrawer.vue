<script setup>
// Scopo: Drawer compatto per clonare una versione listino esistente in una
//        nuova versione BOZZA, copiando le righe attive della sorgente.
// Apertura: dal pulsante "clona" nella mini-tabella versioni dell'expansion.
// Vincolo D2: target.valido_dal >= sorgente.valido_dal (validato anche backend).
// Avviso retroattivo (D2): se valido_dal < oggi mostra warning sul fatto che
// le fatturazioni gia' emesse non vengono toccate (servirebbe rettifica DB-L4).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { cloneVersione } from '../api/listini'
import { getVersioneCloneDefaults } from '../api/formDefaults'
import { toDateString, displayDate, addDaysToToday } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listino: { type: Object, default: null },
  sourceVersione: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'cloned'])

const form = ref({})

function emptyForm() {
  // Form iniziale prima della risposta BE. Sovrascritto da loadDefaults sotto.
  const src = props.sourceVersione
  return {
    codice_versione: src?.codice_versione || '',
    valido_dal: addDaysToToday(1),
    valido_al: null,
  }
}

// Defaults BE (Fase 2.B5b): suffisso codice + lead_gg + min_valido_dal
// (vincolo D2: target.valido_dal >= source.valido_dal).
async function loadDefaults() {
  if (!props.listino?.id || !props.sourceVersione?.id) return
  const res = await execute(
    () => getVersioneCloneDefaults(props.listino.id, props.sourceVersione.id),
    { silent: true },
  )
  if (res === null) return
  form.value = {
    codice_versione: res.default_codice_versione || '',
    valido_dal: res.default_valido_dal ? new Date(res.default_valido_dal + 'T00:00:00') : null,
    valido_al: res.default_valido_al ? new Date(res.default_valido_al + 'T00:00:00') : null,
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  form.value = emptyForm()
  await loadDefaults()
})

const canSave = computed(() =>
  !!form.value.codice_versione?.trim() &&
  !!form.value.valido_dal
)

// Avviso retroattivo: scatta quando valido_dal e' precedente a oggi.
// Backend permette comunque (entro il vincolo src.valido_dal), ma l'utente
// deve essere consapevole che le fatturazioni successive non saranno corrette.
const isRetroattivo = computed(() => {
  if (!form.value.valido_dal) return false
  const target = new Date(form.value.valido_dal)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return target < today
})

async function handleSave() {
  if (!props.listino?.id || !props.sourceVersione?.id) return
  const f = form.value
  const payload = {
    codice_versione: f.codice_versione.trim(),
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
  }
  const result = await execute(
    () => cloneVersione(props.listino.id, props.sourceVersione.id, payload),
    { successMessage: t('vendite.listini.versione_clonata') }
  )
  if (result !== null) {
    emit('cloned', { listinoId: props.listino.id, versione: result })
    close()
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }">
    <template #header>
      <DrawerTitle :action="t('vendite.listini.clona')" :title="t('vendite.listini.clona_versione')" :icon="MANAGE_ICONS.CLONE" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="sourceVersione" class="app-drawer-section">
        <h4>
          {{ t('vendite.listini.versione_sorgente') }}:
          {{ sourceVersione.codice_versione }}
          ({{ displayDate(sourceVersione.valido_dal) }} → {{ displayDate(sourceVersione.valido_al) || '∞' }})
        </h4>
        <p class="app-text-muted mt-025">{{ t('vendite.listini.clona_help') }}</p>
      </div>

      <div class="form-field">
        <label>{{ t('vendite.listini.field_codice_versione') }} *</label>
        <InputText v-model="form.codice_versione" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.listini.field_valido_dal') }} *</label>
          <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
        </div>
      </div>

      <Message v-if="isRetroattivo" severity="warn" :closable="false" class="mt-1">
        {{ t('vendite.listini.warning_retroattivo') }}
      </Message>

      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
