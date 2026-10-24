<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: la schermata dei PROCESSI AUTOMATICI — quali programmi girano da soli,
//        di che classe sono, con quale identità e per quali aziende — più lo
//        stato dei presidi: le viste che il catalogo `dbops.presidi` marca
//        di natura ZERO — quelle che devono restare vuote.
//
// ⭐ Fino al 2026-09-05 tutto questo si vedeva solo da `psql`, e
//    `GET /tracciamento/job-runs/` esisteva da mesi senza un solo consumatore
//    nel frontend. Un presidio che si interroga a mano lo guarda chi sta
//    lavorando a quel pezzo; uno che sta in una schermata lo guarda anche chi
//    passa di lì.
// ⛔ Quelle viste nominano TUTTE le aziende e non hanno RLS, quindi il gate è
//    `AdminAPIView` (SUPER_ADMIN). Dal 2026-10-06 (Tid) la voce sta in
//    Strumenti → Diagnostica, il gruppo `adminOnly`: il posto e il permesso
//    dicono ancora la stessa cosa, un livello più in basso. Fino ad allora
//    stava in `amm-software`, proprio per questa ragione.
// ⚠️ Niente `useReadonlyMode`: dietro `adminOnly` non c'è un livello d'area da
//    risolvere — o sei super admin e vedi tutto, o non arrivi alla pagina. Un
//    terzo cancello che non decide niente sarebbe rumore.
// ⭐ DUE SCHEDE, PROCESSI E PRESIDI (2026-10-14, Tid). Fino ad allora i presidi
//    stavano SOTTO la lista, con un tetto in `vh`: a ogni presidio acceso la
//    sezione saliva e le righe visibili della lista calavano — due contenuti
//    che si dividono un'altezza sola se la rubano a vicenda, qualunque tetto si
//    scelga. Ora ognuno ha la pagina intera, e la notizia dei presidi sta nel
//    BADGE della scheda, che si legge anche senza aprirla.
// ⭐ Si apre SEMPRE su «Processi», anche tornando dopo aver lasciato i
//    presidi aperti (`ripartiDaIniziale`); il pallino in topbar porta GIÀ sui presidi
//    (`?tab=presidi`, `PROCESSI_TABS`). ⛔ La vista non cambia scheda da sola
//    quando un presidio si accende: i presidi arrivano dopo il primo disegno, e
//    la pagina salterebbe sotto gli occhi di chi legge. Il richiamo è il badge.
import { computed, onActivated } from 'vue'
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import { useProcessiAutomaticiStore } from '../stores/processiAutomatici'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabDaQuery } from '../../core/composables/useTabDaQuery'
import { PROCESSI_TABS } from '../../core/constants'
import ProcessiAutomaticiTab from '../components/ProcessiAutomaticiTab.vue'
import ProcessoDrawer from '../components/ProcessoDrawer.vue'
import PresidiProcessiPanel from '../components/PresidiProcessiPanel.vue'
import { SEGMENTO_NON_LETTI, statoPallino } from '../../core/utils/pallinoPresidi'

const { t } = useI18n()
const store = useProcessiAutomaticiStore()

// La scheda attiva, pilotabile da fuori con `?tab=` (il pallino in topbar apre
// i presidi). Guard sulla rotta, pulizia della query e agganci KeepAlive
// vivono nel BB.
const activeTab = useTabDaQuery({
  nomeRotta: 'strumenti-diagnostica-processi-automatici',
  ammessi: PROCESSI_TABS,
  iniziale: PROCESSI_TABS.PROCESSI,
  // A ogni ingresso si riparte da «Processi», non dalla scheda dell'ultima
  // visita (Tid 2026-10-24); i presidi si raggiungono dal pallino o dal badge.
  ripartiDaIniziale: true,
})

