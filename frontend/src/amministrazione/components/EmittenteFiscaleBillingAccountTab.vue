<script setup>
// Scopo: Tab autonomo riusabile: i clienti (billing account) di un emittente
// fiscale, IN CONSULTAZIONE, configurabile
// (`<ListaConfigurabile codice="anagrafiche.emittente_billing_account">`):
// colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`.
// Lista paginata con search su ragione_sociale/codice BA/id_fiscale.
// L'unica cosa che si fa qui e' rendere l'emittente l'azienda PREDEFINITA (in
// cui nascono i clienti creati senza sessione): il pulsante sopra la lista.
// Nessuna azione di riga.
// ⛔ Dal 2026-11-27 (giro 6 di brief-db-revisione-anagrafiche, D-T4-3; Tid,
//    §26.2) un cliente NON si aggiunge e non si toglie da qui: ogni billing
//    account nasce col suo collegamento a un'azienda e non lo perde mai. Prima
//    c'erano il lookup del BA con «Aggiungi» e il cestino di riga: il primo
//    urtava il vincolo unico (il collegamento c'e' gia'), il secondo lo
//    rifiuta il database (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`), anche sulla
//    predefinita, che si sposta e non si cancella.
//
// ⭐ CONVERTITO AL BB `DrawerTabLista` + `useDrawerTabLista` il 2026-09-01.
//    Questo tab ERA il pattern: il legame col padre (watch immediate, reset
//    filtri, doppia fetch) e lo scheletro di markup vivevano qui, unici
//    esemplari. Col secondo tab-lista (i registri di numerazione) sarebbero
//    diventati due copie, quindi il pattern e' salito nel core e questo file
//    lo CONSUMA. ⛔ Non e' cortesia verso il BB: un building block estratto e
//    lasciato accanto alla sua copia sono due implementazioni della stessa
//    regola, e la copia diverge in silenzio.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliBAStore } from '../stores/emittentiFiscaliBA'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import PredefinitoSegno from '../../core/components/PredefinitoSegno.vue'

const { t } = useI18n()
const store = useEmittentiFiscaliBAStore()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
// ⛔ Fino al 2026-10-23 le tre scritture finivano in un `catch` vuoto, «gestito
//    dall'interceptor axios globale»: l'interceptor di `core/api.js` non mostra
//    toast, e un rifiuto restava muto. Ora passano da `execute`.
const { execute } = useApiHandler()

// Scopo: rilegge il summary e, se non arriva, lo DICE (lo store lo lascia
//        risalire). ⭐ Separato dalle scritture: un summary che fallisce dopo
//        un POST riuscito non fa sembrare fallito il POST.
function caricaSummary() {
  return execute(() => store.fetchSummary())
}
const isReadonly = useInjectReadonly()

const props = defineProps({
  emittenteId: { type: Number, required: true }
})

// ⭐ Il `fetchExtra` NON e' un di piu': il summary e' indipendente dalla
//    pagina corrente (vedi A8/C3 del WIP), e senza di lui `hasDefault`
//    derivato da `store.items` sbagliava quando il record default era fuori
//    dalla pagina paginata. Il BB lo tiene allineato in tutti e due i momenti
//    in cui conta — al cambio di emittente e sul pulsante "Ricarica".
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(store, {
  parentId: () => props.emittenteId,
  parentField: 'emittenteId',
  fetchExtra: caricaSummary,
})

// Pulsante «rendi predefinita» spento se QUESTO emittente lo e' gia' (la riga
// puo' stare in qualsiasi pagina). La fonte di verita' e' il summary BE.
const hasDefault = computed(() => store.hasDefaultMapping)

// Scopo: rende questo emittente l'azienda predefinita, con conferma: decide
//        in quale azienda nascono i clienti creati senza sessione, e toglie il
//        ruolo all'azienda che lo aveva. ⛔ La riga si SPOSTA (UPDATE), non si
//        cancella e ricrea: il DB rifiuta la cancellazione di ogni collegamento.
function rendiPredefinito() {
  confirmAction({
    header: t('common.confirm'),
    message: t('amministrazione.emittenti_fiscali.ba_rendi_predefinita_confirm'),
    onAccept: async () => {
      const esito = await execute(() => store.impostaPredefinito())
      if (esito === null) return
      notify.success(t('amministrazione.emittenti_fiscali.ba_predefinita_impostata'))
      await caricaSummary()
    },
  })
}
</script>

<template>
  <DrawerTabLista
    ref="listaRef"
    codice="anagrafiche.emittente_billing_account"
    :emittente-esplicito="emittenteId"
    :help-text="t('amministrazione.emittenti_fiscali.ba_help')"
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
    <!-- La predefinita ha il suo pulsante SOPRA la lista, non un drawer:
         e' il motivo per cui lo scaffolding non riceve `onNew` e per cui il
         BB espone lo slot `testata`. -->
    <template #testata>
      <div v-if="!isReadonly">
        <div>
          <Button
            :label="t('amministrazione.emittenti_fiscali.ba_rendi_predefinita')"
            :icon="MANAGE_ICONS.PREDEFINITO"
            severity="secondary"
            :disabled="hasDefault"
            @click="rendiPredefinito"
          />
        </div>
      </div>
    </template>

    <template #filtri-sempre>
      <InputText
        v-model="searchText"
        class="app-filter-w-lg"
        :placeholder="t('amministrazione.emittenti_fiscali.ba_filter_placeholder')"
      />
    </template>

    <!-- `is_default` e' una colonna vera del catalogo (boolean, ordinabile):
         il segno del predefinito al posto del "Si'/No". ⏭️ Lo slot si toglie
         quando la riga 269 di `ui.lista_colonna` porta `formato=predefinito`
         (richiesta al team DB, 2026-11-26): la resa e' gia' quella del BB. -->
    <template #cell-is_default="{ data }">
      <PredefinitoSegno :value="data.is_default" />
    </template>
    <template #cell-billing_account_codice="{ data }">
      {{ data.billing_account_codice || '—' }}
    </template>
    <template #cell-billing_account_ragione_sociale="{ data }">
      {{ data.billing_account_ragione_sociale || t('amministrazione.emittenti_fiscali.ba_default_label') }}
    </template>
    <!-- Slot sul `codice` della colonna (`id_fiscale`), non sul campo letto
         (`id_fiscale_univoco`): sono due nomi diversi. -->
    <template #cell-id_fiscale="{ data }">
      {{ data.id_fiscale_univoco || '—' }}
    </template>

    <template #empty>
      <div class="app-empty-state">{{ t('amministrazione.emittenti_fiscali.ba_empty') }}</div>
    </template>
  </DrawerTabLista>
</template>
