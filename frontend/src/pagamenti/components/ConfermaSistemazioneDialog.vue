<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CONFERMA DI UNA SISTEMAZIONE — il momento in cui una decisione
//        registrata diventa un fatto e il denaro si muove.
//
// ⚠️ REGISTRARE NON E' ESEGUIRE, e il controllo dell'eccedenza sta QUI: fra il
//    momento in cui si decide e quello in cui si conferma puo' essere arrivato
//    un altro incasso. Verificarlo alla registrazione darebbe una garanzia che
//    scade.
//
// ⭐ IL CANALE SI CHIEDE SOLO SUL RIMBORSO, e si chiede adesso: «da quale conto
//    esce il bonifico» e' una decisione del momento in cui si paga, non della
//    settimana scorsa. ⛔ Sulle altre due destinazioni non si chiede, e non e'
//    una comodita': il denaro non esce, quindi non c'e' nessun conto da cui
//    farlo uscire — offrire il campo suggerirebbe una scelta inesistente.
//
// ⛔ Da CONFERMATA non si torna: il denaro si e' gia' mosso, e la correzione e'
//    una sistemazione NUOVA. Lo si dice PRIMA.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Select from 'primevue/select'

import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { confermaSistemazione } from '../api/pagamenti'
import { useCanaliIncasso } from '../composables/useCanaliIncasso'
import { useEtichettePagamenti } from '../etichette'
import { formatCurrency } from '../../core/utils/format'
import { DESTINAZIONE_CON_CANALE } from '../vocabolari'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  sistemazione: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'confermata'])

const { t } = useI18n()
const { execute, loading } = useApiHandler()
// ⚠️ Fail-visible: una destinazione nuova si legge come CODICE, non come il
//    percorso di una chiave i18n — che a video sembrerebbe un guasto.
const { destinazione: etichettaDestinazione } = useEtichettePagamenti()

// ⛔ «Caricati e vuoti» e «non caricati» non sono la stessa cosa, e a video si
//    somigliano: una fetch fallita direbbe «nessun canale configurato», che e'
//    un'affermazione — e falsa. I tre stati li tiene il BB.
const {
  canali,
  caricati: canaliCaricati,
  errore: erroreCanali,
  carica: caricaCanali,
  azzera: azzeraCanali,
  loading: caricamentoCanali,
} = useCanaliIncasso()
const enteIncassoId = ref(null)

const serveCanale = computed(
  () => props.sistemazione?.destinazione === DESTINAZIONE_CON_CANALE,
)

// ⚠️ Il canale e' OBBLIGATORIO solo dove serve. Su rimborso lo pretende la
//    funzione madre; altrove chiederlo sarebbe un ostacolo inventato.
const canSave = computed(() => !serveCanale.value || enteIncassoId.value != null)

watch(() => props.visible, async (aperto) => {
  enteIncassoId.value = null
  azzeraCanali()
  // ⚠️ I canali si chiedono SOLO dove servono: sulle altre due destinazioni il
  //    denaro non esce, e una chiamata inutile e' anche un errore possibile.
  if (!aperto || !serveCanale.value) return
  await caricaCanali()
})

async function onConferma() {
  const payload = {}
  if (serveCanale.value && enteIncassoId.value != null) {
    payload.ente_incasso_id = enteIncassoId.value
  }
  const esito = await execute(
    () => confermaSistemazione(props.sistemazione.id, payload),
    { successMessage: t('pagamenti.sistemazioni.confermata') },
  )
  if (esito === null) return
  emit('confermata', esito)
  emit('update:visible', false)
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ enteIncassoId: enteIncassoId.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t('pagamenti.sistemazioni.conferma_titolo')"
    width="md"
    :loading="loading || caricamentoCanali"
    :save-disabled="!canSave"
    :save-label="t('pagamenti.sistemazioni.conferma_azione')"
    save-severity="danger"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onConferma"
    @cancel="emit('update:visible', false)"
  >
    <div v-if="sistemazione" class="form-grid">
      <!-- ⛔ Si dice che non si torna indietro, e si dice PRIMA. -->
      <Message severity="warn" :closable="false">
        {{ t('pagamenti.sistemazioni.conferma_irreversibile') }}
      </Message>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('pagamenti.sistemazioni.col_destinazione') }}</label>
          <span>{{ etichettaDestinazione(sistemazione.destinazione) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.sistemazioni.col_importo') }}</label>
          <span>{{ formatCurrency(sistemazione.importo) }}</span>
        </div>
      </div>

      <!-- ⭐ Solo sul rimborso: e' l'unica destinazione in cui il denaro ESCE. -->
      <div v-if="serveCanale" class="form-field">
        <label>{{ t('pagamenti.sistemazioni.campo_canale') }}</label>
        <Select
          v-model="enteIncassoId"
          :options="canali"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('pagamenti.sistemazioni.campo_canale_placeholder')"
          :disabled="!canali.length"
        />
        <small class="app-text-muted">{{ t('pagamenti.sistemazioni.canale_aiuto') }}</small>
        <Message v-if="erroreCanali" severity="warn" :closable="false" size="small">
          {{ t('pagamenti.sistemazioni.canali_non_letti') }}
        </Message>
        <Message
          v-else-if="canaliCaricati && !canali.length"
          severity="info"
          :closable="false"
          size="small"
        >
          {{ t('pagamenti.sistemazioni.nessun_canale') }}
        </Message>
      </div>
    </div>
  </AppDialog>
</template>
