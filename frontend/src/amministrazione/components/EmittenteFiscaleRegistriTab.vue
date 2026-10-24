<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Tab dei REGISTRI DI NUMERAZIONE dentro il drawer dell'emittente
//        fiscale — la maschera che a `vendite.registri_fatturazione` mancava
//        del tutto (brief-be-fe-crud-registri-di-numerazione, fasi F4/F5).
//
// ⭐ VIVE QUI E NON IN UNA VOCE DI MENU. Il registro è per-emittente: una lista
//    globale costringerebbe a mettere l'emittente in colonna e a filtrarci
//    sopra, cioè a ricostruire a mano il contesto che il drawer dà già.
//
// ⛔ IL CESTINO È QUASI SEMPRE SPENTO, ED È IL COMPORTAMENTO CORRETTO. Sei
//    trigger presidiano la disattivazione, e CINQUE guardano l'ESISTENZA dei
//    figli, non le righe attive: un registro che ha visto anche un solo
//    documento — anche annullato — non si spegne più. Per questo il valore di
//    questa schermata non è il cestino: è vedere i registri e governare la
//    forma del numero.
//
// ⭐ E PER LA STESSA RAGIONE C'È «RIATTIVA». I due UNIQUE parziali non filtrano
//    su `attivo`: un registro spento continua a occupare il suo slot, quindi
//    per una terna già occupata non si crea, si RIACCENDE quello che c'è. È il
//    motivo per cui il filtro di stato nasce su «tutti» e non su «solo attivi»:
//    una lista che nasconde gli spenti nasconde le righe che spiegano il
//    rifiuto.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { useRegistriNumerazioneStore } from '../stores/registriNumerazione'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import RegistroNumerazioneDrawer from './RegistroNumerazioneDrawer.vue'
import AttivoTag from '../../core/components/AttivoTag.vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

const { t, te } = useI18n()
const notify = useNotify()
const store = useRegistriNumerazioneStore()
const { confirmAction } = useConfirmAction()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  // ⚠️ È il SOGGETTO-RUOLO dell'emittente, non la PK di `emittenti_fiscali`:
  //    è la colonna su cui `registri_fatturazione` si aggancia
  //    (`feedback_emittente_pk_vs_soggetto_ruolo`). Il nome della prop lo dice,
  //    perché un id passato dalla famiglia sbagliata non solleva niente —
  //    filtra su numeri che non corrispondono e la lista esce vuota.
  emittenteSoggettoRuoloId: { type: Number, required: true },
  emittenteRagioneSociale: { type: String, default: '' },
})

const drawerVisible = ref(false)
const registroSelezionato = ref(null)

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => props.emittenteSoggettoRuoloId,
  parentField: 'emittenteSoggettoRuoloId',
  searchTableOptions: { defaultSortField: 'codice' },
  newTooltipKey: 'amministrazione.registri_numerazione.nuovo_tooltip',
  onNew: () => apri(null),
})

// ⚠️ Il filtro di stato ha TRE valori, non due: «tutti» è `null` e non
//    l'assenza del campo. Un `v-model` su un booleano non saprebbe dire
//    «tutti», e il default cadrebbe su «solo attivi» — che è esattamente la
//    lista che nasconde le righe che spiegano il rifiuto.
const opzioniStato = computed(() => [
  { value: null, label: t('amministrazione.registri_numerazione.stato_tutti') },
  { value: true, label: t('amministrazione.registri_numerazione.stato_attivi') },
  { value: false, label: t('amministrazione.registri_numerazione.stato_disattivati') },
])

function applicaFiltroStato(valore) {
  store.filters.attivo = valore
  store.filters.offset = 0
  store.fetchList()
}

function apri(riga) {
  registroSelezionato.value = riga?.id ?? null
  drawerVisible.value = true
}

// Scopo: spegne o riaccende il registro, con la conferma sul verbo giusto.
// ⛔ Qui non si ricontrolla se si PUÒ spegnere: a rifiutare sono i sei trigger,
//    e il pulsante è già spento quando la check dice di no. Un controllo in più
//    qui sarebbe un settimo elenco che diverge in silenzio.
function cambiaAttivo(riga, attivo) {
  confirmAction({
    header: t('common.confirm'),
    message: attivo
      ? t('amministrazione.registri_numerazione.riattiva_confirm', { codice: riga.codice })
      : t('amministrazione.registri_numerazione.disattiva_confirm', { codice: riga.codice }),
    danger: !attivo,
    // ⛔ Fino al 2026-10-23 l'errore finiva in un `catch` vuoto, «gestito
    //    dall'interceptor axios globale»: l'interceptor di `core/api.js` non
    //    mostra toast, e il rifiuto di uno dei sei trigger restava muto.
    onAccept: async () => {
      const esito = await execute(() => store.cambiaAttivo(riga.id, attivo))
      if (esito === null) return
      notify.success(attivo
        ? t('amministrazione.registri_numerazione.riattivato')
        : t('amministrazione.registri_numerazione.disattivato'))
    },
  })
}

