<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CORREZIONE GUIDATA (Q-7) — da una distinta registrata nasce una
//        distinta nuova con le righe di segno opposto gia' compilate.
//
// ⭐ Perche' e' un gesto guidato e non «apri una distinta e digita i negativi»:
//    su venti righe la ricopiatura a mano e' il punto in cui nasce il SECONDO
//    errore, e questa volta su un documento che rovescia del denaro.
//
// ⛔ NON si chiama «storno», mai. `STORNATA` e' stata ritirata dal catalogo il
//    21/08, e rimetterne la parola nell'interfaccia riaprirebbe una porta che
//    il lotto 2 ha chiuso.
//
// ⚠️ E NON E' ANCORA UN MOVIMENTO: la distinta nuova nasce in BOZZA. Il denaro
//    si muove quando qualcuno la REGISTRA, guardandola. Precompilare e' un
//    aiuto, non una decisione — e va detto, o «Correggi» si legge come il gesto
//    che sistema tutto da se'.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'

import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString, oggiAziendale } from '../../core/utils/date'
import { correggiDistinta } from '../api/pagamenti'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  distinta: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'corretta'])

const { t } = useI18n()
const notify = useNotify()
const { execute, loading, campiErrati } = useApiHandler()

// ⭐ La data della distinta NUOVA nasce oggi: la correzione e' un fatto di oggi,
//    non del giorno dell'errore. ⚠️ Resta modificabile — l'errore puo' essere
//    stato trovato a periodo gia' chiuso.
const dataContabile = ref(null)
const motivo = ref('')

watch(() => props.visible, (aperto) => {
  if (!aperto) return
  dataContabile.value = oggiAziendale()
  motivo.value = ''
})

async function onCorreggi() {
  // ⚠️ NIENTE `silent` e niente `successMessage`: il messaggio giusto dipende
  //    dall'ESITO — «creata» e «non c'era niente da correggere» sono due
  //    notizie diverse — e i guard del database (non registrata, gia' corretta)
  //    devono parlare.
  const dati = await execute(() => correggiDistinta(props.distinta.id, {
    dataContabile: dataContabile.value ? toDateString(dataContabile.value) : null,
    motivo: motivo.value.trim() || null,
  }))
  if (dati === null) return

  // ⛔ `NULLA_DA_CORREGGERE` NON e' un errore: e' la risposta vera di una
  //    distinta che non ha righe postate. Si dice, e non si apre niente —
  //    perche' non c'e' niente da aprire.
  if (!dati.distinta?.id) {
    notify.warn(t('pagamenti.correggi.nulla_da_correggere'))
    emit('update:visible', false)
    return
  }

  // ⭐ Le righe SALTATE si annunciano. Una riga non postata non ha prodotto
  //    movimenti e non c'e' niente da rovesciare — ma il silenzio lascia
  //    l'operatore a chiedersi dove sia finita.
  const saltate = Number(dati.esito?.righe_saltate ?? 0)
  notify.success(
    saltate > 0
      ? t('pagamenti.correggi.creata_con_saltate', {
          righe: dati.esito?.righe_create ?? 0,
          saltate,
        })
      : t('pagamenti.correggi.creata', { righe: dati.esito?.righe_create ?? 0 }),
  )

  emit('corretta', dati.distinta.id)
  emit('update:visible', false)
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ dataContabile: dataContabile.value, motivo: motivo.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t('pagamenti.correggi.titolo')"
    width="md"
    :loading="loading"
    :save-disabled="!distinta"
    :save-label="t('pagamenti.correggi.conferma')"
    save-severity="warn"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onCorreggi"
    @cancel="emit('update:visible', false)"
  >
    <div v-if="distinta" class="form-grid">
      <!-- ⭐ Che cosa sta per succedere, in una riga: la distinta nuova nasce
           in BOZZA e il denaro non si muove finche' non la registra qualcuno. -->
      <Message severity="info" :closable="false">
        {{ t('pagamenti.correggi.che_cosa_fa', { codice: distinta.codice }) }}
      </Message>

      <div class="form-field">
        <label>{{ t('pagamenti.distinte.col_data_contabile') }}</label>
        <DatePicker
          v-model="dataContabile"
          :date-format="DATE_FORMAT"
          show-icon
          :invalid="campiErrati.includes('data_contabile')"
        />
        <small class="app-text-muted">{{ t('pagamenti.correggi.data_aiuto') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.correggi.campo_motivo') }}</label>
        <Textarea v-model="motivo" rows="2" auto-resize />
        <!-- ⚠️ Resta scritto sulla distinta nuova: e' quello che leggera' chi
             si trovera' davanti due documenti gemelli di segno opposto. -->
        <small class="app-text-muted">{{ t('pagamenti.correggi.motivo_aiuto') }}</small>
      </div>

      <!-- ⚠️ Le righe non registrate NON si correggono, e va detto PRIMA: non
           hanno prodotto movimenti, quindi non c'e' niente da rovesciare. -->
      <Message severity="secondary" :closable="false" size="small">
        {{ t('pagamenti.correggi.solo_le_registrate') }}
      </Message>
    </div>
  </AppDialog>
</template>
