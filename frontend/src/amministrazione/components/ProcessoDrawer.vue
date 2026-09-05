<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: drawer di CONSULTAZIONE di un processo automatico: chi è, dove scrive,
//        con quale identità lavora e quando è girato l'ultima volta.
//        Più l'unico verbo della schermata: creare l'utente tecnico di
//        un'azienda che il processo non serve ancora.
//
// ⭐ Sola lettura per costruzione: il registro dei processi è CATALOGO — nasce
//    da un seed, non da questa schermata. `FormFooter close-only`: non c'è
//    niente da salvare, e un pulsante «Salva» che non salva niente è peggio di
//    nessun pulsante.
// ⚠️ Le tre schede sono `Tabs` PrimeVue 4 e NON `useDrawerTabLista`: quello
//    serve a una lista PAGINATA con endpoint proprio e filtri. Qui bersagli e
//    identità sono elenchi CHIUSI dal modello (un pugno di righe, consegnate
//    col dettaglio in un round-trip) e le corse sono le ultime N. Montarci un
//    paginator sarebbe cerimoniale.
// ⛔ La lista delle CORSE è l'unica che potrebbe crescere: è limitata a 50 dal
//    backend e lo dice a video. Se un giorno servisse scorrerla tutta, allora sì
//    diventa una lista vera con `useDrawerTabLista` — non prima.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Button from 'primevue/button'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useNotify } from '../../core/composables/useNotify'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { DRAWER_WIDTH } from '../../core/constants'
import {
  getProcesso,
  listProcessoRun,
  creaUtenteTecnico,
  riattivaUtenteTecnico,
} from '../api/amministrazione'
import { displayTimestamp } from '../../core/utils/date'



