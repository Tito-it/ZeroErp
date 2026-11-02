<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il POPOVER dei BLOCCHI di una coppia (articolo, magazzino): gli
//        attesi `APERTA` in uscita — le promesse fatte ad altri che tengono
//        impegnata la merce — col soggetto, la causale, la data prevista, la
//        sorgente e la nota. E' il drill-down di `n_blocchi` (D-L2-j).
//
// ⭐ Si apre DALLA CELLA, sulla riga cliccata: chi lo apre passa la riga
//    (`apri(event, riga)`), e la lettura parte allora — non al mount, perche'
//    N righe a video farebbero N letture per un numero che nessuno apre.
// ⭐ Tre stati, non due (`useLetturaTreStati`): «non letto» · «nessun blocco»
//    · «non sono riuscito a leggere». A blocchi zero la cella non e' nemmeno
//    cliccabile, quindi «nessun blocco» qui e' il caso in cui la disponibilita'
//    e' cambiata sotto i piedi — e va detto, non confuso con un errore.
// ⛔ Niente `DataTable`: l'elenco e' corto per natura (le promesse aperte di
//    UNA coppia) e si rende come lista — una tabella grezza in piu' sarebbe
//    un'eccezione alla regola zero delle liste per un caso che non la chiede.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Tag from 'primevue/tag'
import { useAuthStore } from '../../stores/auth'
import { AZIONE_BLOCCA_MERCE } from '../vocabolari'

import { RISULTATI, useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { displayDate } from '../../core/utils/date'
import { formatNumber } from '../../core/utils/format'
import { listBlocchi } from '../api/magazzino'
import { useEtichetteMagazzino } from '../etichette'

import { STATUS_ICONS } from '../../core/constants'
const { t } = useI18n()
const auth = useAuthStore()
const { sorgenteMovimento } = useEtichetteMagazzino()
// «Libera» (Lotto 3 R-5): il chiamante apre la finestra. Solo sui blocchi
// MANUALI — senza sorgente: gli attesi di un documento si chiudono col loro
// documento, e il verbo li rifiuterebbe — e solo a chi ha `blocca_merce`
// (permesso => nascondi).
const emit = defineEmits(['libera'])
const puoLiberare = (b) => b.sorgente_codice_interno == null && auth.isActionAllowed(AZIONE_BLOCCA_MERCE)
function libera(b) {
  popover.value?.hide()
  emit('libera', b)
}
const popover = ref(null)
const riga = ref(null)

const { dati: blocchi, caricati, errore, loading, carica, azzera } =
  useLetturaTreStati(listBlocchi, { estrai: RISULTATI, vuoto: [] })

// Scopo: apre il popover sulla cella e legge i blocchi della coppia.
function apri(event, r) {
  riga.value = r
  popover.value?.toggle(event)
  carica(r.articolo_id, r.magazzino_id)
}

function onChiuso() {
  riga.value = null
  azzera()
}

defineExpose({ apri })
</script>

<template>
  <Popover ref="popover" :style="{ width: '520px' }" @hide="onChiuso">
    <div class="app-blocchi">
      <div class="app-blocchi-testata">
        <strong>{{ t('magazzino.disponibilita.blocchi_titolo') }}</strong>
        <span v-if="riga" class="app-text-muted">
          {{ riga.articolo_codice }} · {{ riga.magazzino_codice }}
        </span>
      </div>

      <div v-if="loading" class="app-loading">
        <i :class="STATUS_ICONS.CARICAMENTO" />
      </div>

      <!-- ⛔ «Non sono riuscito a leggere» non e' «non ce ne sono». -->
      <p v-else-if="caricati && errore" class="app-text-muted">
        {{ t('magazzino.disponibilita.blocchi_non_letti') }}
      </p>
      <p v-else-if="caricati && !blocchi.length" class="app-text-muted">
        {{ t('magazzino.disponibilita.blocchi_nessuno') }}
      </p>

      <ul v-else-if="caricati" class="app-blocchi-elenco">
        <li v-for="b in blocchi" :key="b.id" class="app-blocchi-voce">
          <div class="app-blocchi-riga">
            <!-- La quantita' e' NEGATIVA per costruzione (un'uscita): si
                 mostra in valore assoluto, il verso lo dice il titolo. -->
            <strong>{{ formatNumber(Math.abs(Number(b.qta))) }}</strong>
            <span v-if="b.causale_codice" v-tooltip.bottom="b.causale_descrizione || undefined">
              {{ b.causale_codice }}
            </span>
            <Tag
              v-if="b.sorgente_codice_interno"
              :value="sorgenteMovimento(b.sorgente_codice_interno)"
              severity="secondary"
            />
            <span v-if="b.data_prevista" class="app-text-muted">
              {{ t('magazzino.disponibilita.blocchi_entro', { data: displayDate(b.data_prevista) }) }}
            </span>
            <Button v-if="puoLiberare(b)" :label="t('magazzino.blocchi.libera')"
                    link size="small" @click="libera(b)" />
          </div>
          <div v-if="b.soggetto_ragione_sociale || b.nota" class="app-blocchi-riga app-text-muted">
            <span v-if="b.soggetto_ragione_sociale">{{ b.soggetto_ragione_sociale }}</span>
            <span v-if="b.nota">{{ b.nota }}</span>
          </div>
        </li>
      </ul>
    </div>
  </Popover>
</template>

<style scoped>
/* Il solo layout dell'elenco nel popover: componente-specifico, non un
 * pattern di pagina. Token `--app-*` e basta. */
.app-blocchi {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
}
.app-blocchi-testata {
  display: flex;
  justify-content: space-between;
  gap: var(--app-space-sm);
  align-items: baseline;
}
.app-blocchi-elenco {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.app-blocchi-voce {
  padding: 0.4rem 0;
  border-top: 1px solid var(--app-border-color);
}
.app-blocchi-riga {
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-space-sm);
  align-items: center;
  font-size: 0.85rem;
}
</style>
