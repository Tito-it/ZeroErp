<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la REGISTRAZIONE della distinta — l'unico gesto irreversibile del
//        cantiere: da qui i movimenti nascono e non si tolgono piu'.
//
// ⭐ Prima si mostra L'ANTEPRIMA, e non e' una cortesia: e' cio' che rende la
//    conferma una decisione invece di un salto nel buio. In particolare dice
//    quali righe restano indietro **e perche'** — una riga non registrata senza
//    motivo si legge come un dato perso.
//
// 🔴 E i due numeri che si spediscono (`righe_attese`, `totale_atteso`) sono la
//    DICHIARAZIONE di cio' che l'operatore ha davanti: se il database trova
//    numeri diversi si ferma. ⛔ Non si «prendono dall'anteprima e via»: si
//    prendono dall'anteprima **appena mostrata**, perche' e' quella che la
//    persona ha guardato. Ricaricarli in silenzio prima di spedire toglierebbe
//    il controllo proprio nel momento in cui serve.
// ⚠️ E lo ZERO e' legittimo — una distinta senza righe registrabili — quindi i
//    due numeri si spediscono anche a zero: filtrarli trasformerebbe un esito
//    vero («non c'e' nulla da postare») in un errore falso.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useChiaveGesto } from '../../core/composables/useChiaveGesto'
import { useNotify } from '../../core/composables/useNotify'
import { useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { statoRigaContabileSeverity } from '../../core/utils/severity'
import { anteprimaRegistrazione, registraDistinta } from '../api/pagamenti'
import { formatCurrency } from '../../core/utils/format'
import { ESITO_NULLA_DA_POSTARE } from '../vocabolari'

const props = defineProps({
  visible: { type: Boolean, default: false },
  distintaId: { type: [Number, null], default: null },
})
const emit = defineEmits(['update:visible', 'registrata'])

const { t } = useI18n()
const notify = useNotify()
const { execute, loading } = useApiHandler()
// ⭐ La key del GESTO: un «Registra» ripremuto dopo un timeout rimanda la
//    stessa, e il backend risponde con la ricevuta della prima esecuzione
//    invece di registrare due volte. Vive finche' il dialog resta aperto.
const gesto = useChiaveGesto()

// ⛔ «Non ho letto l'anteprima» e «l'anteprima dice zero» sono due cose diverse,
//    e a video si somigliano — un dialog vuoto col pulsante spento. Senza
//    distinguerle, una lettura fallita si legge come «non c'e' niente da
//    registrare»: un'affermazione, e falsa, sul foglio che sta per essere
//    chiuso. I tre stati li tiene il BB.
const {
  dati: anteprima,
  errore: erroreAnteprima,
  loading: caricamentoAnteprima,
  carica: caricaAnteprima,
  azzera: azzeraAnteprima,
} = useLetturaTreStati((id) => anteprimaRegistrazione(id))

const nonRegistrabili = computed(() => anteprima.value?.righe_non_registrabili || [])
const righeAttese = computed(() => anteprima.value?.righe_registrabili ?? 0)

// ⚠️ Nessuna riga registrabile: NON si nasconde il dialog e non si spegne il
//    pulsante in silenzio. Il database risponderebbe «nulla da postare», che e'
//    un esito vero — ma dirlo PRIMA evita un giro a vuoto, e soprattutto
//    spiega che il lavoro da fare e' l'abbinamento, non la registrazione.
const nienteDaRegistrare = computed(() => righeAttese.value === 0)

// ⭐ Lo scarto di quadratura non blocca, SEGNALA: e' una discrepanza fra il
//    dichiarato e il digitato, e potrebbe essere giusta (il foglio sbagliava).
//    Chi registra deve saperlo, non essere fermato.
const scarto = computed(() => anteprima.value?.scarto_dichiarato ?? null)
const scartoAperto = computed(
  () => scarto.value != null && Number(scarto.value) !== 0,
)

watch(() => props.visible, async (aperto) => {
  azzeraAnteprima()
  // Chiudere o riaprire il dialog chiude il gesto: il prossimo e' un altro.
  gesto.azzera()
  if (!aperto || !props.distintaId) return
  await caricaAnteprima(props.distintaId)
})

async function onRegistra() {
  if (!anteprima.value) return
  // ⛔ NIENTE `successMessage` fisso: la frase giusta dipende dall'ESITO, e un
  //    toast di successo su `NULLA_DA_POSTARE` direbbe «registrata» di un gesto
  //    che non e' successo — su una distinta di denaro e' la bugia peggiore che
  //    si possa costruire.
  // ⚠️ La key segue i NUMERI: se l'anteprima riletta dopo un rifiuto ne
  //    porta di diversi, la dichiarazione e' un'altra e la key e' nuova.
  const dichiarazione = {
    righeAttese: anteprima.value.righe_registrabili,
    totaleAtteso: anteprima.value.totale_registrabile,
  }
  const ricevuta = await execute(
    () => gesto.invia(
      { distintaId: props.distintaId, ...dichiarazione },
      (config) => registraDistinta(props.distintaId, dichiarazione, config),
    ),
  )

  if (ricevuta === null) {
    // ⛔ RIFIUTATA: si RILEGGE l'anteprima e il dialog resta aperto.
    // ⚠️ NON si riprova in automatico: un retry cieco su un gesto irreversibile
    //    e' la cosa peggiore che si possa costruire. Chi conferma deve vedere i
    //    numeri NUOVI e decidere di nuovo.
    // ⭐ E si rilegge su QUALUNQUE rifiuto, non sul codice della dichiarazione
    //    non corrispondente: e' la stessa regola del resto del cantiere —
    //    si riconosce la SITUAZIONE, non il codice. E la situazione e' una
    //    sola: il gesto e' stato rifiutato, quindi i numeri a video potrebbero
    //    non essere piu' quelli veri. Legarsi a un codice lascerebbe fuori il
    //    secondo motivo di rifiuto che nascera'.
    await caricaAnteprima(props.distintaId)
    return
  }

  // ⭐ La frase segue l'esito, e porta i NUMERI della ricevuta: «fatto» senza
  //    numeri non dice se sono state registrate due righe o venti.
  if (ricevuta.esito === ESITO_NULLA_DA_POSTARE) {
    notify.warn(t('pagamenti.registra.nulla_da_postare'))
  } else {
    notify.success(t('pagamenti.registra.fatto_con_numeri', {
      righe: ricevuta.righe_postate ?? 0,
      totale: formatCurrency(ricevuta.totale_postato),
    }))
  }
  emit('registrata', ricevuta)
  emit('update:visible', false)
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="t('pagamenti.registra.titolo')"
    width="lg"
    :loading="loading || caricamentoAnteprima"
    :save-disabled="!anteprima || nienteDaRegistrare"
    :save-label="t('pagamenti.registra.conferma')"
    save-severity="danger"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onRegistra"
    @cancel="emit('update:visible', false)"
  >
    <!-- ⛔ Il fallimento si DICE, e con la sua conseguenza: da qui non si
         registra, perche' registrare senza aver visto che cosa si registra e'
         esattamente il salto nel buio che questo dialog esiste per evitare. -->
    <Message v-if="erroreAnteprima" severity="error" :closable="false">
      {{ t('pagamenti.registra.anteprima_non_letta') }}
    </Message>

    <div class="form-grid" v-if="anteprima">
      <!-- ⛔ Si dice che non si torna indietro, e si dice PRIMA. -->
      <Message severity="warn" :closable="false">
        {{ t('pagamenti.registra.irreversibile') }}
      </Message>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('pagamenti.registra.righe_registrabili') }}</label>
          <span>{{ righeAttese }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.registra.totale_registrabile') }}</label>
          <span>{{ formatCurrency(anteprima.totale_registrabile) }}</span>
        </div>
      </div>

      <Message v-if="nienteDaRegistrare" severity="info" :closable="false">
        {{ t('pagamenti.registra.niente_da_registrare') }}
      </Message>

      <!-- La quadratura: segnala, non ferma. -->
      <Message v-if="scartoAperto" severity="warn" :closable="false" size="small">
        {{ t('pagamenti.registra.scarto_aperto', { importo: formatCurrency(scarto) }) }}
      </Message>

      <!-- ⭐ CHI RESTA INDIETRO, E PERCHE'. Senza questo elenco la
           registrazione parziale e' indistinguibile da una totale, e le righe
           rimaste non le cerca piu' nessuno. -->
      <template v-if="nonRegistrabili.length">
        <div class="app-drawer-section">
          <h4>{{ t('pagamenti.registra.restano_indietro', { n: nonRegistrabili.length }) }}</h4>
        </div>
        <DataTable
          :value="nonRegistrabili"
          class="app-datatable app-datatable--inner"
          data-key="id"
        >
          <Column field="importo" :header="t('pagamenti.righe.col_importo')">
            <template #body="{ data }">{{ formatCurrency(data.importo) }}</template>
          </Column>
          <Column field="stato_descrizione" :header="t('pagamenti.righe.col_stato')">
            <template #body="{ data }">
              <Tag
                :value="data.stato_descrizione || data.stato_codice"
                :severity="statoRigaContabileSeverity(data.stato_codice)"
              />
            </template>
          </Column>
        </DataTable>
      </template>
    </div>
  </AppDialog>
</template>