const props = defineProps({
  visible: { type: Boolean, default: false },
  codice: { type: String, default: null },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible', 'identita-creata'])

// ⛔ Quante corse si mostrano. Sede UNICA: prima il numero stava nella
//    chiamata E nella frase i18n, e due numeri per lo stesso fatto
//    divergono al primo che si tocca.
const CORSE_MOSTRATE = 50

const { t } = useI18n()
const { execute } = useApiHandler()
const notify = useNotify()
const onClose = useDrawerClose(emit)

const dettaglio = ref(null)
const corse = ref([])
const caricamento = ref(false)
const tabAttiva = ref('bersagli')
const emittenteScelto = ref(null)
const creazioneInCorso = ref(false)
// ⭐ L'azienda per cui la fabbrica ha detto «c'è già, ed è spento». Si tiene il
//    CODICE e non un booleano: cambiando scelta nella tendina il pulsante di
//    riattivazione deve sparire, o resterebbe acceso su un'altra azienda.
// ⛔ Non si calcola qui se un utente tecnico spento esista: lo saprebbe solo
//    ricostruendo lo username deterministico `processo@azienda`, che è una
//    regola del DATABASE — scriverla anche qui la renderebbe due, e la seconda è
//    quella che diverge il giorno che il formato cambia.
const daRiattivare = ref(null)
const codiceRifiuto = 'E_UTENTE_TECNICO_DA_RIATTIVARE'

// ⭐ Le aziende che questo processo NON serve arrivano dal dettaglio: sono
//    l'elenco su cui il verbo agisce. Senza, il pannello mostrerebbe due
//    identità e non direbbe che la terza azienda è scoperta.
const emittentiScoperti = computed(
  () => (dettaglio.value?.emittenti_non_serviti || []).map((e) => ({
    label: e.emittente_codice, value: e.emittente_codice,
  })),
)

// ⚠️ Un processo su canale CODA non VUOLE un utente tecnico: gira con
//    l'identità di chi lo accoda. Dirlo evita che l'assenza sembri un difetto.
const vuoleIdentita = computed(
  () => dettaglio.value
    && dettaglio.value.classe === 'DOMINIO'
    && ['PGAGENT', 'COMMAND'].includes(dettaglio.value.canale),
)

// Scopo: carica dettaglio + corse del processo aperto.
async function carica() {
  if (!props.codice) return
  caricamento.value = true
  try {
    const [det, run] = await Promise.all([
      execute(() => getProcesso(props.codice)),
      execute(() => listProcessoRun(props.codice, { limit: CORSE_MOSTRATE })),
    ])
    // ⚠️ `execute` restituisce GIA' il payload scartato dall'envelope
    //    (`{data, meta}` -> `data`): scartarlo una seconda volta darebbe
    //    `undefined`, e il drawer sarebbe vuoto SENZA nessun errore.
    dettaglio.value = det ?? null
    corse.value = run?.results ?? []
    emittenteScelto.value = null
    daRiattivare.value = null
  } finally {
    caricamento.value = false
  }
}

// ⚠️ `immediate` non serve — il drawer nasce chiuso — ma il watch sì: il
//    componente resta montato e cambia solo la prop quando si apre un altro
//    processo dalla lista.
watch(() => [props.visible, props.codice], ([aperto]) => {
  if (aperto) carica()
  else dettaglio.value = null
})

// Scopo: crea l'utente tecnico per l'azienda scelta, poi ricarica.
// ⛔ Nessuna scorciatoia «crea tutti quelli che mancano»: sarebbe il sistema che
//    concede perimetri da solo, cioè quello che la decisione D-9 ha escluso.
//
// ⚠️ Il `catch` intercetta SOLO per leggere il codice, e poi rilancia: il toast e
//    il resto della gestione errori restano dove stanno (`execute`). Senza
//    questo, la frase del database — «va riattivato, non creato di nuovo» —
//    arriverebbe all'operatore senza il pulsante che la esegue.
async function creaIdentita() {
  if (!emittenteScelto.value) return
  const azienda = emittenteScelto.value
  creazioneInCorso.value = true
  daRiattivare.value = null
  try {
    const res = await execute(
      () => creaUtenteTecnico(props.codice, azienda).catch((err) => {
        if (err?.response?.data?.error?.code === codiceRifiuto) {
          daRiattivare.value = azienda
        }
        throw err
      }),
    )
    if (res !== null) {
      notify.success(t('amministrazione.processi.identita_creata'))
      emit('identita-creata')
      await carica()
    }
  } finally {
    creazioneInCorso.value = false
  }
}

// Scopo: riaccende l'utente tecnico spento dell'azienda scelta, poi ricarica.
// ⚠️ Riaccende TUTTA la terna (utente, identità, legame): la fabbrica non
//    ammette una riattivazione parziale, perché un anello spento fermerebbe il
//    processo lasciandolo con l'aria di essere a posto.
async function riattivaIdentita() {
  if (!daRiattivare.value) return
  creazioneInCorso.value = true
  try {
    const res = await execute(
      () => riattivaUtenteTecnico(props.codice, daRiattivare.value),
    )
    if (res !== null) {
      notify.success(t('amministrazione.processi.identita_riattivata'))
      daRiattivare.value = null
      emit('identita-creata')
      await carica()
    }
  } finally {
    creazioneInCorso.value = false
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @update:visible="v => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="t('amministrazione.processi.drawer_action')"
        :title="codice || ''"
        icon="pi pi-cog"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content">
      <template v-if="dettaglio">
        <div class="app-proc-testa">
          <Tag :value="dettaglio.classe" severity="info" />
          <Tag :value="dettaglio.canale" severity="secondary" />
          <Tag
            v-if="!dettaglio.attivo"
            :value="t('amministrazione.stato_inattivo')"
            severity="danger"
          />
          <span class="app-proc-descrizione">{{ dettaglio.descrizione }}</span>
        </div>

        <Tabs v-model:value="tabAttiva">
          <TabList>
            <Tab value="bersagli">
              {{ t('amministrazione.processi.tab_bersagli') }}
              ({{ dettaglio.bersagli.length }})
            </Tab>
            <Tab value="identita">
              {{ t('amministrazione.processi.tab_identita') }}
              ({{ dettaglio.identita.length }})
            </Tab>
            <Tab value="run">
              {{ t('amministrazione.processi.tab_run') }} ({{ corse.length }})
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel value="bersagli">
              <!-- ⚠️ È un elenco DICHIARATO: prova che qualcuno ha detto dove
                   il processo scrive, non che scriva solo lì. -->
              <p class="app-proc-help">
                {{ t('amministrazione.processi.bersagli_help') }}
              </p>
              <table class="app-proc-tabella">
                <thead>
                  <tr>
                    <th>{{ t('amministrazione.processi.col_tabella') }}</th>
                    <th>{{ t('amministrazione.processi.col_percorso') }}</th>
                    <th>{{ t('amministrazione.processi.col_colonna') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="b in dettaglio.bersagli" :key="`${b.schema_tabella}.${b.nome_tabella}`">
                    <td>{{ b.schema_tabella }}.{{ b.nome_tabella }}</td>
                    <!-- ⛔ Percorso assente = il processo scrive dove non c'è
                         niente su cui filtrare: è il caso che il presidio
                         «dominio senza emittente» esiste per prendere. -->
                    <td>
                      <Tag
                        v-if="!b.emittente_via"
                        :value="t('amministrazione.processi.senza_percorso')"
                        severity="warn"
                      />
                      <span v-else>{{ b.emittente_via }}</span>
                    </td>
                    <td>{{ b.emittente_colonna || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </TabPanel>

            <TabPanel value="identita">
              <p class="app-proc-help">
                {{ vuoleIdentita
                  ? t('amministrazione.processi.identita_help')
                  : t('amministrazione.processi.identita_non_serve') }}
              </p>
              <table v-if="dettaglio.identita.length" class="app-proc-tabella">
                <thead>
                  <tr>
                    <th>{{ t('amministrazione.processi.col_utente') }}</th>
                    <th>{{ t('amministrazione.processi.col_azienda') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="i in dettaglio.identita" :key="i.auth_user_id">
                    <td>{{ i.username }}</td>
                    <td>{{ i.emittente_codice }}</td>
                  </tr>
                </tbody>
              </table>

              <!-- ⭐ Il numero che rompe il silenzio: senza questo blocco, «due
                   identità» si legge come «tutto a posto» anche quando la terza
                   azienda non viene servita e il suo lavoro non parte. -->
              <template v-if="vuoleIdentita && emittentiScoperti.length">
                <Message severity="warn" :closable="false">
                  {{ t('amministrazione.processi.aziende_scoperte', { n: emittentiScoperti.length }) }}
                </Message>
                <div class="app-proc-crea">
                  <Select
                    v-model="emittenteScelto"
                    :options="emittentiScoperti"
                    option-label="label"
                    option-value="value"
                    :placeholder="t('amministrazione.processi.scegli_azienda')"
                    @change="daRiattivare = null"
                  />
                  <Button
                    :label="t('amministrazione.processi.crea_identita')"
                    icon="pi pi-user-plus"
                    :disabled="!emittenteScelto || creazioneInCorso"
                    :loading="creazioneInCorso"
                    @click="creaIdentita"
                  />
                  <!-- ⭐ Compare SOLO dopo che la fabbrica ha detto che c'è
                       qualcosa di spento: è il rifiuto parlante a portare qui,
                       non un'ipotesi del frontend. -->
                  <Button
                    v-if="daRiattivare"
                    :label="t('amministrazione.processi.riattiva_identita')"
                    icon="pi pi-replay"
                    severity="warn"
                    :disabled="creazioneInCorso"
                    :loading="creazioneInCorso"
                    @click="riattivaIdentita"
                  />
                </div>
              </template>
            </TabPanel>

            <TabPanel value="run">
              <p class="app-proc-help">
                {{ t('amministrazione.processi.run_help', { n: CORSE_MOSTRATE }) }}
              </p>
              <table v-if="corse.length" class="app-proc-tabella">
                <thead>
                  <tr>
                    <th>{{ t('amministrazione.processi.col_quando') }}</th>
                    <th>{{ t('amministrazione.processi.col_jobname') }}</th>
                    <th>{{ t('amministrazione.processi.col_origine') }}</th>
                    <th>{{ t('amministrazione.processi.col_esito') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in corse" :key="r.id">
                    <td>{{ displayTimestamp(r.started_at) }}</td>
                    <td>{{ r.jobname }}</td>
                    <td>{{ r.origine }}</td>
                    <td>
                      <!-- ⚠️ `ok` è a tre stati: `null` = corsa ancora aperta,
                           non «fallita». Appiattirlo a rosso direbbe il falso. -->
                      <Tag
                        v-if="r.ok === true"
                        :value="t('amministrazione.processi.esito_ok')"
                        severity="success"
                      />
                      <Tag
                        v-else-if="r.ok === false"
                        :value="r.error_code || t('amministrazione.processi.esito_ko')"
                        severity="danger"
                      />
                      <Tag
                        v-else
                        :value="t('amministrazione.processi.esito_in_corso')"
                        severity="secondary"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="app-proc-help">
                {{ t('amministrazione.processi.run_nessuno') }}
              </p>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>

      <p v-else-if="caricamento" class="app-proc-help">{{ t('common.loading') }}</p>
    </div>

    <FormFooter close-only @cancel="onClose" />
  </Drawer>
</template>

<style scoped>
.app-proc-testa { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.app-proc-descrizione { font-size: 0.9rem; opacity: 0.85; }
.app-proc-help { font-size: 0.85rem; opacity: 0.8; margin: 0.5rem 0; }
/* Tabelle di consultazione, non liste: scorrono nel proprio contenitore. */
.app-proc-tabella { width: 100%; display: block; overflow-x: auto; font-size: 0.85rem; }
.app-proc-tabella th, .app-proc-tabella td {
  text-align: left; padding: 0.25rem 0.5rem; white-space: nowrap;
}
.app-proc-tabella th { opacity: 0.7; font-weight: 500; }
.app-proc-crea { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.75rem; }
</style>
