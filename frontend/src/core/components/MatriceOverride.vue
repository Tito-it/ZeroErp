<!--
  SPDX-License-Identifier: GPL-3.0-or-later
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
// ⛔ IL BB NON CONOSCE IL DOMINIO. Non sa cosa sia un'area, un livello o
//    un'azione: sa che esistono delle VOCI, che alcune hanno un override e che
//    un override si puo' TOGLIERE. I valori li disegna il caller negli slot.
//    Se conoscesse i livelli sarebbe il pannello permessi travestito da
//    componente, e il terzo uso non lo potrebbe riusare.
//
// ⛔ NON PAGINA, ed e' una scelta di modello e non una svista: si usa dove la
//    popolazione e' limitata PER CATALOGO (le aree funzionali, le azioni di
//    processo, i model overridabili). Paginare nasconderebbe righe proprio
//    nella schermata che esiste per farle vedere tutte. Se un giorno le voci
//    crescessero con l'USO e non col catalogo, l'astrazione giusta e' un'altra
//    (`ListaConfigurabile`), non una prop `paginata` qui.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { MANAGE_ICONS } from '../constants'

const { t } = useI18n()

const props = defineProps({
  // Tutte le voci del catalogo, gia' caricate. ⚠️ TUTTE: una lista parziale
  // qui e' il difetto che il pattern esiste per togliere.
  voci: { type: Array, required: true },
  // `voce -> chiave stabile`. Non c'e' un default `id`: le tre matrici dei
  // permessi hanno chiavi diverse (`area_id`, `azione_id`,
  // `app_label.model_name`), e un default indovinato le farebbe collidere in
  // silenzio.
  chiave: { type: Function, required: true },
  // Le righe SCRITTE, indicizzate per chiave. La PRESENZA della chiave e'
  // l'override; il valore lo usa il caller nello slot.
  overrides: { type: Object, default: () => ({}) },
  // Intestazione della colonna voce.
  labelVoce: { type: String, default: '' },
  // Avviso per riga: `(voce) => string|null`. Il BB non puo' saperlo — servono
  // due valori di dominio da confrontare — ma sa dove disegnarlo.
  avviso: { type: Function, default: null },
  // Ricerca locale. Si accende dove le voci sono tante (le azioni di processo);
  // ⚠️ filtra la VISTA e mai il modello: una riga nascosta dal filtro resta
  // nel salvataggio del caller, che non passa da qui.
  ricerca: { type: Boolean, default: false },
  ricercaPlaceholder: { type: String, default: '' },
  // Testo da cercare in una voce. Default: tutti i valori stringa della voce.
  testoRicerca: { type: Function, default: null },
  // Sola lettura. `null` = eredita quella iniettata dal drawer.
  // ⛔ `type: null` (qualunque tipo) e NON `Boolean`, ed e' la differenza fra
  //    funzionare e no: con `Boolean` nella lista dei tipi Vue applica il
  //    *boolean casting* e una prop ASSENTE arriva come `false`, non come
  //    `null` — il ramo dell'inject non si accenderebbe mai e il pannello
  //    sarebbe editabile dentro un drawer in sola lettura, senza errori.
  readonly: { type: null, default: null },
})

const emit = defineEmits(['reset'])

// Readonly: prop esplicita se data, altrimenti quella iniettata dal drawer.
// ⚠️ `== null` e non falsy: `readonly: false` esplicito deve poter vincere
// sull'inject, altrimenti un pannello dichiaratamente editabile dentro un
// drawer readonly non sarebbe esprimibile.
const injected = useInjectReadonly()
const isReadonly = computed(() =>
  props.readonly == null ? injected.value : props.readonly
)

const termine = ref('')

function _testo(voce) {
  if (props.testoRicerca) return props.testoRicerca(voce)
  return Object.values(voce)
    .filter(v => typeof v === 'string')
    .join(' ')
}

const vociVisibili = computed(() => {
  const q = termine.value.trim().toLowerCase()
  if (!q) return props.voci
  return props.voci.filter(v => _testo(v).toLowerCase().includes(q))
})

const haOverride = (voce) =>
  Object.prototype.hasOwnProperty.call(props.overrides, props.chiave(voce))

const valoreOverride = (voce) => props.overrides[props.chiave(voce)]

const avvisoDi = (voce) => (props.avviso ? props.avviso(voce) : null)
</script>

<template>
  <div class="app-matrice-override">
    <div v-if="ricerca" class="app-matrice-override-ricerca">
      <InputText
        v-model="termine"
        :placeholder="ricercaPlaceholder || t('matrice_override.cerca')"
      />
    </div>

    <DataTable
      :value="vociVisibili"
      class="app-datatable"
      size="small"
    >
      <Column :header="labelVoce">
        <template #body="{ data }">
          <!-- Il nome della voce lo disegna il caller: qui non si sa se una
               voce si chiami `descrizione`, `permission_codename` o altro. -->
          <slot name="voce" :voce="data">{{ chiave(data) }}</slot>
        </template>
      </Column>

      <Column :header="t('matrice_override.col_ereditato')">
        <template #body="{ data }">
          <span class="app-matrice-override-ereditato">
            <slot name="ereditato" :voce="data" />
          </span>
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
            :class="[MANAGE_ICONS.ERRORE, 'app-matrice-override-avviso']"
          />
        </template>
      </Column>

      <Column v-if="!isReadonly" style="width: 3rem">
        <template #body="{ data }">
          <!-- ⭐ «Torna all'ereditato» CANCELLA la riga, non ne scrive una
               uguale: un override che ripete il valore ereditato congela la
               voce, perche' da quel momento non segue piu' la sua sorgente.
               Sono due verbi diversi e devono restare due pulsanti diversi. -->
          <Button
            v-if="haOverride(data)"
            :icon="MANAGE_ICONS.UNDO"
            text
            v-tooltip.left="t('matrice_override.reset_tooltip')"
            @click="emit('reset', chiave(data))"
          />
        </template>
      </Column>

      <template #empty>
        <span class="app-matrice-override-vuota">
          {{ t('matrice_override.nessuna_voce') }}
        </span>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.app-matrice-override-ricerca {
  margin-bottom: 0.5rem;
}
.app-matrice-override-ereditato {
  color: var(--app-text-secondary, var(--p-text-muted-color));
}
.app-matrice-override-avviso {
  margin-left: 0.4rem;
  color: var(--p-orange-500);
}
.app-matrice-override-vuota {
  color: var(--app-text-secondary, var(--p-text-muted-color));
}
</style>
