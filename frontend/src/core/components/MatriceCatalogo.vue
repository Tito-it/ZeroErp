<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA BASE di ogni matrice limitata dal catalogo — «tutte le voci del
//        catalogo, ognuna col suo valore», editabile sulla riga, senza
//        paginazione e senza combo «aggiungi».
//
// ⭐ PERCHE' ESISTE (2026-10-31, B1-bis del brief-db-liste-datatable-grezze-
//    secondo-giro, decisione Tid). Era la meta' bassa di `MatriceOverride`, e
//    due matrici vere la volevano SENZA l'altra meta': il profilo di un
//    reparto (ogni area e ogni azione hanno il loro valore, e il reparto non
//    eredita da niente: e' la sorgente da cui eredita l'operatore) e le
//    utility di un emittente (configurata o no, ma senza un ereditato).
//    Montate su `MatriceOverride` avrebbero mostrato «Override» su ogni riga e
//    un ripristino che non vuol dire niente. Lo strato override sta sopra:
//    `MatriceOverride` = questa base + ereditato, stato e ripristino.
//
// ⛔ LA BASE NON CONOSCE IL DOMINIO. Sa che ci sono delle VOCI, con una chiave
//    e un nome; le colonne dei valori e le azioni di riga le disegna il
//    chiamante negli slot.
//
// ⛔ NON PAGINA, ed e' una scelta di modello: si usa dove la popolazione e'
//    limitata PER CATALOGO, e paginare nasconderebbe righe nella schermata che
//    esiste per farle vedere tutte. Se le voci crescessero con l'USO,
//    l'astrazione giusta e' `ListaConfigurabile`.
//
// Slot:
//   #voce="{ voce }"     → il nome della voce (default: la chiave)
//   #colonne             → le <Column> dei valori, dopo la voce
//   #azioni="{ voce }"   → la cella azioni; la colonna c'e' solo se lo slot
//                          c'e' e la matrice non e' in sola lettura
//   #empty               → lo stato vuoto (default: «Nessuna voce»)
import { computed, ref, useSlots } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
// DataTable grezza: e' il BB della matrice limitata dal catalogo, eccezione
// NOMINATA dalla regola zero — non pagina per modello (v. «NON PAGINA» sopra).
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'

const { t } = useI18n()
const slots = useSlots()

const props = defineProps({
  // Tutte le voci del catalogo, gia' caricate. ⚠️ TUTTE: una lista parziale
  // qui e' il difetto che il pattern esiste per togliere.
  voci: { type: Array, required: true },
  // `voce -> chiave stabile`. Nessun default `id`: le matrici hanno chiavi
  // diverse (`area_id`, `azione_id`, `app_label.model_name`, `utility_id`), e
  // un default indovinato le farebbe collidere in silenzio.
  chiave: { type: Function, required: true },
  // Intestazione della colonna voce.
  labelVoce: { type: String, default: '' },
  // Ricerca locale, dove le voci sono tante. ⚠️ Filtra la VISTA e mai il
  // modello: una riga nascosta dal filtro resta nel salvataggio del caller.
  ricerca: { type: Boolean, default: false },
  ricercaPlaceholder: { type: String, default: '' },
  // Testo da cercare in una voce. Default: tutti i valori stringa della voce.
  testoRicerca: { type: Function, default: null },
  // Sola lettura. `null` = eredita quella iniettata dal drawer.
  // ⛔ `type: null` (qualunque tipo) e NON `Boolean`: con `Boolean` Vue applica
  //    il *boolean casting* e una prop ASSENTE arriva come `false` — il ramo
  //    dell'inject non si accenderebbe mai e la matrice sarebbe editabile
  //    dentro un drawer in sola lettura, senza errori.
  readonly: { type: null, default: null },
})

// ⚠️ `== null` e non falsy: `readonly: false` esplicito deve poter vincere
// sull'inject (una matrice dichiaratamente editabile in un drawer readonly).
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

const conAzioni = computed(() => !!slots.azioni && !isReadonly.value)
</script>

<template>
  <div>
    <div v-if="ricerca" class="app-matrice-catalogo-ricerca">
      <InputText
        v-model="termine"
        :placeholder="ricercaPlaceholder || t('common.search')"
      />
    </div>

    <!-- `scrollable` serve alla colonna azioni `frozen`: senza, PrimeVue la
         ignora e su un pannello stretto Salva/Annulla di una riga in modifica
         scorrono fuori vista (EmittenteFiscaleUtilitiesTab, sette colonne). -->
    <DataTable
      :value="vociVisibili"
      :data-key="chiave"
      class="app-datatable"
      size="small"
      scrollable
    >
      <Column :header="labelVoce">
        <template #body="{ data }">
          <!-- ⚠️ Il testo della voce VA A CAPO entro una larghezza massima:
               la tabella e' `width: max-content` (main.css, `.app-datatable`),
               quindi senza tetto una descrizione lunga allarga la colonna e
               spinge i valori fuori vista (pannello permessi, azioni di
               processo, 2026-10-04). -->
          <div class="app-matrice-catalogo-voce">
            <slot name="voce" :voce="data">{{ chiave(data) }}</slot>
          </div>
        </template>
      </Column>

      <slot name="colonne" />

      <Column v-if="conAzioni" class="app-col-actions" :exportable="false"
        frozen align-frozen="right">
        <template #body="{ data }">
          <slot name="azioni" :voce="data" />
        </template>
      </Column>

      <template #empty>
        <slot name="empty">
          <span class="app-matrice-catalogo-vuota">
            {{ t('common.empty_list') }}
          </span>
        </slot>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.app-matrice-catalogo-ricerca {
  margin-bottom: 0.5rem;
}
/* Con la tabella a `max-content` il tetto e' cio' che limita il contributo
   della cella, e il resto della larghezza resta alle colonne dei valori. */
.app-matrice-catalogo-voce {
  max-width: 22rem;
  white-space: normal;
  overflow-wrap: anywhere;
}
.app-matrice-catalogo-vuota {
  color: var(--app-text-muted);
}
</style>
