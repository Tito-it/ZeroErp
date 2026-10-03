// Scopo: cuore condiviso dei form riga articolo (B11 2026-06-05, regola del 2).
//        OrdiniRigaForm e PreventiviRigaForm condividono questo nucleo "thin":
//        flag composito (isEdit/isCasoA/isPadreComposito), wiring UoM operative
//        (useArticoloUomOptions + uomLabel + autopick base in create), wiring
//        ComponentiDialog (useComponentiDialog) e submitRiga create/update.
//
// DELIBERATAMENTE thin: lo strato resolver listino + gate L2 + cella
// prezzo-listino + campo `ordine` di PreventiviRigaForm (superset), il `form`
// stesso (campo `ordine` solo preventivi; il drift sconto_perc/sconto_percentuale
// è stato sanato col rename DB 2026-06-05 → ora `sconto_percentuale` ovunque) e
// `canSave`/`buildPayload`/`handleSave` restano nei form di dominio.
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
//   showComponentiDialog, apriComponentiDialog, onComponentiConfirm, submitRiga,
//   fissa, modificato, chiudiConConferma, seguiRiga }
//
// ⭐ LA FOTOGRAFIA DELLA RIGA (2026-10-03, D-13 di
//    work-done/analisi-fe-chrome-drawer.md, ok Tid). Fino a quel giorno i
//    form di riga dei documenti non ne avevano una: la fotografia del drawer
//    copriva la sola testata, e una riga in compilazione si perdeva SENZA
//    DOMANDA cambiando riga o uscendo dal drawer. Sta qui, una volta per i tre
//    form che condividono il cuore: il form di dominio PIU' i componenti BoM
//    confermati nel dialog, che stanno fuori dal form ma partono col Salva.
//    Il form espone `modificato` e `chiudiConConferma` (`defineExpose`), e il
//    suo Annulla passa da `chiudiConConferma`.
//
// ⭐ `seguiRiga(popola)` — IL LEGAME FORM ↔ RIGA, una volta per i tre form
//    (2026-10-03, regola del 2, ok Tid). `popola(riga)` e' del dominio (che
//    campi, come si leggono; `riga` null = creazione); qui stanno le due
//    regole che non lo sono:
//    · la fotografia si fissa a riga caricata, dopo il giro di watch;
//    · la STESSA riga riletta dal server (`risincronizza` di useFormInline,
//      per esempio dopo che il pannello componenti ha salvato un prezzo) NON
//      ripopola un form modificato: fino a quel giorno qta e descrizione
//      scritte e non salvate tornavano ai valori del server, senza domanda.
//      Form pulito → si ripopola tutto; modificato → si tiene cio' che ha
//      scritto l'operatore, e si allinea solo il prezzo di un padre composito
//      (e' la somma dei componenti, scritta dal trigger: non si digita).
//    ⚠️ Il form la chiama DOVE scriverebbe il suo `watch(() => props.riga)`, in
//    fondo alle dichiarazioni che `popola` usa: il watch e' `immediate`.
//    ⚠️ `visibile` sempre vero: il form esiste solo mentre e' aperto (`v-if`
//    del contenitore), e allo smontaggio la fotografia se ne va con lui.

import { computed, nextTick, watch } from 'vue'
import { useDrawerFormPreserve } from '../../../core/composables/useDrawerFormPreserve'
import { useI18n } from 'vue-i18n'
import { useArticoloUomOptions } from '../../../catalogo/composables/useArticoloUomOptions'
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
    const base = uom.is_base ? ` ${t('vendite.listini.uom_base_suffix')}` : ''
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

  // ⚠️ Il form si fotografa APPIATTITO, campo per campo: annidato sotto una
  //    chiave, il confronto diventerebbe `JSON.stringify` dell'intero oggetto e
  //    perderebbe le regole del BB (`*_obj` ignorati, vuoti equivalenti, testi a
  //    meno degli spazi) — un `''` al posto di `null` direbbe «modificato».
  const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(
    computed(() => ({ ...form.value, componenti_confermati: componenti.componentiPayload.value })),
    { visibile: () => true },
  )

  function seguiRiga(popola) {
    watch(riga, (nuova, prima) => {
      const stessaRiga = nuova && prima && nuova.id === prima.id
      if (stessaRiga && modificato.value) {
        if (isPadreComposito.value) {
          form.value.prezzo_unitario = nuova.prezzo_unitario != null ? Number(nuova.prezzo_unitario) : null
        }
        return
      }
      popola(nuova)
      nextTick(() => fissa())
    }, { immediate: true })
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
    fissa,
    modificato,
    chiudiConConferma,
    seguiRiga,
  }
}
