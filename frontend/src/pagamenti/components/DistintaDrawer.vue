<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer della DISTINTA CONTABILE — il foglio del denaro raccolto in una
//        giornata da un canale: testata, quadratura, e le righe che lo
//        compongono.
//
// ⚠️ PRIMO GIRO: SOLA CONSULTAZIONE. I verbi — apertura con form, digitazione
//    delle righe, abbinamento alla rata, registrazione — arrivano nel giro
//    successivo. ⛔ Non si montano pulsanti che non fanno niente: un'azione
//    dichiarata e inerte e' peggio della sua assenza, perche' sembra
//    presidiata (e' la stessa specie del campo `action` ignorato da
//    `RowActionsMenu` fino al 2026-08-17).
//
// ⭐ I DUE CATALOGHI DI STATO arrivano dentro il dettaglio, in un round-trip:
//    `stati_distinta` e `stati_riga`, coi flag che governano l'interfaccia
//    (`is_final`, `is_postabile`, `richiede_abbinamento`). ⛔ Non si riscrivono
//    qui: il giorno che nasce uno stato nuovo, una copia nel frontend lo
//    nasconderebbe senza dirlo.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'

import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { statoDistintaSeverity, statoRigaContabileSeverity } from '../../core/utils/severity'
import { getDistinta } from '../api/pagamenti'
import { euro } from '../formato'

const props = defineProps({
  visible: { type: Boolean, default: false },
  distintaId: { type: [Number, null], default: null },
})
const emit = defineEmits(['update:visible'])

const { t } = useI18n()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
// ⚠️ Guard anti-race: aprire due distinte in rapida successione farebbe
//    atterrare la risposta piu' lenta DOPO quella piu' recente, e a video
//    resterebbe il documento sbagliato — senza nessun errore.
const { tag, isCurrent, invalidate } = useFetchVersion()

const dettaglio = ref(null)
const loading = ref(false)

const distinta = computed(() => dettaglio.value?.distinta || null)
const righe = computed(() => dettaglio.value?.righe || [])


// ⭐ LA QUADRATURA, ed e' il numero per cui la testata esiste: quanto e' stato
//    dichiarato all'apertura contro quanto e' stato effettivamente digitato.
// ⚠️ `importo_dichiarato` NULL non e' zero — significa «non e' stato dichiarato
//    niente», quindi la quadratura NON SI APPLICA. Mostrare 0,00 direbbe
//    «quadra» di una distinta che nessuno ha mai quadrato.
const quadraturaApplicabile = computed(() => distinta.value?.importo_dichiarato != null)
const scarto = computed(() => distinta.value?.scarto_dichiarato ?? null)
const quadra = computed(
  () => quadraturaApplicabile.value && Number(scarto.value || 0) === 0,
)

// Scopo: carica il documento all'apertura e a ogni cambio di id.
async function loadDetail() {
  if (!props.distintaId) return
  const mio = tag()
  loading.value = true
  try {
    const res = await loadDetailOrClose(() => getDistinta(props.distintaId))
    if (!isCurrent(mio)) return
    dettaglio.value = res?.data?.data || null
  } finally {
    if (isCurrent(mio)) loading.value = false
  }
}

