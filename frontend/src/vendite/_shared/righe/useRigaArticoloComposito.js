// Scopo: cuore condiviso dei form riga articolo (B11 2026-06-05, regola del 2).
//        OrdiniRigaForm e PreventiviRigaForm condividono questo nucleo "thin":
//        flag composito (isEdit/isCasoA/isPadreComposito), wiring UoM operative
//        (useArticoloUomOptions + uomLabel + autopick base in create), wiring
//        ComponentiDialog (useComponentiDialog) e submitRiga create/update.
//
// DELIBERATAMENTE thin: lo strato resolver listino + gate L2 + cella
// prezzo-listino + campo `ordine` di PreventiviRigaForm (superset), il `form`
// stesso (i nomi campo divergono — vedi drift `sconto_perc`/`sconto_percentuale`,
// brief DB) e `canSave`/`buildPayload`/`handleSave` restano nei form di dominio.
// Un composable che possedesse tutto sarebbe un mega-config leaky
// (cfr. feedback_concentrico_no_yagni).
//
// Parametri:
//   store        store Pinia con addRiga(parentId, payload) / aggiornaRiga(parentId, rigaId, payload)
//   parentId     getter () => props.<ordineId|preventivoId>
//   riga         getter () => props.riga (null in create)
//   articoloObj  ref dell'articolo selezionato (letto per is_composito / isPadreComposito)
//   form         ref del form di dominio (passato a useComponentiDialog + autopick UoM)
//
// Ritorna: { isEdit, isCasoA, isPadreComposito, uomOptions, uomLoading,
//   loadUomPerArticolo, pickBaseUomId, resetUomOptions, uomLabel,
//   caricaUomConPickBase, componentiDialogVisible, componentiPayload,
//   showComponentiDialog, apriComponentiDialog, onComponentiConfirm, submitRiga }

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoloUomOptions } from '../../../core/composables/useArticoloUomOptions'
import { useComponentiDialog } from '../componenti/useComponentiDialog'

export function useRigaArticoloComposito({ store, parentId, riga, articoloObj, form }) {
  const { t } = useI18n()

  const isEdit = computed(() => riga() != null)
  // Riga padre composita CASO A: flag derivato dal BE list_righe (EXISTS su
  // *_righe_componenti attivi). In create il flag è undefined.
  const isCasoA = computed(() => isEdit.value && !!riga()?.is_composito_caso_a)
  // Unifica EDIT CASO A e CREATE composito: in entrambi il prezzo padre non è
  // rappresentativo (SUM componenti via trigger DB) → campo prezzo nascosto e
  // resolver del singolo articolo da non chiamare.
  const isPadreComposito = computed(
    () => isCasoA.value || articoloObj.value?.is_composito === true,
  )

  // UoM operative dell'articolo (BB centralizzato Fase 4.F1): solo quelle
  // definite a livello articolo, non l'intero catalogo.
  const { uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions } =
    useArticoloUomOptions()

  function uomLabel(uom) {
    const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
    return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
  }

  // Carica le UoM dell'articolo e, in create, pre-seleziona la base.
  async function caricaUomConPickBase(articoloId) {
    const list = await loadUomPerArticolo(articoloId)
    if (!isEdit.value && !form.value.uom_operativa_id) {
      form.value.uom_operativa_id = pickBaseUomId(list)
    }
  }

  // Dialog componenti BoM pre-save (CREATE composito): auto-open al primo set
  // articolo+UoM+qta validi; raccoglie gli override prezzi componente. In EDIT
  // lo stato componenti viaggia via il pannello di dominio.
  const componenti = useComponentiDialog({
    form,
    isCreate: () => !isEdit.value,
    isComposito: () => articoloObj.value?.is_composito === true,
    isPadreComposito: () => isPadreComposito.value,
  })

  // Le action dello store sono già unwrappate (ritornano res.data.data); non
  // passare da useApiHandler.execute (feedback_useapihandler_solo_axios).
  function submitRiga(payload) {
    return isEdit.value
      ? store.aggiornaRiga(parentId(), riga().id, payload)
      : store.addRiga(parentId(), payload)
  }

  return {
    isEdit,
    isCasoA,
    isPadreComposito,
    uomOptions,
    uomLoading,
    loadUomPerArticolo,
    pickBaseUomId,
    resetUomOptions,
    uomLabel,
    caricaUomConPickBase,
    ...componenti,
    submitRiga,
  }
}
