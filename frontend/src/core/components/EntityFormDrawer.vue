<script setup>
// Scopo: drawer CRUD generico guidato da SCHEMA-campi per entita' descrittive
//        con store tipizzato + i18n + widget FK (estrazione regola del 2,
//        2026-06-05). Estratto dai 6 drawer geografici quasi identici
//        (Comune/Province/Regioni/Stati/CodiciPostali/Toponomastica), che
//        diventano wrapper ~15 righe.
//
// NON sostituisce GenericConfigDrawer.vue: quello e' metadata-driven
// (information_schema + CRUD generico /core/config/tables/, label = nome
// colonna grezzo, niente FK/i18n/store). Qui invece store tipizzato + label
// i18n + Select FK / autocomplete / toggle. Data-layer diversi → due componenti.
//
// `fields`: array di entry. Ogni entry e':
//   - un campo: { name, type:'text'|'select'|'autocomplete'|'toggle', labelKey,
//       required?, maxlength?, lookupFn?, optionLabel?, optionValue?,
//       placeholderKey?, component? (autocomplete), disabledInEdit?, editOnly?,
//       default? (toggle) }
//   - un gruppo: { group:true, fields:[<campi>] } → reso in form-grid-2col.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { useLookup } from '../composables/useLookup'
import { useDrawerFormPreserve, gestoreVisibile } from '../composables/useDrawerFormPreserve'
import { DRAWER_WIDTH } from '../constants'
import FormFooter from './FormFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import EntityFormField from './EntityFormField.vue'
import Drawer from 'primevue/drawer'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  item: { type: Object, default: null },
  store: { type: Object, required: true }, // { create, update?, fetchList? }
  fields: { type: Array, required: true },
  titleKey: { type: String, required: true },
  icon: { type: String, default: '' },
  width: { type: String, default: DRAWER_WIDTH.SIMPLE },
  successKeys: { type: Object, default: () => ({}) }, // { create, update }
  refreshOnSave: { type: Boolean, default: true },
})
const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

// Appiattisce gruppi + campi semplici in un'unica lista di field-def.
const flatFields = computed(() =>
  props.fields.flatMap(f => (f.group ? f.fields : [f])),
)

// useLookup per ogni campo select (fields e' statico → numero di hook stabile).
const lookups = {}
for (const f of props.fields.flatMap(f => (f.group ? f.fields : [f]))) {
  if (f.type === 'select' && f.lookupFn) lookups[f.name] = useLookup(f.lookupFn)
}

const form = ref({})
// Modifiche non salvate: la fotografia si fissa all'apertura (anche in
// creazione: un record nuovo compilato e poi chiuso e' lavoro perso), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
const chiudi = () => chiudiConConferma(() => emit('update:visible', false))

function defaultFor(f) {
  if (f.type === 'toggle') return f.default ?? true
  if (f.type === 'text') return ''
  return null
}

watch(() => props.visible, (val) => {
  if (!val) return
  // Lazy load dei lookup FK alla prima apertura.
  for (const name in lookups) {
    if (!lookups[name].loaded.value) lookups[name].load()
  }
  const f = {}
  const isEdit = props.mode === 'edit' && props.item
  for (const fd of flatFields.value) {
    if (isEdit) {
      f[fd.name] = fd.type === 'text'
        ? (props.item[fd.name] ?? '')
        : (props.item[fd.name] ?? defaultFor(fd))
    } else {
      f[fd.name] = defaultFor(fd)
    }
  }
  form.value = f
  fissa()
})

function fieldVisible(fd) {
  // editOnly (es. toggle attivo): nascosto in create, mostrato in edit.
  return !(fd.editOnly && props.mode === 'create')
}

const canSave = computed(() =>
  flatFields.value.every(fd => {
    if (!fd.required) return true
    const v = form.value[fd.name]
    return fd.type === 'text' ? String(v ?? '').trim().length > 0 : v != null
  }),
)

async function handleSave() {
  if (!canSave.value) return
  const isCreate = props.mode === 'create'
  const payload = {}
  for (const fd of flatFields.value) {
    if (fd.editOnly && isCreate) continue // attivo non inviato in create
    let v = form.value[fd.name]
    if (fd.type === 'text') {
      v = String(v ?? '').trim()
      v = v === '' ? null : v
    }
    payload[fd.name] = v
  }
  const msg = isCreate ? t(props.successKeys.create) : t(props.successKeys.update)
  const result = await execute(
    () => (isCreate ? props.store.create(payload) : props.store.update(props.item.id, payload)),
    { successMessage: msg },
  )
  if (result !== null) {
    emit('saved')
    emit('update:visible', false)
    if (props.refreshOnSave && typeof props.store.fetchList === 'function') {
      props.store.fetchList()
    }
  }
}
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width }"
    @update:visible="suVisibile"
  >
    <template #header>
      <DrawerTitle
        :modificato="modificato"
        :action="mode === 'create' ? t('common.new') : t('common.edit')"
        :title="t(titleKey)"
        :icon="icon"
      />
    </template>
    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <template v-for="(entry, i) in fields" :key="entry.group ? 'g' + i : entry.name">
          <div v-if="entry.group" class="form-grid-2col">
            <template v-for="fd in entry.fields" :key="fd.name">
              <EntityFormField
                v-if="fieldVisible(fd)"
                v-model="form[fd.name]"
                :field="fd"
                :mode="mode"
                :lookup="lookups[fd.name] || null"
              />
            </template>
          </div>
          <EntityFormField
            v-else-if="fieldVisible(entry)"
            v-model="form[entry.name]"
            :field="entry"
            :mode="mode"
            :lookup="lookups[entry.name] || null"
          />
        </template>
      </div>

      <FormFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="chiudi"
      />
    </div>
  </Drawer>
</template>
