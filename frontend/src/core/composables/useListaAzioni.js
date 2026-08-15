// Scopo: le DUE azioni di utility che accompagnano ogni <ListaConfigurabile>
// — «Personalizza colonne» e «Esporta» — piu' lo stato che le governa
// (dirty/colonneNuove/configReady, dialog e download dell'export).
//
// Estratto 2026-08-15 alla 5ª occorrenza, non alla 2ª: vivevano dentro
// `useListaConfigurabilePage`, che pero' e' costruito su `useSearchTable` e
// quindi pretende uno store con la forma «ricerca testuale + sort + limit».
// I tre cruscotti (situazione aperta, backlog, competenza) sono pilotati da
// mese/stadio/card via `usePagedDashFetch` e quello scaffolding non lo possono
// usare: le loro CINQUE liste sarebbero rimaste senza personalizzazione ne'
// export, oppure con cinque copie delle stesse due azioni.
//
// Qui vive la parte che NON dipende dallo store; `useListaConfigurabilePage`
// la consuma a sua volta, cosi' le 37 viste standard e i cruscotti producono
// le stesse identiche azioni e non possono divergere.
//
// ⚠️ NON tocca colonne ne' ordinamento della lista a video: apre la modale di
// personalizzazione (che agisce sulla preferenza dell'operatore, non sul
// catalogo) e legge la configurazione per l'export. Una lista che non offriva
// queste azioni continua a rendersi identica finche' l'operatore non decide
// diversamente.
//
// Uso:
//   const { azioniLista, exportDialogVisible, exportLoading, onExportConfirm }
//     = useListaAzioni(() => listaRef.value, {
//         exportFn: exportDashboardBacklogDocumenti,
//         getExportParams: (formato) => ({ formato, ...filtriCorrenti() }),
//       })
//
// `listaGetter` e' una FUNZIONE e non un ref: le pagine con piu' liste (il
// cruscotto competenza ne ha tre) devono poter puntare a quella VISIBILE in
// quel momento, altrimenti il pulsante personalizzerebbe una lista che
// l'operatore non sta guardando.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFileDownload } from './useFileDownload'
import { MANAGE_ICONS } from '../constants'

export function useListaAzioni(
  listaGetter,
  { exportFn = null, getExportParams = () => ({}) } = {},
) {
  const { t } = useI18n()

  // defineExpose auto-unwrappa i ref: niente `.value` extra sui campi esposti.
  const lista = computed(() => (typeof listaGetter === 'function' ? listaGetter() : listaGetter?.value))
  const dirty = computed(() => lista.value?.dirty ?? false)
  const colonneNuove = computed(() => lista.value?.colonneNuove ?? 0)
  const configReady = computed(() => lista.value?.config != null)

  // Export DEF-1: scarica CSV/Excel con i filtri attualmente applicati.
  // ⚠️ `useFileDownload` bypassa `useApiHandler` di proposito (un blob non e'
  // un envelope JSON e l'handler lo romperebbe).
  const { download, loading: exportLoading } = useFileDownload()
  const exportDialogVisible = ref(false)

  // Scopo: esegue il download nel formato scelto e chiude il dialog solo se
  //        e' andato a buon fine (`!== null`, non `truthy`: un blob vuoto e'
  //        un esito valido).
  async function onExportConfirm(formato) {
    if (typeof exportFn !== 'function') return
    const result = await download(
      () => exportFn(getExportParams(formato)),
      { successMessage: t('lista_config.export_success') },
    )
    if (result !== null) exportDialogVisible.value = false
  }

  // Le due azioni, nella forma attesa da PageActionsBar. `export` e'
  // condizionata al proprio handler: senza `exportFn` il pulsante aprirebbe un
  // dialog che non scarica niente.
  const azioniLista = computed(() => {
    const personalizzaLabel = t('lista_config.personalizza_colonne')
    const azioni = [
      {
        key: 'personalizza-colonne',
        kind: 'utility',
        label: colonneNuove.value > 0
          ? `${personalizzaLabel} (${colonneNuove.value})`
          : personalizzaLabel,
        tooltip: colonneNuove.value > 0
          ? t('lista_config.colonne_nuove_disponibili', { n: colonneNuove.value })
          : personalizzaLabel,
        icon: MANAGE_ICONS.PERSONALIZZA,
        // Finche' la config non e' arrivata non c'e' nulla da personalizzare:
        // meglio spento che una modale vuota.
        disabled: !configReady.value,
        command: () => lista.value?.openModal?.(),
      },
    ]
    if (typeof exportFn === 'function') {
      azioni.push({
        key: 'export',
        kind: 'utility',
        label: t('lista_config.export'),
        tooltip: t('lista_config.export_tooltip'),
        icon: MANAGE_ICONS.DOWNLOAD,
        disabled: exportLoading.value,
        command: () => { exportDialogVisible.value = true },
      })
    }
    return azioni
  })

  return {
    dirty,
    colonneNuove,
    configReady,
    exportDialogVisible,
    exportLoading,
    onExportConfirm,
    azioniLista,
  }
}
