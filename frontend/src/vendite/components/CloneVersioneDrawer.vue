<script setup>
// Scopo: Drawer compatto per clonare una versione listino esistente in una
//        nuova versione BOZZA, copiando le righe attive della sorgente.
// Apertura: dal pulsante "clona" nella mini-tabella versioni dell'expansion.
// Da qualunque stato, anche da una BOZZA (C-1 = a, brief-modello-documento-vendita
// §16.16 FE-C2). Vincolo D2: target.valido_dal >= sorgente.valido_dal, lo dice
// il verbo del DB (`fn_clona_versione_listino`) sul campo valido_dal.
// I componenti dei compositi senza giorni in comune fra distinta e versione
// nuova non si copiano: la risposta li conta (`componenti_saltati`) e lo si dice.
// Avviso retroattivo (D2): se valido_dal < oggi mostra warning sul fatto che
// le fatturazioni gia' emesse non vengono toccate (servirebbe rettifica DB-L4).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useNotify } from '../../core/composables/useNotify'
import { cloneVersione } from '../api/listini'
import { getVersioneCloneDefaults } from '../api/formDefaults'
import { toDateString, displayDate, addDaysToToday, giornoDi, oggiAziendale, parseIsoDate } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import AppDrawer from '../../core/components/AppDrawer.vue'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listino: { type: Object, default: null },
  sourceVersione: { type: Object, default: null },
})

const emit = defineEmits(['update:visible', 'cloned'])

const form = ref({})
// Modifiche non salvate: fotografia dopo i default BE, chiudere con
// modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

function emptyForm() {
  // Form iniziale prima della risposta BE. Sovrascritto da loadDefaults sotto.
  const src = props.sourceVersione
  return {
    codice_versione: src?.codice_versione || '',
    valido_dal: addDaysToToday(1),
    valido_al: null,
  }
}

// Defaults BE (Fase 2.B5b): suffisso codice + lead_gg. D2 (la copia non
// comincia prima della sorgente) la dice il verbo del DB, sul campo valido_dal.
async function loadDefaults() {
  if (!props.listino?.id || !props.sourceVersione?.id) return
  const res = await execute(
    () => getVersioneCloneDefaults(props.listino.id, props.sourceVersione.id),
    { silent: true },
  )
  if (res === null) return
  form.value = {
    codice_versione: res.default_codice_versione || '',
    valido_dal: parseIsoDate(res.default_valido_dal),
    valido_al: parseIsoDate(res.default_valido_al),
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  form.value = emptyForm()
  await loadDefaults()
  fissa()
})

const canSave = computed(() =>
  !!form.value.codice_versione?.trim() &&
  !!form.value.valido_dal
)

// Avviso retroattivo: scatta quando valido_dal e' precedente a oggi.
// Il DB permette comunque (entro il vincolo D2 del verbo), ma l'utente
// deve essere consapevole che le fatturazioni successive non saranno corrette.
const isRetroattivo = computed(() => {
  if (!form.value.valido_dal) return false
  const target = giornoDi(form.value.valido_dal)
  return target !== null && target < oggiAziendale()
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
    if (result.componenti_saltati > 0) {
      notify.warn(t('vendite.listini.clona_componenti_saltati', { count: result.componenti_saltati }))
    }
    emit('cloned', { listinoId: props.listino.id, versione: result })
    close()
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.listini.clona_versione')"
    :icon="MANAGE_ICONS.CLONE"
    :action="t('vendite.listini.clona')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="handleSave"
  >
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
      <InputText v-model="form.codice_versione"
        :invalid="campiErrati.includes('codice_versione')"
      />
    </div>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.listini.field_valido_dal') }} *</label>
        <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon
          :invalid="campiErrati.includes('valido_dal')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_valido_al') }}</label>
        <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar
          :invalid="campiErrati.includes('valido_al')"
        />
      </div>
    </div>

    <Message v-if="isRetroattivo" severity="warn" :closable="false" class="mt-1">
      {{ t('vendite.listini.warning_retroattivo') }}
    </Message>
  </AppDrawer>
</template>
