<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la CELLA di una riga di giornale (`vendite.giornale`), per codice di
//        colonna — la resa unica che il giornale trasversale e la Storia di
//        fattura e lotto montano negli slot `cell-${codice}` di
//        <ListaConfigurabile>/<DrawerTabLista>.
//
// ⭐ ESTRATTA il 2026-09-27 (regola del 2): fino a quel giorno gli slot stavano
//    inline in `GiornaleListView`, e la Storia di fattura e lotto aveva i suoi
//    `<Column>` scritti a mano — due rese dello stesso fatto, gia' divergenti
//    (il trasversale perdeva gli «a capo» di `cosa`, la Storia mostrava il
//    registro col codice grezzo).
//
// ⚠️ Il `codice` e' la COLONNA, e nella vita della cella non cambia: per questo
//    il lookup delle etichette si sceglie una volta, al setup, e solo per le
//    due colonne che lo leggono. La cache e' di modulo (`useGlobalLookup`),
//    quindi N celle sono N letture della stessa entry, non N fetch.
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import { gravitaGiornaleSeverity } from '../../../core/utils/severity'
import { useLookupEtichettato } from '../../../core/composables/useLookupEtichettato'
import { CAMPO_CODICE_REGISTRO, SORGENTE_REGISTRI, SORGENTE_TIPI_ENTITA } from './giornaleCelle'

const props = defineProps({
  // Il `codice` della colonna a catalogo (uno di `GIORNALE_CELLE`).
  codice: { type: String, required: true },
  riga: { type: Object, required: true },
})

const { t, te } = useI18n()

// ⚠️ Letto una volta: vedi header, la colonna non cambia nella vita della cella.
const colonna = props.codice
const etichettaRegistro = colonna === 'registro'
  ? useLookupEtichettato(SORGENTE_REGISTRI, { campoCodice: CAMPO_CODICE_REGISTRO }).etichetta
  : null
const etichettaEntita = colonna === 'entity_type'
  ? useLookupEtichettato(SORGENTE_TIPI_ENTITA).etichetta
  : null
</script>

<template>
  <!-- ⚠️ NULL resta distinguibile — trattino e colore neutro: e' il segnale di
       un vincolo allargato, non un dato mancante. -->
  <Tag
    v-if="codice === 'gravita'"
    :value="riga.gravita ?? '—'"
    :severity="gravitaGiornaleSeverity(riga.gravita)"
  />
  <!-- Il registro, etichettato dal catalogo (`etichetta_key` di
       `config.registri_giornale`). -->
  <span v-else-if="codice === 'registro'" class="app-drawer-header-muted">
    {{ etichettaRegistro(riga.registro) }}
  </span>
  <Tag
    v-else-if="codice === 'entity_type'"
    :value="etichettaEntita(riga.entity_type)"
    severity="secondary"
  />
  <!-- ⭐ Il FATTO, tradotto quando il catalogo lo dichiara (`etichetta_key` da
       `config.eventi_dominio`, solo EVENT_LOG); altrove `cosa` e' gia' una
       frase. Ripiego fail-visible sul codice grezzo, mai il path della chiave.
       `app-giornale-cosa` tiene gli «a capo» di DETAIL e HINT. -->
  <span v-else-if="codice === 'cosa'" class="app-giornale-cosa">
    {{ labelOrCode(t, te, riga.etichetta_key, riga.cosa) }}
  </span>
  <span v-else class="app-mono app-giornale-mono">{{ riga[codice] }}</span>
</template>

<style scoped>
.app-giornale-mono {
  font-size: 0.85em;
}
</style>
