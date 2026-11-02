<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: IL TELAIO di una matrice slot/override — «tutte le voci del catalogo,
//        ognuna col suo stato», con l'override che si imposta SULLA RIGA.
//
// ⭐ PERCHE' ESISTE (regola del 2, estrazione approvata da Tid il 2026-09-05).
//    E' il pattern deciso il 2026-04-08 sul tab Utilities degli emittenti dopo
//    che il CRUD libero aveva prodotto quattro difetti ricorrenti. Le sue due
//    regole sono:
//      ❌ combo «scegli voce» + bottone «Aggiungi»
//      ❌ mostrare solo le righe gia' override — chi guarda non vede quelle
//         ammesse e non configurate
//    Il pannello permessi dell'operatore faceva ENTRAMBE, ed e' il secondo uso
//    reale: da qui il building block.
//
// ⭐ DAL 2026-10-31 E' LO STRATO, non la matrice intera (B1-bis del brief-db-
//    liste-datatable-grezze-secondo-giro, decisione Tid). La meta' bassa —
//    tutte le voci, ricerca, sola lettura, nessuna paginazione — e' la base
//    `MatriceCatalogo`, che serve anche a matrici SENZA override (il profilo
//    di un reparto, le utility di un emittente). Qui restano le tre cose che
//    fanno di una matrice una matrice di override: la colonna «ereditato», lo
//    stato override/ereditato con l'avviso, e il ripristino.
//
// ⛔ IL BB NON CONOSCE IL DOMINIO. Non sa cosa sia un'area, un livello o
//    un'azione: sa che esistono delle VOCI, che alcune hanno un override e che
//    un override si puo' TOGLIERE. I valori li disegna il caller negli slot.
//    Se conoscesse i livelli sarebbe il pannello permessi travestito da
//    componente, e il terzo uso non lo potrebbe riusare.
//
// ⛔ NON PAGINA: e' la regola della base (`MatriceCatalogo`, «NON PAGINA»).
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import MatriceCatalogo from './MatriceCatalogo.vue'
import { MANAGE_ICONS, STATUS_ICONS } from '../constants'

const { t } = useI18n()

const props = defineProps({
  // Tutte le voci del catalogo (v. la base).
  voci: { type: Array, required: true },
  // `voce -> chiave stabile` (v. la base: nessun default `id`).
  chiave: { type: Function, required: true },
  // Le righe SCRITTE, indicizzate per chiave. La PRESENZA della chiave e'
  // l'override; il valore lo usa il caller nello slot.
  overrides: { type: Object, default: () => ({}) },
  // Intestazione della colonna voce.
  labelVoce: { type: String, default: '' },
  // Avviso per riga: `(voce) => string|null`. Il BB non puo' saperlo — servono
  // due valori di dominio da confrontare — ma sa dove disegnarlo.
  avviso: { type: Function, default: null },
  ricerca: { type: Boolean, default: false },
  ricercaPlaceholder: { type: String, default: '' },
  testoRicerca: { type: Function, default: null },
  // Sola lettura: passa alla base COSI' COM'E' — `null` vuol dire «eredita dal
  // drawer», e la decisione la prende una sede sola (v. la base, `type: null`).
  readonly: { type: null, default: null },
})

const emit = defineEmits(['reset'])

const haOverride = (voce) =>
  Object.prototype.hasOwnProperty.call(props.overrides, props.chiave(voce))

const valoreOverride = (voce) => props.overrides[props.chiave(voce)]

const avvisoDi = (voce) => (props.avviso ? props.avviso(voce) : null)
</script>

<template>
  <MatriceCatalogo
    :voci="voci"
    :chiave="chiave"
    :label-voce="labelVoce"
    :ricerca="ricerca"
    :ricerca-placeholder="ricercaPlaceholder"
    :testo-ricerca="testoRicerca"
    :readonly="readonly"
  >
    <template #voce="{ voce }">
      <!-- Il nome della voce lo disegna il caller: qui non si sa se una voce
           si chiami `descrizione`, `permission_codename` o altro. -->
      <slot name="voce" :voce="voce">{{ chiave(voce) }}</slot>
    </template>

    <template #colonne>
      <Column :header="t('matrice_override.col_ereditato')">
        <template #body="{ data }">
          <div class="app-matrice-override-ereditato">
            <slot name="ereditato" :voce="data" />
          </div>
        </template>
      </Column>

      <Column :header="t('matrice_override.col_override')">
        <template #body="{ data }">
          <slot
            name="override"
            :voce="data"
            :valore="valoreOverride(data)"
            :ha-override="haOverride(data)"
          />
        </template>
      </Column>

      <Column :header="t('matrice_override.col_stato')" style="width: 9rem">
        <template #body="{ data }">
          <Tag
            v-if="haOverride(data)"
            :value="t('matrice_override.stato_override')"
            :severity="avvisoDi(data) ? 'warn' : 'info'"
          />
          <Tag
            v-else
            :value="t('matrice_override.stato_ereditato')"
            severity="secondary"
          />
          <!-- ⚠️ Il motivo dell'avviso viaggia SEMPRE col tooltip: e' l'unico
               canale che arriva anche dove non c'e' hover, e un'icona muta
               chiederebbe di indovinare. -->
          <i
            v-if="avvisoDi(data)"
            v-tooltip.top="avvisoDi(data)"
            :class="[STATUS_ICONS.ERRORE, 'app-matrice-override-avviso']"
          />
        </template>
      </Column>
    </template>

    <template #azioni="{ voce }">
      <!-- ⭐ «Torna all'ereditato» CANCELLA la riga, non ne scrive una uguale:
           un override che ripete il valore ereditato congela la voce, perche'
           da quel momento non segue piu' la sua sorgente. Sono due verbi
           diversi e devono restare due pulsanti diversi. -->
      <Button
        v-if="haOverride(voce)"
        :icon="MANAGE_ICONS.UNDO"
        text
        v-tooltip.left="t('matrice_override.reset_tooltip')"
        @click="emit('reset', chiave(voce))"
      />
    </template>
  </MatriceCatalogo>
</template>

<style scoped>
.app-matrice-override-ereditato {
  max-width: 16rem;
  white-space: normal;
  overflow-wrap: anywhere;
  color: var(--app-text-muted);
}
.app-matrice-override-avviso {
  margin-left: 0.4rem;
  color: var(--app-warning-color);
}
</style>
