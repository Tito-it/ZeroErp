<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: ⭐ LE UTILITY DELLA FATTURAZIONE — la sede degli elenchi che il giro
//        automatico produce e non può chiudere da solo. Non è un cruscotto
//        (non misura) e non è un registro (non racconta lo storico): è il
//        posto dove finisce ciò che chiede una persona.
//
// ⭐ NASCE CON UNA LISTA E CON LO SPAZIO PER LE ALTRE (richiesta di Tid,
// 2026-08-22). La prima è «Fondi da decidere»; il contenitore è a tab proprio
// perché ne arriveranno altre — aggiungerne una è un `<Tab>` più un
// componente, senza toccare menu, rotte né permessi.
//
// 📌 PERCHÉ DENTRO VENDITE E NON NEL DOMINIO «STRUMENTI» (decisione di Tid,
// 2026-08-22): i dati sono di area `vendite` — RLS, perimetro emittente e
// permessi vivono lì. Una pagina nel dominio Strumenti avrebbe portato la
// voce di menu in un'area e i suoi cancelli in un'altra: due posti da tenere
// allineati a mano, e nessuno dei due lo direbbe quando divergono.
//
// 📌 Il nome della voce è «Tool fatturazione» (scelta di Tid) e non
// «Strumenti»: quel nome è già di un dominio di primo livello della sidebar
// (code di lavoro), e due voci omonime nello stesso menu si leggono come la
// stessa cosa. La voce sta IN FONDO al menu vendite: non è un percorso
// quotidiano, è dove si va quando qualcosa è rimasto indietro.
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, MANAGE_ICONS } from '../../core/constants'
import FondiFatturaDaDecidereTab from '../components/FondiFatturaDaDecidereTab.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.VENDITE)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-toolbar-start">
        <h2 style="margin: 0;">{{ t('vendite.tool_fatturazione.page_title') }}</h2>
        <small class="app-text-muted">
          {{ t('vendite.tool_fatturazione.page_description') }}
        </small>
      </div>
      <ReadonlyBadge />
    </div>

    <!-- ⚠️ NIENTE `app-tab-content` sul contenitore <Tabs> (stessa trappola di
         CodeLavoroView/ResiView): come figlia diretta di `.app-page` quella
         classe attiva `flex:1; min-height:0; overflow:hidden`, regola pensata
         per il PANNELLO e non per il contenitore — i TabPanels si prendono
         tutto lo spazio e la TabList sparisce appena la tabella si popola
         (sintomo dipendente dai DATI: chi ha più righe non vede più i tab). -->
    <Tabs value="fondi-da-decidere" lazy>
      <TabList>
        <Tab value="fondi-da-decidere">
          <i :class="MANAGE_ICONS.FONDI" />
          {{ t('vendite.tool_fatturazione.tab_fondi_da_decidere') }}
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="fondi-da-decidere">
          <FondiFatturaDaDecidereTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>