// ⭐ Il badge della scheda si COLORA con la stessa funzione del pallino in
//    topbar (`statoPallino`): accesi = danger, non letti = warn («cecita', non
//    guasto»), tutto a zero = un verde con lo `0`. Fino al 2026-09-19 i due
//    colori qui erano INVERTITI rispetto al pallino (warn sugli accesi, danger
//    sui non letti): due sedi per lo stesso vocabolario, e dicevano il
//    contrario. ⚠️ `null` (lettura fallita) = nessun tag: il verde vuol dire
//    «visto e vuoto», e qui non si e' visto niente — lo dice il pannello.
const testataPresidi = computed(() => statoPallino(store.presidiTestata))

const drawer = useDrawerState()

// ⚠️ I PRESIDI si leggono all'apertura della PAGINA, non della scheda: il badge
//    deve dire la verita' anche a chi resta sui processi. Nessuno li rinfresca
//    al rientro, e sono proprio il dato che invecchia — un processo che
//    stanotte ha smesso di dare segni di vita si vede solo rileggendoli.
//    `onActivated` copre il primo montaggio E ogni rientro. Nessun polling: un
//    registro di catalogo non cambia ogni pochi secondi.
onActivated(() => {
  store.caricaPresidi()
})

function openDettaglio(row) {
  drawer.editRow(row, 'codice')
}

// Dopo la creazione di un utente tecnico cambiano sia la riga sia i presidi.
function onIdentitaCreata() {
  store.fetchList()
  store.caricaPresidi()
}
</script>

<template>
  <div class="app-page">
    <!-- ⚠️ NIENTE `app-tab-content` sul contenitore <Tabs> (§Pattern Tab-View):
         sul contenitore i TabPanels schiacciano fuori vista la TabList appena
         la tabella si popola. -->
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab :value="PROCESSI_TABS.PROCESSI">{{ t('amministrazione.processi.tab_processi') }}</Tab>
        <Tab :value="PROCESSI_TABS.PRESIDI">
          <span class="app-proc-tab-presidi">
            {{ t('amministrazione.processi.tab_presidi') }}
            <!-- ⛔ Un controllo NON LETTO non è uno zero: senza il suo segmento
                 il badge resterebbe verde mentre non si è visto niente, che su
                 una schermata nata per dire «va tutto bene» è il difetto
                 peggiore. Segmenti e colori sono quelli di `statoPallino`, gli
                 stessi del pallino in topbar. -->
            <Tag
              v-for="seg in testataPresidi?.segmenti ?? []"
              :key="seg.chiave"
              :value="seg.chiave === SEGMENTO_NON_LETTI
                ? t('amministrazione.processi.presidi_non_letti_conteggio', { n: seg.valore })
                : String(seg.valore)"
              :severity="seg.severity"
            />
          </span>
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel :value="PROCESSI_TABS.PROCESSI">
          <ProcessiAutomaticiTab @apri="openDettaglio" />
        </TabPanel>
        <TabPanel :value="PROCESSI_TABS.PRESIDI">
          <!-- ⛔ Niente filtri sui presidi (Tid, 2026-10-14): filtri e azioni
               di lista sono della scheda Processi, e restano lì. -->
          <div class="app-tab-content">
            <p class="app-proc-help">{{ t('amministrazione.processi.presidi_help') }}</p>
            <div class="app-proc-presidi-corpo">
              <PresidiProcessiPanel
                :presidi="store.presidi"
                :loading="store.presidiLoading"
                :errore="store.presidiErrore"
              />
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <ProcessoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :codice="drawer.state.itemId"
      @identita-creata="onIdentitaCreata"
    />
  </div>
</template>

<style scoped>
.app-proc-tab-presidi { display: inline-flex; align-items: center; gap: 0.5rem; }
/* Il pannello prende l'altezza che resta e scorre DENTRO di se' (le schede,
   con la striscia dei presidi a zero ferma sotto). `overflow: hidden` e' la
   rete: senza, un pannello lungo spingerebbe fuori la pagina. */
.app-proc-presidi-corpo {
  flex: 1 1 auto; min-height: 0; overflow: hidden;
  display: flex; flex-direction: column;
}
.app-proc-help { font-size: 0.85rem; opacity: 0.8; margin: 0 0 0.75rem; }
</style>
