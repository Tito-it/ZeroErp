<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Sopra la lista Modelli documento, con che cosa stampa ogni azienda
//        (brief-db-modelli-documento-standard §6 e §11 F-1): dove un'azienda
//        usa il modello STANDARD, e dove la stampa si FERMA perche' l'azienda
//        ha modelli suoi ma nessuno predefinito (strada B: lo standard non
//        entra), o perche' non stampa nemmeno lo standard.
//
// ⭐ L'esito e' del DB (`GET /documenti/templates/risoluzione/`, la vista
//    `vw_template_risoluzione_emittente`, la stessa regola della stampa): qui
//    si raggruppa per azienda e si dice in parole. Nessuna regola ricopiata.
// ⭐ Due pesi diversi, e si vedono: cio' che ferma la stampa e' un avviso per
//    riga (azienda + documento, col rimedio); l'uso dello standard e' un fatto,
//    una riga per azienda in un solo riquadro informativo.
// ⚠️ Un pannello, non una lista: le righe sono le aziende del perimetro per i
//    documenti che hanno un modello, e la regola zero delle liste
//    (`<ListaConfigurabile>`) vale per gli elenchi di record, non per questo
//    riassunto.
// ⚠️ Si rilegge quando il chiamante lo chiede (`aggiorna`: dopo un salvataggio
//    o una personalizzazione cambia l'esito) e a ogni riattivazione sotto
//    KeepAlive (un'altra tab puo' aver cambiato i modelli).
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { listRisoluzioneTemplate } from '../api/templateDocumenti'

const props = defineProps({
  // Un contatore: ogni volta che cambia, il pannello rilegge.
  aggiorna: { type: Number, default: 0 },
})

const { t } = useI18n()
const { execute } = useApiHandler()
const righe = ref([])

// Una lettura alla volta: mount e prima attivazione sotto KeepAlive arrivano
// insieme, e due risposte in volo potrebbero arrivare in ordine inverso.
// ⚠️ Una richiesta arrivata con una lettura in volo (un salvataggio subito
//    dopo il mount) non si perde: la lettura in volo e' partita PRIMA del
//    salvataggio, quindi a fine volo se ne fa un'altra.
let inVolo = null
let daRileggere = false
async function carica() {
  if (inVolo) {
    daRileggere = true
    return inVolo
  }
  inVolo = (async () => {
    do {
      daRileggere = false
      const dati = await execute(() => listRisoluzioneTemplate())
      if (dati !== null) righe.value = dati?.results ?? []
    } while (daRileggere)
  })()
  try {
    await inVolo
  } finally {
    inVolo = null
  }
}

onMounted(carica)
onActivated(carica)
watch(() => props.aggiorna, carica)

// Scopo: il nome di un documento a video: il tipo, con la sorgente fra
//        parentesi (lo stesso tipo puo' avere due sorgenti).
function documento(riga) {
  return `${riga.tipo_documento_output_descrizione} (${riga.sorgente_tipo_descrizione})`
}

function azienda(riga) {
  return riga.emittente_ragione_sociale || riga.emittente_fiscale_codice
}

// Cio' che ferma la stampa: una riga per azienda e documento.
const ferme = computed(() =>
  righe.value.filter((r) => r.esito === 'SENZA_PREDEFINITO' || r.esito === 'NON_RISOLTO'),
)

// Chi stampa con lo standard: una riga per azienda, coi documenti.
const conStandard = computed(() => {
  const perAzienda = new Map()
  for (const r of righe.value) {
    if (r.esito !== 'STANDARD') continue
    const voce = perAzienda.get(r.emittente_fiscale_id)
      ?? { emittenteFiscaleId: r.emittente_fiscale_id, azienda: azienda(r), documenti: [] }
    voce.documenti.push(documento(r))
    perAzienda.set(r.emittente_fiscale_id, voce)
  }
  return [...perAzienda.values()]
})
</script>

<template>
  <div v-if="ferme.length || conStandard.length" class="template-risoluzione">
    <Message
      v-for="r in ferme"
      :key="`${r.emittente_fiscale_id}-${r.tipo_documento_output_id}-${r.sorgente_tipo_id}`"
      :severity="r.esito === 'NON_RISOLTO' ? 'error' : 'warn'"
      :closable="false"
    >
      {{ t(`config.modelli_documenti.risoluzione.${r.esito}`, {
        azienda: azienda(r), documento: documento(r),
      }) }}
    </Message>
    <Message v-if="conStandard.length" severity="info" :closable="false">
      <div>{{ t('config.modelli_documenti.risoluzione.titolo_standard') }}</div>
      <ul class="template-risoluzione-elenco">
        <li v-for="voce in conStandard" :key="voce.emittenteFiscaleId">
          <strong>{{ voce.azienda }}</strong>: {{ voce.documenti.join(', ') }}
        </li>
      </ul>
    </Message>
  </div>
</template>

<style scoped>
.template-risoluzione {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
  margin-bottom: var(--app-space-sm);
}
.template-risoluzione-elenco {
  margin: 0.25rem 0 0;
  padding-left: 1.25rem;
}
</style>