// Scopo: le azioni di riga. ⭐ Due verbi bloccabili sulla stessa riga, e ognuno
//        legge il SUO motivo: `rimozione_blocco_*` per lo spegnimento,
//        `forma_blocco_*` per la modifica della forma. Riusare una colonna per
//        l'altra domanda mostrerebbe la frase sbagliata senza che niente
//        fallisca (api.md §12.5.4).
// ⚠️ Il campo si chiama `tooltip`, non `motivo`: `RowActionsMenu` legge solo
//    quello, e da lì ricava sia il tooltip inline sia la riga sotto la voce
//    nel kebab.
function buildRowActions(data) {
  const bloccatoSpegnimento = bloccoAttivo(data, 'rimozione_blocco', 'can_disattivare')
  return [
    {
      key: 'apri',
      label: t('common.edit'),
      icon: MANAGE_ICONS.EDIT,
      command: () => apri(data),
    },
    data.attivo
      ? {
          key: 'disattiva',
          label: t('amministrazione.registri_numerazione.disattiva'),
          icon: MANAGE_ICONS.DELETE,
          severity: 'danger',
          disabled: bloccatoSpegnimento,
          tooltip: bloccatoSpegnimento
            ? motivoBloccoRiga(t, te, data, 'rimozione_blocco')
            : '',
          command: () => cambiaAttivo(data, false),
        }
      : {
          // ⭐ La riattivazione NON è simmetrica allo spegnimento e non ha
          //    guard: è la strada che il §0 impone quando la terna è occupata.
          key: 'riattiva',
          label: t('amministrazione.registri_numerazione.riattiva'),
          icon: MANAGE_ICONS.RELOAD,
          // 🔴 DIFETTO TROVATO IL 2026-09-02, e non dava nessun errore.
          //    `RowActionsMenu` disabilita da sé le azioni sulle righe spente
          //    (`disableWhenInactive`, default true): senza questo escape la
          //    riattivazione era SPENTA su tutti i registri disattivati —
          //    cioè sugli unici su cui ha senso — e il tooltip diceva «azione
          //    non disponibile su record inattivo». La strada che il §0 impone
          //    quando la terna è occupata non era percorribile dalla lista.
          allowWhenInactive: true,
          command: () => cambiaAttivo(data, true),
        },
  ]
}

// Scopo: il motivo per cui la FORMA di quella riga non si tocca — mostrato in
//        lista, non solo dentro il drawer, così si vede quali sezionali sono
//        ormai fissati senza aprirli uno per uno.
function motivoForma(data) {
  return motivoBloccoRiga(t, te, data, 'forma_blocco')
}
</script>

<template>
  <div>
    <DrawerTabLista
      ref="listaRef"
      codice="vendite.registri_numerazione"
      :emittente-esplicito="emittenteSoggettoRuoloId"
      :help-text="t('amministrazione.registri_numerazione.help')"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('amministrazione.registri_numerazione.filtro_placeholder')"
        />
      </template>
      <template #filtri>
        <!-- ⚠️ IL PLACEHOLDER PORTA L'ETICHETTA DEL DEFAULT, e non e' cosmetica:
             il valore di partenza e' `null` = TUTTI, e per PrimeVue `null` e'
             «niente selezionato» — la combo usciva VUOTA su un filtro che era
             attivo e valeva «tutti». Con l'etichetta giusta lo stato di
             partenza e quello scelto a mano si leggono allo stesso modo, che e'
             la verita': sono lo stesso stato. Rilievo di Tid in collaudo,
             2026-09-02. -->
        <Select
          :model-value="store.filters.attivo"
          :options="opzioniStato"
          :placeholder="t('amministrazione.stato_all')"
          option-label="label"
          option-value="value"
          class="app-filter-w-sm"
          @update:model-value="applicaFiltroStato"
        />
      </template>

      <template #cell-prefisso="{ data }">
        {{ data.prefisso || '—' }}
      </template>
      <template #cell-suffisso="{ data }">
        {{ data.suffisso || '—' }}
      </template>
      <template #cell-serie_default="{ data }">
        {{ data.serie_default || '—' }}
      </template>
      <template #cell-utility_codice="{ data }">
        {{ data.utility_codice || '—' }}
      </template>
      <!-- ⛔ NESSUNO slot per `data_insert`: la colonna dichiara a catalogo
           `tipo_dato=datetime` + `formato=datetime_short`, e
           <ListaConfigurabile> ha un formatter built-in che lo applica. Uno
           slot qui non aggiungerebbe niente e toglierebbe l'ora — sarebbe una
           seconda regola di formato accanto al catalogo, e piu' povera. -->
      <!-- ⭐ La forma fissata si vede DALLA LISTA: un'icona con il motivo
           accanto alle cifre, così non serve aprire riga per riga per sapere
           quali sezionali hanno già consegnato numeri. -->
      <template #cell-lunghezza_numero="{ data }">
        {{ data.lunghezza_numero }}
        <i
          v-if="data.forma_blocco_reason"
          v-tooltip.top="motivoForma(data)"
          class="app-forma-bloccata" :class="STATUS_ICONS.BLOCCATO"
        />
      </template>
      <template #cell-attivo="{ data }">
        <!-- ⛔ Il prop si chiama `active`, NON `attivo`: con il nome sbagliato
             Vue non solleva niente, il prop resta al suo default `false` e la
             colonna dice «non attivo» su OGNI riga. Difetto visto in app il
             2026-09-02, su questa lista e sulla gemella. -->
        <AttivoTag :active="data.attivo" />
      </template>
      <!-- v-if sul TEMPLATE dello slot: senza slot `actions` la colonna non si
           monta affatto, che è il comportamento voluto in sola lettura. -->
      <template v-if="!isReadonly" #actions="{ data }">
        <RowActionsMenu
          :row="data"
          :actions="buildRowActions(data)"
        />
      </template>

      <template #empty>
        <div class="app-empty-state">{{ t('amministrazione.registri_numerazione.vuota') }}</div>
      </template>
    </DrawerTabLista>

    <RegistroNumerazioneDrawer
      v-model:visible="drawerVisible"
      :registro-id="registroSelezionato"
      :emittente-ragione-sociale="emittenteRagioneSociale"
      @saved="reloadAll"
    />
  </div>
</template>

<style scoped>
.app-forma-bloccata {
  margin-left: 0.35rem;
  font-size: 0.75rem;
  opacity: 0.65;
}
</style>