watch(
  () => [props.visible, props.distintaId],
  ([vis]) => {
    if (vis && props.distintaId) {
      loadDetail()
    } else if (!vis) {
      // ⚠️ Si azzera alla CHIUSURA: senza, riaprendo su un'altra distinta si
      //    vedrebbe per un istante quella di prima — e su documenti di denaro
      //    un lampo del documento sbagliato non e' un dettaglio estetico.
      dettaglio.value = null
      invalidate()
    }
  },
  { immediate: true },
)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="t('pagamenti.distinte.titolo_singolare')"
        :icon="NAV_ICONS.DISTINTE"
      />
    </template>

    <div class="app-drawer-content">
      <!-- ⚠️ Il caricamento si DICE. Un drawer che si apre vuoto e resta vuoto
           per mezzo secondo si legge come «questa distinta non ha niente», che
           e' un'affermazione — e per giunta falsa. -->
      <div v-if="loading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="contentReady && distinta">
        <DrawerEntityHeader>
          <Tag :value="distinta.codice" severity="secondary" />
          <span class="app-drawer-header-muted">
            {{ displayDate(distinta.data_contabile) }}
          </span>
          <span v-if="distinta.centro_descrizione">{{ distinta.centro_descrizione }}</span>
          <span v-if="distinta.ente_descrizione" class="app-drawer-header-muted">
            {{ distinta.ente_descrizione }}
          </span>

          <template #status>
            <Tag
              :value="distinta.stato_descrizione || distinta.stato_codice"
              :severity="statoDistintaSeverity(distinta.stato_codice)"
            />
          </template>
        </DrawerEntityHeader>

        <!-- ⚠️ Il primo giro e' di sola consultazione, e lo si DICE: una
             schermata senza verbi, senza spiegare perche', si legge come una
             schermata rotta. -->
        <Message severity="info" :closable="false" size="small">
          {{ t('pagamenti.distinte.solo_consultazione') }}
        </Message>

        <!-- ══ La quadratura ══ -->
        <div class="app-drawer-section">
          <h4>{{ t('pagamenti.distinte.sezione_quadratura') }}</h4>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_importo_dichiarato') }}</label>
            <span>{{ euro(distinta.importo_dichiarato) }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_totale_righe') }}</label>
            <span>{{ euro(distinta.totale_righe) }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_scarto_dichiarato') }}</label>
            <!-- ⭐ Tre esiti, non due: quadra · non quadra · non si applica. -->
            <span v-if="!quadraturaApplicabile" class="app-text-muted">
              {{ t('pagamenti.distinte.quadratura_non_applicabile') }}
            </span>
            <Tag
              v-else-if="!quadra"
              :value="euro(scarto)"
              severity="warn"
            />
            <Tag v-else :value="t('pagamenti.distinte.quadra')" severity="success" />
          </div>
          <div class="form-field">
            <label>{{ t('pagamenti.distinte.col_righe_registrabili') }}</label>
            <span>
              {{ distinta.righe_registrabili ?? 0 }} / {{ distinta.righe_totali ?? 0 }}
            </span>
          </div>
        </div>

        <!-- ══ Chi e quando ha registrato ══ -->
        <template v-if="distinta.data_conferma">
          <div class="app-drawer-section">
            <h4>{{ t('pagamenti.distinte.sezione_registrazione') }}</h4>
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('pagamenti.distinte.col_data_conferma') }}</label>
              <span>{{ displayTimestamp(distinta.data_conferma) }}</span>
            </div>
            <div class="form-field">
              <label>{{ t('pagamenti.distinte.col_user_conferma') }}</label>
              <span>{{ distinta.user_conferma || '—' }}</span>
            </div>
          </div>
        </template>

        <!-- ══ Le righe ══ -->
        <div class="app-drawer-section">
          <h4>{{ t('pagamenti.distinte.sezione_righe') }}</h4>
        </div>
        <DataTable
          :value="righe"
          class="app-datatable app-datatable--inner"
          data-key="id"
          scrollable
          scroll-height="flex"
        >
          <Column field="data_pagamento" :header="t('pagamenti.righe.col_data_pagamento')">
            <template #body="{ data }">{{ displayDate(data.data_pagamento) }}</template>
          </Column>
          <Column field="riferimento_ente" :header="t('pagamenti.righe.col_riferimento_ente')">
            <template #body="{ data }">{{ data.riferimento_ente || '—' }}</template>
          </Column>
          <Column field="importo" :header="t('pagamenti.righe.col_importo')" style="text-align: right;">
            <template #body="{ data }">{{ euro(data.importo) }}</template>
          </Column>
          <Column field="billing_account_descrizione" :header="t('pagamenti.righe.col_billing_account_descrizione')">
            <template #body="{ data }">{{ data.billing_account_descrizione || '—' }}</template>
          </Column>
          <Column field="fattura_numero" :header="t('pagamenti.righe.col_fattura_numero')">
            <template #body="{ data }">{{ data.fattura_numero || '—' }}</template>
          </Column>
          <Column field="stato_descrizione" :header="t('pagamenti.righe.col_stato')">
            <template #body="{ data }">
              <Tag
                :value="data.stato_descrizione || data.stato_codice"
                :severity="statoRigaContabileSeverity(data.stato_codice)"
              />
              <!-- ⭐ La forzatura resta SCRITTA sulla riga ed e' cio' che
                   l'elenco delle rate fuori capienza legge: qui si vede, o la
                   riga racconta meno di quello che e' successo. -->
              <Tag
                v-if="data.forzata"
                :value="t('pagamenti.righe.forzata')"
                severity="warn"
              />
            </template>
          </Column>
          <template #empty>
            <div class="app-empty-state">
              <i class="pi pi-list" />
              <p>{{ t('pagamenti.distinte.nessuna_riga') }}</p>
            </div>
          </template>
        </DataTable>
      </template>
    </div>

    <FormFooter close-only @cancel="onClose" />
  </Drawer>
</template>
