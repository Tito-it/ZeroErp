<script setup>
// Scopo: Dialog BLOCCANTE della prima scelta dell'emittente di lavoro.
//        Compare solo a chi puo' scegliere e non ha mai scelto
//        (`deve_scegliere` da /me/): il super admin al primo accesso, o quello
//        la cui preferenza e' decaduta perche' l'emittente e' stato disattivato.
//
//        Perche' bloccante e non un avviso: senza emittente attivo si e' in
//        modalita' «Tutti gli emittenti», che e' di sola lettura — si
//        potrebbero compilare documenti fino in fondo e vederseli rifiutare
//        dal DB alla scrittura. Meglio chiedere prima che spiegare dopo.
//
//        Chi ha gia' scelto «Tutti» consapevolmente NON lo rivede: quel caso
//        ha `deve_scegliere = false` (lo distingue la preferenza salvata).
//
//        ⚠️ Un dialog bloccante DEVE avere sempre una via d'uscita, altrimenti
//        un errore di rete chiude l'utente fuori dall'applicazione. Qui le vie
//        sono tre: le opzioni caricate, il «riprova» se la chiamata fallisce,
//        e la chiusura esplicita che lascia in modalita' globale (sola
//        lettura, ma l'app resta usabile). Se poi gli emittenti selezionabili
//        sono zero, il dialog non compare affatto: non c'e' scelta da fare.

import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Select from 'primevue/select'
import ProgressSpinner from 'primevue/progressspinner'
import AppDialog from './AppDialog.vue'
import { useApiHandler } from '../composables/useApiHandler'
import { useAuthStore } from '../../stores/auth'
import { listEmittentiSelezionabili } from '../api/emittenteAttivo'

const { t } = useI18n()
const auth = useAuthStore()
const { execute } = useApiHandler()

const opzioni = ref([])
const scelto = ref(null)
const caricamento = ref(false)
const errore = ref(false)
const caricato = ref(false)
const inCorso = ref(false)
// Rinuncia esplicita dell'utente: resta in modalita' globale per questa
// sessione. Non tocca la preferenza lato server, quindi al prossimo accesso
// gli verra' richiesto di nuovo — e va bene: la scelta serve davvero.
const rimandato = ref(false)

const voci = computed(() =>
  opzioni.value.map(o => ({
    value: o.emittente_fiscale_id,
    label: o.ragione_sociale || o.codice
  }))
)

// Visibile finche' la scelta serve E non e' stata rimandata. Dopo il
// caricamento, zero opzioni = niente da scegliere → il dialog sparisce da se'
// invece di restare aperto e vuoto (il difetto trovato al primo accesso di
// Tid, 2026-08-04).
const visibile = computed(() => {
  if (!auth.deveScegliereEmittente || rimandato.value) return false
  if (caricato.value && !errore.value && voci.value.length === 0) return false
  return true
})

// Scopo: carica le opzioni. `immediate` nel watch e' obbligatorio: al mount di
//        AppLayout il profilo e' gia' in memoria, quindi `visibile` nasce gia'
//        `true` e un watch normale non scatterebbe MAI — la combo restava
//        vuota e il dialog senza uscita. Vedi memoria
//        `feedback_keepalive_onactivated`: lo stato iniziale va gestito, non
//        solo le sue transizioni.
async function carica() {
  caricamento.value = true
  errore.value = false
  try {
    opzioni.value = await listEmittentiSelezionabili()
    // Unico emittente disponibile: preselezionato. Resta comunque una
    // conferma esplicita — l'utente deve sapere dentro cosa sta entrando.
    if (opzioni.value.length === 1) {
      scelto.value = opzioni.value[0].emittente_fiscale_id
    }
  } catch {
    errore.value = true
    opzioni.value = []
  } finally {
    caricamento.value = false
    caricato.value = true
  }
}

watch(visibile, (aperto) => {
  if (aperto && !caricato.value && !caricamento.value) carica()
}, { immediate: true })

async function conferma() {
  if (scelto.value == null) return
  inCorso.value = true
  try {
    // Via `execute`, non chiamata nuda: un reject qui morirebbe come
    // unhandled rejection e il dialog resterebbe aperto senza spiegazione.
    await execute(
      () => auth.cambiaEmittenteAttivo(scelto.value),
      { errorMessage: t('core.emittente_attivo.cambio_errore') }
    )
  } finally {
    inCorso.value = false
  }
}
</script>

<template>
  <!-- `closable=false` + `closeOnEscape=false`: non e' una scelta rimandabile
       con un click distratto. La rinuncia esiste, ma e' un pulsante esplicito
       in footer che dichiara la conseguenza (sola lettura).
       AppDialog (BB obbligatorio per le dialog modali) con footer custom:
       tre bottoni — riprova / rimanda / conferma — fuori dal contratto
       Annulla/Salva del FormFooter integrato. -->
  <AppDialog
    :visible="visibile"
    width="sm"
    :closable="false"
    :close-on-escape="false"
    :header="t('core.emittente_attivo.scelta_titolo')"
  >
    <p class="mb-1">{{ t('core.emittente_attivo.scelta_messaggio') }}</p>

    <div v-if="caricamento" class="flex justify-content-center p-2">
      <ProgressSpinner style="width: 2.5rem; height: 2.5rem" />
    </div>

    <Message v-else-if="errore" severity="error" :closable="false">
      {{ t('core.emittente_attivo.scelta_errore') }}
    </Message>

    <Select
      v-else
      v-model="scelto"
      :options="voci"
      option-label="label"
      option-value="value"
      :placeholder="t('core.emittente_attivo.aria')"
      class="w-full"
      :disabled="inCorso"
    />

    <template #footer>
      <Button
        v-if="errore"
        :label="t('common.retry')"
        severity="secondary"
        outlined
        :loading="caricamento"
        @click="carica"
      />
      <!-- Via d'uscita sempre presente: l'app resta raggiungibile anche se
           questa scelta non si riesce a fare. -->
      <Button
        :label="t('core.emittente_attivo.scelta_rimanda')"
        severity="secondary"
        text
        :disabled="inCorso"
        @click="rimandato = true"
      />
      <Button
        :label="t('core.emittente_attivo.scelta_conferma')"
        :disabled="scelto == null || inCorso || errore"
        :loading="inCorso"
        @click="conferma"
      />
    </template>
  </AppDialog>
</template>
