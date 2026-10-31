<script setup>
// Scopo: Sub-drawer delle UoM operative di un articolo.
// ⭐ Dal 2026-10-31 la lista e' a catalogo (`catalogo.articolo_uom`, 111;
//    brief-db-liste-datatable-grezze-secondo-giro riga 4), sul BB
//    `ListaConFormInline`: colonne dal catalogo, ricerca (da 1 carattere: i
//    codici UoM sono corti) e ordinamento lato server. Il form e'
//    `ArticoloUomForm`. ⛔ Fino a quel giorno una `DataTable` grezza sulla
//    collezione intera, col form scritto qui.
// Click riga → modifica (pattern master-detail inline); il kebab tiene la
// sola azione secondaria, l'eliminazione, spenta col motivo dalla vista DB.
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerListaConForm } from '../../core/composables/useDrawerListaConForm'
import { deleteArticoloUom } from '../api/catalogo'
import { useArticoloUomStore } from '../stores/articoloUom'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { labelOrCode } from '../../core/utils/i18nLabel'
import AppDrawer from '../../core/components/AppDrawer.vue'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ListaConFormInline from '../../core/components/ListaConFormInline.vue'
import ArticoloUomForm from './ArticoloUomForm.vue'

const { t, te } = useI18n()
const isReadonly = useInjectReadonly()
const { execute } = useApiHandler()
const store = useArticoloUomStore()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

// La colla col BB (`useDrawerListaConForm`): l'articolo e' il padre SOLO a
// drawer aperto; footer e uscita seguono il form della UoM.
const {
  listaRef, formAperto, padre, modificato, chiudiConConferma, footer, onFormAperto,
} = useDrawerListaConForm({
  visible: () => props.visible,
  padre: () => props.articoloId,
})

// Scopo: Elimina UoM operativa; la lista si rilegge e il padre lo sa.
async function onDelete(row) {
  const result = await execute(
    () => deleteArticoloUom(props.articoloId, row.id),
    { successMessage: t('catalogo.uom_eliminata') }
  )
  if (result !== null && listaRef.value) listaRef.value.cambiata()
}

// Capability eliminazione (Fase 6) letta dalla vista DB: row.puo_eliminarsi +
// row.motivo_non_eliminabile (solo is_base blocca). L'azione resta visibile
// anche quando non eseguibile, col motivo nel tooltip.
function deleteUomTooltip(row) {
  if (row.puo_eliminarsi) return t('common.delete')
  const motivo = row.motivo_non_eliminabile
  if (!motivo) return t('common.delete')
  // Difensivo: motivo nuovo non mappato i18n -> label generica.
  const key = `catalogo.motivo_${motivo.toLowerCase()}`
  return labelOrCode(t, te, key, t('common.delete'))
}

function rowActions(row) {
  return [
    {
      key: 'elimina-uom',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !isReadonly.value && !formAperto.value,
      disabled: !row.puo_eliminarsi,
      tooltip: deleteUomTooltip(row),
      command: () => onDelete(row),
    },
  ]
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :proteggi-corpo="false"
    :title="t('catalogo.tab_uom')"
    :icon="MANAGE_ICONS.UOM"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="footer"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <ListaConFormInline
      ref="listaRef"
      codice="catalogo.articolo_uom"
      :store="store"
      :parent-id="padre"
      :is-modificabile="!isReadonly"
      new-tooltip-key="catalogo.nuova_uom_operativa"
      new-label-key="catalogo.nuova_uom_operativa"
      edit-label-key="catalogo.modifica_uom_operativa"
      :row-actions="rowActions"
      @changed="emit('saved')"
      @form-aperto="onFormAperto"
    >
      <template #cell-is_base="{ data }">
        <Tag v-if="data.is_base" :value="t('catalogo.tag_base')" severity="info" />
      </template>
      <template #cell-factor_to_base="{ data }">
        <span class="app-mono">{{ data.factor_to_base }}</span>
      </template>
      <template #cell-is_logistic_uom="{ data }">
        <Tag v-if="data.is_logistic_uom" :value="t('catalogo.tag_logistica')" severity="success" />
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>

      <template #form="{ riga, onSaved, onCancel, registra }">
        <ArticoloUomForm
          :ref="registra"
          :riga="riga"
          :articolo-id="articoloId"
          :non-editable-fields="store.nonEditableFields"
          @saved="onSaved"
          @cancel="onCancel"
        />
      </template>
    </ListaConFormInline>
  </AppDrawer>
</template>
