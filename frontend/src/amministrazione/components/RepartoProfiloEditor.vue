<script setup>
// Scopo: drawer editor profilo permessi di un reparto.
// Aree: griglia con Select livello (TUTTO/LETTURA/BLOCCATO).
// Azioni: lista con ToggleSwitch.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRepartiStore } from '../stores/reparti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useLookup } from '../../core/composables/useLookup'
import { listAreeFunzionali, listAzioniProcesso } from '../api/amministrazione'
import { LIVELLO_ACCESSO, buildLivelloOptions } from '../constants'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Drawer from 'primevue/drawer'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'



const { t } = useI18n()
const repartiStore = useRepartiStore()
const { execute, loading } = useApiHandler()
const { confirmSave } = useConfirmAction()
const isReadonly = useInjectReadonly()
const areeFunzionali = useLookup(listAreeFunzionali, { immediate: true })
const azioniProcesso = useLookup(listAzioniProcesso, { immediate: true })

const props = defineProps({
  visible: Boolean,
  uoId: { type: Number, default: null },
  uoNome: { type: String, default: '' }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const livelloOptions = buildLivelloOptions(t)

const localAree = ref([])
const localAzioni = ref([])

watch(() => props.visible, async (val) => {
  if (!val || !props.uoId) return
  await repartiStore.fetchProfilo(props.uoId)

  const profilo = repartiStore.currentProfilo
  if (profilo) {
    // Inizializza con tutte le aree, precompilando quelle gia' configurate
    const existingMap = new Map((profilo.aree || []).map(a => [a.area_id, a.livello]))
    localAree.value = (areeFunzionali.items.value || []).map(af => ({
      area_id: af.id,
      area_codice: af.codice,
      area_descrizione: af.descrizione,
      livello: existingMap.get(af.id) || LIVELLO_ACCESSO.BLOCCATO
    }))

    const existingAzioni = new Map((profilo.azioni || []).map(a => [a.azione_id, a.abilitata]))
    localAzioni.value = (azioniProcesso.items.value || []).map(ap => ({
      azione_id: ap.id,
      permission_codename: ap.permission_codename,
      azione_descrizione: ap.descrizione,
      area_codice: ap.area_codice,
      pericolosa: ap.pericolosa,
      abilitata: existingAzioni.get(ap.id) || false
    }))
  }
})

function onSave() {
  confirmSave(async () => {
    const aree = localAree.value.map(a => ({
      area_id: a.area_id,
      livello: a.livello
    }))
    const azioni = localAzioni.value.map(a => ({
      azione_id: a.azione_id,
      abilitata: a.abilitata
    }))
    const result = await execute(
      () => repartiStore.saveProfilo(props.uoId, aree, azioni),
      { successMessage: t('notifications.save_success') }
    )
    if (result) emit('saved')
  }, t('amministrazione.profilo_save_confirm'))
}

const onClose = useDrawerClose(emit, 'cancelled')
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('amministrazione.profilo_reparto', { nome: uoNome })" :icon="NAV_ICONS.SITEMAP" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
    <Accordion :value="['aree', 'azioni']" multiple>
      <AccordionPanel value="aree">
        <AccordionHeader>{{ t('amministrazione.aree_funzionali') }}</AccordionHeader>
        <AccordionContent>
          <DataTable :value="localAree" size="small">
            <Column field="area_descrizione" :header="t('amministrazione.col_area')" />
            <Column :header="t('amministrazione.col_livello')" style="width: 12rem">
              <template #body="{ data }">
                <Select v-model="data.livello" :options="livelloOptions"
                  option-label="label" option-value="value" />
              </template>
            </Column>
          </DataTable>
        </AccordionContent>
      </AccordionPanel>

      <AccordionPanel value="azioni">
        <AccordionHeader>{{ t('amministrazione.azioni_processo') }}</AccordionHeader>
        <AccordionContent>
          <DataTable :value="localAzioni" size="small">
            <Column field="azione_descrizione" :header="t('amministrazione.col_azione')" />
            <Column field="area_codice" :header="t('amministrazione.col_area')" style="width: 8rem" />
            <Column :header="t('amministrazione.col_abilitata')" style="width: 6rem">
              <template #body="{ data }">
                <ToggleSwitch v-model="data.abilitata" />
              </template>
            </Column>
          </DataTable>
        </AccordionContent>
      </AccordionPanel>
    </Accordion>
    </div>

    <FormFooter v-if="contentReady" :loading="loading" @save="onSave" @cancel="onClose" />
  </Drawer>
</template>
