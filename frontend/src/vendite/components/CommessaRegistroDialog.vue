<script setup>
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: Vue
// Scopo: il REGISTRO di una riga di commessa — «perché questa riga è così».
// ------------------------------------------------------------
//
// ⛔ PERCHÉ ESISTE. Fino al 2026-08-28 `vendite.commesse_attivita_log` si
//    SCRIVEVA e non si LEGGEVA: sei tipi di evento — oneri aggiunti, righe
//    annullate a mano, ritirate alla chiusura del documento di origine,
//    riportate da emettere, accrediti — registrati fedelmente dal database e
//    irraggiungibili da qualunque schermata. La guida operativa prometteva il
//    contrario. Trovato in collaudo: una riga passata ad ANNULLATA da sé, e
//    nessun modo di sapere perché.
//
// ⭐ La domanda che questo pannello risponde è **di riga**, non di commessa: si
//    apre dal kebab della riga e mostra la sua storia. L'endpoint accetta anche
//    la commessa intera — qui si passa sempre `commessaAttivitaId`, perché
//    «cosa è successo a QUESTA riga» è la domanda che l'operatore ha in mente
//    quando vede uno stato che non si aspettava.
//
// ⚠️ Il vocabolario degli eventi è del DATABASE ed è aperto. `labelOrCode`:
//    un evento nuovo si mostra col proprio codice invece di sparire, e nessuna
//    lista chiusa vive qui.
//
// ⭐ La RESA è del BB `core/components/GiornaleEventi.vue` (estratto il
//    2026-08-28 alla seconda occorrenza, la prima è il giornale delle pratiche).
//    Qui restano le tre cose che sono di QUESTO dominio: da dove arrivano gli
//    eventi, come si chiamano, e che forma ha la riga di dettaglio.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../core/components/AppDialog.vue'
import GiornaleEventi from '../../core/components/GiornaleEventi.vue'
import { listCommessaRegistro } from '../api/commesse'
import { eventoRegistroCommessaStyle } from '../../core/utils/severity'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { extractApiError } from '../../core/utils/apiError'
import { useNotify } from '../../core/composables/useNotify'

const props = defineProps({
  visible: { type: Boolean, default: false },
  commessaId: { type: Number, default: null },
  commessaAttivitaId: { type: Number, default: null },
})
const emit = defineEmits(['update:visible'])

const { t, te } = useI18n()
const notify = useNotify()

const eventi = ref([])
const loading = ref(false)
// ⚠️ `caricato` e non `!loading`: un empty-state positivo su una fetch mai
//    riuscita direbbe «non è successo niente» quando invece non lo sappiamo.
const caricato = ref(false)


// Scopo: l'etichetta dell'evento, con ripiego sul codice grezzo.
function eventoLabel(evento) {
  return labelOrCode(
    t, te,
    `vendite.commesse.registro_evento.${String(evento || '').toLowerCase()}`,
    evento,
  )
}

// Scopo: la riga di dettaglio sotto l'evento.
// ⭐ Il `motivo` per primo e da solo se c'è: è la frase scritta da una persona o
//    dal database per spiegare il gesto, ed è quello che si sta cercando.
// ⚠️ Il resto del payload NON si appiattisce in automatico: ogni evento ha una
//    forma sua, e stampare `chiave: valore` su tutto produrrebbe righe di id
//    tecnici che non dicono niente. Si nominano i pochi campi leggibili.
function dettaglioLeggibile(ev) {
  const parti = []
  if (ev.motivo) parti.push(ev.motivo)
  const d = ev.dettaglio && typeof ev.dettaglio === 'object' ? ev.dettaglio : {}
  if (d.stato_precedente) {
    parti.push(`${t('vendite.commesse.registro_stato_precedente')}: ${d.stato_precedente}`)
  }
  if (d.importo != null) {
    parti.push(`${t('vendite.commesse.registro_importo')}: ${d.importo}`)
  }
  return parti.join(' — ')
}

async function carica() {
  if (!props.commessaId) return
  loading.value = true
  try {
    const res = await listCommessaRegistro(props.commessaId, {
      commessa_attivita_id: props.commessaAttivitaId ?? undefined,
      limit: 100,
    })
    eventi.value = res.data?.data?.rows ?? []
    caricato.value = true
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    loading.value = false
  }
}

// ⚠️ Si ricarica ogni volta che il pannello si apre, e non una volta sola: fra
//    un'apertura e l'altra la riga può aver cambiato storia (un collega la
//    annulla, un giro la riporta). Un registro che mostra il minuto prima è
//    peggio di nessun registro.
watch(
  () => [props.visible, props.commessaAttivitaId],
  ([visible]) => {
    if (!visible) return
    eventi.value = []
    caricato.value = false
    carica()
  },
  { immediate: true },
)
</script>

<template>
  <!-- `AppDialog` di sola chiusura (2026-09-18: era l'ultimo `Dialog` grezzo
       del frontend, con `46rem` fuori scala). `lg` e' la taglia dei registri. -->
  <AppDialog
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    :header="t('vendite.commesse.registro_header')"
    width="lg"
    close-only
  >
    <GiornaleEventi
      :eventi="eventi"
      :loading="loading"
      :caricato="caricato"
      campo-codice="evento"
      :etichetta="eventoLabel"
      :stile="eventoRegistroCommessaStyle"
      :dettaglio="dettaglioLeggibile"
      :testo-vuoto="t('vendite.commesse.registro_vuoto')"
      :testo-placeholder="t('vendite.commesse.registro_placeholder')"
    />
  </AppDialog>
</template>
