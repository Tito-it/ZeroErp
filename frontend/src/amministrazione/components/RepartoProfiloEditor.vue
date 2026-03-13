<script setup>
// Scopo: drawer editor profilo permessi di un reparto.
// Aree: griglia con Select livello (TUTTO/LETTURA/BLOCCATO).
// Azioni: lista con ToggleSwitch.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRepartiStore } from '../stores/reparti'
import { useUtentiStore } from '../stores/utenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { DRAWER_WIDTH } from '../../core/constants'
import { useConfirm } from 'primevue/useconfirm'
import Drawer from 'primevue/drawer'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'

const { t } = useI18n()
const repartiStore = useRepartiStore()
const utentiStore = useUtentiStore()
const { execute, loading } = useApiHandler()
const confirm = useConfirm()

const props = defineProps({
  visible: Boolean,
  uoId: { type: Number, default: null },
  uoNome: { type: String, default: '' }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const livelloOptions = [
  { label: 'TUTTO', value: 'TUTTO' },
  { label: 'LETTURA', value: 'LETTURA' },
  { label: 'BLOCCATO', value: 'BLOCCATO' }
]

const localAree = ref([])
const localAzioni = ref([])

watch(() => props.visible, async (val) => {
  if (!val || !props.uoId) return
  await Promise.all([
    utentiStore.fetchAreeFunzionali(),
    utentiStore.fetchAzioniProcesso(),
    repartiStore.fetchProfilo(props.uoId)
  ])

  const profilo = repartiStore.currentProfilo
  if (profilo) {
    // Inizializza con tutte le aree, precompilando quelle gia' configurate
    const existingMap = new Map(profilo.aree.map(a => [a.area_id, a.livello]))
    localAree.value = utentiStore.areeFunzionali.map(af => ({
      area_id: af.id,
      area_codice: af.codice,
      area_descrizione: af.descrizione,
      livello: existingMap.get(af.id) || 'BLOCCATO'
    }))

    const existingAzioni = new Map(profilo.azioni.map(a => [a.azione_id, a.abilitata]))
    localAzioni.value = utentiStore.azioniProcesso.map(ap => ({
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
  confirm.require({
    message: t('amm.profilo_save_confirm'),
    header: t('amm.profilo_save_title'),
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
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
    }
  })
}

function onClose() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :header="t('amm.profilo_reparto_title', { nome: uoNome })"
    @update:visible="val => emit('update:visible', val)"
  >
    <ConfirmDialog />

    <Accordion :multiple="true" :active-index="[0, 1]">
      <AccordionPanel>
        <AccordionHeader>{{ t('amm.aree_funzionali') }}</AccordionHeader>
        <AccordionContent>
          <DataTable :value="localAree" size="small">
            <Column field="area_descrizione" :header="t('amm.col_area')" />
            <Column :header="t('amm.col_livello')" style="width: 12rem">
              <template #body="{ data }">
                <Select v-model="data.livello" :options="livelloOptions"
                  option-label="label" option-value="value" class="w-full" />
              </template>
            </Column>
          </DataTable>
        </AccordionContent>
      </AccordionPanel>

      <AccordionPanel>
        <AccordionHeader>{{ t('amm.azioni_processo') }}</AccordionHeader>
        <AccordionContent>
          <DataTable :value="localAzioni" size="small">
            <Column field="azione_descrizione" :header="t('amm.col_azione')" />
            <Column field="area_codice" :header="t('amm.col_area')" style="width: 8rem" />
            <Column :header="t('amm.col_abilitata')" style="width: 6rem">
              <template #body="{ data }">
                <ToggleSwitch v-model="data.abilitata" />
              </template>
            </Column>
          </DataTable>
        </AccordionContent>
      </AccordionPanel>
    </Accordion>

    <div class="flex justify-end gap-2 mt-4">
      <Button :label="t('common.cancel')" severity="secondary" @click="onClose" />
      <Button :label="t('common.save')" icon="pi pi-check" :loading="loading" @click="onSave" />
    </div>
  </Drawer>
</template>
