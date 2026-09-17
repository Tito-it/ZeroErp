<script setup>
// Scopo: Tab giornale (audit log) dentro il drawer pratica.
// Timeline cronologica inversa degli eventi sulla pratica.
//
// ⭐ Dal 2026-08-28 la resa NON vive più qui: è il BB `core/components/GiornaleEventi.vue`,
//    estratto alla seconda occorrenza (registro delle righe di commessa, ok Tid).
//    Questo file possiede ciò che è delle PRATICHE — la fetch, il vocabolario
//    delle azioni, la forma del dettaglio — e niente altro.
//    ⚠️ Il comportamento non cambia: il BB nasce con `caricato` a `true` di
//    default, che è esattamente ciò che questo tab faceva prima.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchGiornale } from '../api/pratiche-api'
import { azioneGiornaleStyle } from '../../core/utils/severity'
import { labelOrCode } from '../../core/utils/i18nLabel'
import GiornaleEventi from '../../core/components/GiornaleEventi.vue'

const { t, te } = useI18n()

const props = defineProps({
  praticaId: { type: Number, required: true }
})

const eventi = ref([])
const loading = ref(false)

// Scopo: label leggibile dell'azione (i18n) con fallback al codice grezzo se la
// chiave non esiste (codici nuovi a DB non ancora tradotti restano comunque visibili).
function azioneLabel(azione) {
  const key = `pratiche.giornale_azioni.${azione}`
  return labelOrCode(t, te, key, azione)
}

// Scopo: Formatta il dettaglio in testo leggibile. Usa i display fields decodificati
// dal BE (transizione stati, descrizione flusso) invece degli id grezzi del jsonb.
function formatDettaglio(ev) {
  const parts = []
  // Transizione di stato: descrizioni decodificate lato BE (FLUSSO_STATO_CAMBIATO).
  if (ev.dettaglio_stato_nuovo) {
    parts.push(ev.dettaglio_stato_precedente
      ? `${ev.dettaglio_stato_precedente} → ${ev.dettaglio_stato_nuovo}`
      : ev.dettaglio_stato_nuovo)
  }
  const d = ev.dettaglio && typeof ev.dettaglio === 'object' ? ev.dettaglio : {}
  if (d.esito) parts.push(`${t('pratiche.flusso_col_esito')}: ${d.esito}`)
  if (d.motivo) parts.push(d.motivo)
  if (d.note_esito) parts.push(d.note_esito)
  return parts.join(' — ')
}

async function loadGiornale() {
  loading.value = true
  try {
    const res = await fetchGiornale(props.praticaId, { limit: 100 })
    eventi.value = res.data.data.results || []
  } finally {
    loading.value = false
  }
}

watch(() => props.praticaId, (id) => {
  if (id) loadGiornale()
}, { immediate: true })
</script>

<template>
  <GiornaleEventi
    :eventi="eventi"
    :loading="loading"
    campo-codice="azione"
    :etichetta="azioneLabel"
    :stile="azioneGiornaleStyle"
    :dettaglio="formatDettaglio"
    :testo-vuoto="t('pratiche.giornale_vuoto')"
  >
    <!-- Il flusso di appartenenza: informazione delle sole pratiche. -->
    <template #voce-extra="{ evento }">
      <span v-if="evento.flusso_template_descrizione" class="giornale-flusso">
        {{ evento.flusso_template_descrizione }}
      </span>
    </template>
  </GiornaleEventi>
</template>

<style scoped>
.giornale-flusso {
  font-size: var(--app-font-size-sm);
  font-weight: 600;
  color: var(--app-text-color);
}
</style>
