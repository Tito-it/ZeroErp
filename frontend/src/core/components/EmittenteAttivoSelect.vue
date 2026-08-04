<script setup>
// Scopo: Combo dell'EMITTENTE ATTIVO in topbar — «dentro quale emittente sto
//        lavorando» (impersonazione di scope). Visibile solo a chi puo'
//        scegliere: l'operatore ha il suo emittente per permesso e vede il
//        nome come testo, esattamente come prima.
//
//        Cambiare emittente cambia cio' che si vede in TUTTA l'applicazione,
//        quindi il componente:
//          1. chiede conferma, dichiarando che le schede aperte si chiudono —
//             e se ce ne sono di modificate lo dice con il loro numero, perche'
//             «perderai le modifiche» senza sapere quante non aiuta a decidere;
//          2. delega allo store, che sostituisce i token e riparte dal boot.
//
//        La voce «Tutti gli emittenti» e' la modalita' di sola lettura: si
//        vede tutto e non si crea nulla (il DB non saprebbe quale emittente
//        scrivere sui documenti). Va detto nella conferma, non scoperto dopo.

import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import { useAuthStore } from '../../stores/auth'
import { useTabsStore } from '../../stores/tabs'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useApiHandler } from '../composables/useApiHandler'
import { listEmittentiSelezionabili } from '../api/emittenteAttivo'

const { t } = useI18n()
const auth = useAuthStore()
const tabs = useTabsStore()
const { confirmAction } = useConfirmAction()
const { execute } = useApiHandler()

const opzioni = ref([])
const inCorso = ref(false)

// Valore sentinella della voce «Tutti gli emittenti». Non e' un id: il BE
// riceve `null` e rimuove il claim. Un id finto (0, -1) sarebbe finito prima o
// poi in una query.
const TUTTI = '__TUTTI__'

const valoreCorrente = computed(
  () => auth.emittenteAttivo?.emittente_fiscale_id ?? TUTTI
)

// Opzioni della combo + la voce globale in testa. `disabled` durante il cambio
// evita il doppio switch mentre la pagina si sta gia' ricaricando.
const voci = computed(() => [
  { value: TUTTI, label: t('core.emittente_attivo.tutti') },
  ...opzioni.value.map(o => ({
    value: o.emittente_fiscale_id,
    label: o.ragione_sociale || o.codice
  }))
])

onMounted(async () => {
  if (!auth.puoScegliereEmittente) return
  const esito = await execute(() => listEmittentiSelezionabili())
  if (esito !== null) opzioni.value = esito
})

// Scopo: conferma e applica il cambio. Il messaggio nomina l'emittente di
//        destinazione: «confermi?» da solo non dice cosa si sta per fare.
function onCambio(nuovoValore) {
  if (nuovoValore === valoreCorrente.value) return
  const versoGlobale = nuovoValore === TUTTI
  const destinazione = versoGlobale
    ? t('core.emittente_attivo.tutti')
    : (voci.value.find(v => v.value === nuovoValore)?.label ?? '')
  const schedeSporche = tabs.hasDirtyTabs()
    ? tabs.tabs.filter(x => x.dirty).length
    : 0

  confirmAction({
    title: t('core.emittente_attivo.conferma_titolo'),
    message: [
      versoGlobale
        ? t('core.emittente_attivo.conferma_globale')
        : t('core.emittente_attivo.conferma_emittente', { nome: destinazione }),
      schedeSporche > 0
        ? t('core.emittente_attivo.conferma_schede_modificate', { n: schedeSporche })
        : t('core.emittente_attivo.conferma_schede')
    ].join(' '),
    onAccept: async () => {
      inCorso.value = true
      try {
        // Via `execute`, non chiamata nuda: dentro `onAccept` un reject
        // muore silenzioso (memoria feedback_useconfirmaction_destructuring)
        // e l'utente vedrebbe la combo tornare indietro senza spiegazione.
        await execute(
          () => auth.cambiaEmittenteAttivo(versoGlobale ? null : nuovoValore),
          { errorMessage: t('core.emittente_attivo.cambio_errore') }
        )
      } finally {
        inCorso.value = false
      }
    }
  })
}
</script>

<template>
  <!-- Chi non sceglie vede il nome, come prima dell'impersonazione. -->
  <span v-if="!auth.puoScegliereEmittente" class="topbar-company">
    {{ auth.emittenteCorrente?.ragioneSociale || '' }}
  </span>

  <template v-else>
    <Select
      :model-value="valoreCorrente"
      :options="voci"
      option-label="label"
      option-value="value"
      :disabled="inCorso"
      class="topbar-emittente-select"
      :pt="{ root: { 'aria-label': t('core.emittente_attivo.aria') } }"
      @update:model-value="onCambio"
    />

    <!-- Modalità globale: si vede tutto e non si crea nulla. L'avviso sta
         QUI, accanto alla causa, e non dentro i drawer: il vincolo nasce
         dalla scelta in topbar, ed è lì che va spiegato. Il rifiuto vero
         resta del DB (`*_EMITTENTE_NON_RISOLTO`), i cui messaggi sono stati
         riscritti per rimandare a questa combo. -->
    <i
      v-if="auth.isModalitaGlobale"
      v-tooltip.bottom="t('core.emittente_attivo.globale_sola_lettura')"
      class="pi pi-eye topbar-emittente-globale"
      :aria-label="t('core.emittente_attivo.globale_sola_lettura')"
    ></i>
  </template>
</template>

<style scoped>
/* Combo in topbar: deve leggersi come un'etichetta, non come un campo di
   form — il bordo pieno di un Select su fondo scuro pesa troppo per un
   elemento sempre presente. */
.topbar-emittente-select {
  max-width: 16rem;
  background: transparent;
  border-color: var(--app-topbar-border, transparent);
  font-weight: 600;
}

/* Segnale di modalità globale: informativo, non allarmante — vedere tutto
   è una scelta legittima, non un errore. */
.topbar-emittente-globale {
  margin-left: 0.4rem;
  color: var(--app-color-info, var(--p-primary-color));
  cursor: help;
}
</style>
