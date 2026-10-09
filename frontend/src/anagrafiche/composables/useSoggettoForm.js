// Scopo: Composable universale per form soggetto PF/PG/ENTE.
// Gestisce tipo soggetto, campi condizionali (natura), matrice indirizzi,
// validazione e reset. Guidato dalla matrice DB tipi_soggetto_dettaglio.

import { reactive, ref, computed, watch } from 'vue'
import { useLookup } from '../../core/composables/useLookup'
import { lookupTipiSoggettoDettaglio, lookupMatriceIndirizzi } from '../../core/apiCore'

// Il sesso che il form PROPONE a video a un privato in creazione: una proposta
// visibile, mai un default scritto senza che nessuno l'abbia visto.
const SESSO_PROPOSTO = 'M'

export function useSoggettoForm(options = {}) {
  // `proponiSesso`: getter, vero quando il form puo' PROPORRE il sesso (in
  // creazione). In modifica no: un privato senza sesso (dato storico) resta
  // vuoto, e il guard del DB chiede a chi lo vede di sceglierlo.
  const { tipoForzato = null, proponiSesso = () => true } = options

  const form = reactive({
    tipo_soggetto_dettaglio_id: tipoForzato || null,
    // PF
    cognome: '',
    nome: '',
    // ⛔ Nessun default (brief-db-sesso-senza-default, 2026-10-09): se la
    //    natura lo pretende il form lo PROPONE, a video (watch sotto).
    sesso: '',
    data_nascita: null,
    comune_nascita_id: null,
    // PG
    ragione_sociale: '',
    // Comuni PF/PG
    codice_fiscale: '',
    partita_iva: '',
    // Regime fiscale della controparte (I0/D8, 2026-08-29): saliti da
    // `anagrafiche.clienti`, che li teneva su una riga PER FORNITURA — lo stesso
    // soggetto poteva dichiarare valori opposti per gas e acqua. Un ente E' o
    // NON E' una Pubblica Amministrazione.
    // ⚠️ Default 'N', e la direzione e' una decisione: un soggetto di cui
    //    nessuno ha detto nulla NON e' in scissione dei pagamenti — dichiararlo
    //    tale d'ufficio produrrebbe fatture sbagliate su tutta l'anagrafica.
    split_payment: 'N',
    cliente_pa: 'N'
  })

  // Lookup tipi soggetto dettaglio
  const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio, { immediate: true })

  // Tipo corrente selezionato (con safe access)
  const tipoCorrente = computed(() =>
    tipiSoggetto.items.value.find(t => t.id === form.tipo_soggetto_dettaglio_id) || null
  )

  const isPF = computed(() => tipoCorrente.value?.natura_soggetto === 'PF')
  const showPartitaIva = computed(() => !!tipoCorrente.value?.piva_obbligatoria)
  const showDatiSocietari = computed(
    () => tipoCorrente.value?.dati_societari_policy != null
      && tipoCorrente.value.dati_societari_policy !== 'NONE'
  )
  const requireDatiSocietari = computed(
    () => tipoCorrente.value?.dati_societari_policy === 'REQUIRED'
  )
  // Sesso: QUANDO serve lo dice la natura (`sesso_policy`, in config), la
  // regola la presidia il guard del DB. REQUIRED (privato) -> obbligatorio;
  // OPTIONAL (ditta individuale) -> facoltativo, il vuoto e' onesto;
  // NONE (societa', enti) -> il campo non c'e'.
  const sessoPolicy = computed(() => tipoCorrente.value?.sesso_policy ?? null)
  const showSesso = computed(() => sessoPolicy.value != null && sessoPolicy.value !== 'NONE')
  const requireSesso = computed(() => sessoPolicy.value === 'REQUIRED')

  // ⭐ La proposta e' VISIBILE e si ritira se non serve piu': passando da
  //    privato a ditta individuale l'«M» proposto (non scelto) torna vuoto. Un
  //    valore scelto da chi lo vede non si tocca, salvo dove il sesso non si
  //    indica (NONE), che lo vieta.
  // ⚠️ `flush: 'sync'`: il drawer fa `reset()` e poi rimette lo STESSO tipo di
  //    default; con il flush differito la policy risulterebbe invariata, e alla
  //    seconda creazione l'«M» non verrebbe piu' proposto.
  // ⚠️ `immediate`: con `tipoForzato` e il lookup gia' in cache la policy e'
  //    REQUIRED dal primo istante e non CAMBIA mai: senza, nessuna proposta.
  let sessoProposto = null
  watch(sessoPolicy, (policy) => {
    if (policy === 'NONE') {
      form.sesso = ''
    } else if (policy === 'REQUIRED' && !form.sesso && proponiSesso()) {
      form.sesso = SESSO_PROPOSTO
      sessoProposto = SESSO_PROPOSTO
      return
    } else if (policy !== 'REQUIRED' && sessoProposto && form.sesso === sessoProposto) {
      form.sesso = ''
    }
    sessoProposto = null
  }, { flush: 'sync', immediate: true })

  // Matrice indirizzi: ricaricata al cambio tipo
  const matriceIndirizzi = ref([])
  const indirizziObbligatori = computed(
    () => matriceIndirizzi.value.filter(m => m.obbligatorio)
  )

  watch(() => form.tipo_soggetto_dettaglio_id, async (id) => {
    if (!id) {
      matriceIndirizzi.value = []
      return
    }
    try {
      const res = await lookupMatriceIndirizzi(id)
      matriceIndirizzi.value = res.data.data.results
    } catch {
      matriceIndirizzi.value = []
    }
  })

  // Scopo: Validazione campi in base al tipo corrente.
  function validate() {
    const errors = []
    if (!tipoForzato && !form.tipo_soggetto_dettaglio_id) errors.push('tipo_soggetto_dettaglio_id')

    if (isPF.value) {
      if (!form.cognome.trim()) errors.push('cognome')
      if (!form.nome.trim()) errors.push('nome')
      if (requireSesso.value && !form.sesso) errors.push('sesso')
    } else {
      if (!form.ragione_sociale.trim()) errors.push('ragione_sociale')
    }

    if (!form.codice_fiscale.trim()) errors.push('codice_fiscale')
    if (showPartitaIva.value && !form.partita_iva.trim()) errors.push('partita_iva')

    return errors
  }

  // Scopo: Reset form ai valori iniziali.
  function reset() {
    form.tipo_soggetto_dettaglio_id = tipoForzato || null
    form.cognome = ''
    form.nome = ''
    form.sesso = ''
    sessoProposto = null
    form.data_nascita = null
    form.comune_nascita_id = null
    form.ragione_sociale = ''
    form.codice_fiscale = ''
    form.partita_iva = ''
    form.split_payment = 'N'
    form.cliente_pa = 'N'
    matriceIndirizzi.value = []
  }

  return {
    form,
    tipiSoggetto,
    tipoCorrente,
    isPF,
    showPartitaIva,
    showDatiSocietari,
    requireDatiSocietari,
    showSesso,
    requireSesso,
    matriceIndirizzi,
    indirizziObbligatori,
    validate,
    reset
  }
}
