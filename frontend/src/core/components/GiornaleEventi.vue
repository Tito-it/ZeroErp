<script setup>
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: Vue
// Scopo: BB «giornale di eventi» — timeline cronologica inversa di un audit log.
// ------------------------------------------------------------
//
// ⭐ ESTRATTO IL 2026-08-28 (regola del 2, ok Tid). La prima occorrenza è
//    `PraticaGiornaleTab` — che portava scritto in testa «componente
//    riutilizzabile, sarà usato anche da altri domini in futuro» — la seconda è
//    il registro delle righe di commessa, nato dal collaudo «Riporta da
//    emettere». Stessa forma: voce per evento, tag colorato, chi/quando in
//    testata, riga di dettaglio sotto.
//
// ⛔ È PRESENTAZIONALE E BASTA: non conosce rotte, non fa fetch, non sa di quale
//    dominio sta mostrando la storia. Il caller possiede i dati e le tre
//    decisioni che cambiano fra un giornale e l'altro:
//      · `etichetta(codice)` → la frase leggibile dell'evento;
//      · `stile(codice)`     → severity + icona;
//      · `dettaglio(evento)` → la riga sotto, che ha forma diversa per dominio.
//    Ficcarle qui dentro avrebbe voluto dire una mappa di tutti i domini in un
//    componente di `core/`, cioè il contrario di un BB.
//
// ⚠️ Il CODICE dell'evento si chiama diversamente nei due domini (`azione` per
//    le pratiche, `evento` per le commesse): lo dice `campoCodice`. Rinominarlo
//    in uno dei due sarebbe stato un cambio di contratto d'API per far tornare
//    un nome di componente.
//
// ⚠️ Vocabolari APERTI: `etichetta` e `stile` devono ripiegare sul codice grezzo,
//    non sparire. Un evento nuovo a DB deve **vedersi**, anche brutto.
import Tag from 'primevue/tag'
import { displayDate, displayTime } from '../utils/date'
import { STATUS_ICONS } from '../constants'

const props = defineProps({
  eventi: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  // ⚠️ Default `true` per non cambiare il comportamento del primo consumatore,
  //    che questa distinzione non ce l'aveva. Chi la passa distingue «non c'è
  //    niente» da «non lo sappiamo ancora»: un empty-state positivo su una
  //    fetch mai riuscita afferma il falso.
  caricato: { type: Boolean, default: true },
  campoCodice: { type: String, default: 'evento' },
  etichetta: { type: Function, required: true },
  stile: { type: Function, required: true },
  dettaglio: { type: Function, default: () => '' },
  testoVuoto: { type: String, required: true },
  testoPlaceholder: { type: String, default: '' },
})

function codice(ev) {
  return ev?.[props.campoCodice]
}
</script>

<template>
  <div>
    <div v-if="props.loading" class="app-giornale-stato">
      <i :class="STATUS_ICONS.CARICAMENTO" />
    </div>

    <!-- Non caricato: si tace, non si afferma che non è successo niente. -->
    <div v-else-if="!props.caricato" class="app-giornale-stato">
      <i :class="STATUS_ICONS.VUOTO" />
      <p v-if="props.testoPlaceholder">{{ props.testoPlaceholder }}</p>
    </div>

    <div v-else-if="props.eventi.length === 0" class="app-giornale-stato">
      {{ props.testoVuoto }}
    </div>

    <div v-else class="app-giornale-lista">
      <div v-for="ev in props.eventi" :key="ev.id" class="app-voce-registro">
        <div class="app-giornale-testata">
          <i :class="props.stile(codice(ev)).icon" class="app-giornale-icona" />
          <Tag
            :value="props.etichetta(codice(ev))"
            :severity="props.stile(codice(ev)).severity"
          />
          <!-- Spazio del dominio: una chip in più, un riferimento, un numero. -->
          <slot name="voce-extra" :evento="ev" />
          <span v-if="ev.user_insert" class="app-giornale-utente">{{ ev.user_insert }}</span>
          <!-- Il «quando» in fondo a destra: data sopra, ora sotto. -->
          <div class="app-giornale-quando">
            <span class="app-giornale-data">{{ displayDate(ev.data_insert) }}</span>
            <span class="app-giornale-ora">{{ displayTime(ev.data_insert) }}</span>
          </div>
        </div>
        <div v-if="props.dettaglio(ev)" class="app-giornale-dettaglio">
          {{ props.dettaglio(ev) }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-giornale-stato {
  text-align: center;
  color: var(--app-text-muted);
  padding: 0.75rem;
}

.app-giornale-lista {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}


.app-giornale-testata {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.app-giornale-icona {
  font-size: 0.8rem;
  color: var(--app-icon-color);
}

.app-giornale-quando {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
  line-height: 1.2;
}

.app-giornale-data,
.app-giornale-ora {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.app-giornale-utente {
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
  font-style: italic;
}

.app-giornale-dettaglio {
  margin-top: 0.25rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
  padding-left: 1.3rem;
}
</style>
