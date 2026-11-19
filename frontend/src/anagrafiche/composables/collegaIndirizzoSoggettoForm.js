// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL COLLEGAMENTO fra `useIndirizzoSoggettoForm` e il componente
//        `IndirizzoSoggettoForm`: le prop che il form legge dal composable e
//        gli eventi con cui lo aggiorna, in un oggetto solo per `v-bind`.
//        Estratto il 2026-11-18 (regola del 2, ok Tid, revisione di
//        brief-db-fornitore-privato-indirizzi): lo stesso blocco di dodici
//        righe stava ricopiato in cinque componenti, e una prop nuova del form
//        dimenticata in uno non dava errore, non funzionava e basta.
//
// ⭐ Uso: `const legameIndirizzo = collegaIndirizzoSoggettoForm(indirizzo)` e
//        <IndirizzoSoggettoForm v-bind="legameIndirizzo" :campi-errati="…" />
//    Le prop PROPRIE del chiamante (`campiErrati`, `tipiEsistenti`,
//    `comuneInitialItem`, `mostraAutoClone`) restano scritte nel template.
// ⚠️ Una prop da SOVRASCRIVERE va scritta DOPO il `v-bind`: in Vue 3 vince
//    l'ultima nell'ordine del template (es. `IndirizziSoggettoDrawer`, che
//    mostra da se' il proprio avviso di indirizzo non trovato).
// ⚠️ Gli eventi viaggiano come `on…` nello stesso oggetto: nomi in camelCase
//    come i `defineEmits` del form (`update:isLibera`, `switchTipo`).
// ------------------------------------------------------------

import { computed } from 'vue'

export function collegaIndirizzoSoggettoForm(indirizzo) {
  return computed(() => ({
    form: indirizzo.form,
    isLibera: indirizzo.isLibera.value,
    'onUpdate:isLibera': (v) => { indirizzo.isLibera.value = v },
    tipiStato: indirizzo.tipiStato.value,
    statiLookup: indirizzo.statiLookup,
    capOptions: indirizzo.capOptions.value,
    loadingCap: indirizzo.loadingCap.value,
    autoClone: indirizzo.autoClone.value,
    'onUpdate:autoClone': (v) => { indirizzo.autoClone.value = v },
    onSwitchTipo: indirizzo.switchTipo,
    indirizzoWarnings: indirizzo.indirizzoWarnings.value,
    addressNotFound: indirizzo.addressNotFound.value,
  }))
}
