<script setup>
// Scopo: Tab autonomo riusabile per la gestione del mapping BA -> emittente
// fiscale, configurabile
// (`<ListaConfigurabile codice="anagrafiche.emittente_billing_account">`):
// colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`.
// Lista paginata con search su ragione_sociale/codice BA/id_fiscale.
// Nessuna azione "Nuovo": l'inserimento ha una sua form sopra la lista (lookup
// BA + i due pulsanti), quindi lo scaffolding non riceve `onNew`.
//
// ⭐ CONVERTITO AL BB `DrawerTabLista` + `useDrawerTabLista` il 2026-09-01.
//    Questo tab ERA il pattern: il legame col padre (watch immediate, reset
//    filtri, doppia fetch) e lo scheletro di markup vivevano qui, unici
//    esemplari. Col secondo tab-lista (i registri di numerazione) sarebbero
//    diventati due copie, quindi il pattern e' salito nel core e questo file
//    lo CONSUMA. ⛔ Non e' cortesia verso il BB: un building block estratto e
//    lasciato accanto alla sua copia sono due implementazioni della stessa
//    regola, e la copia diverge in silenzio.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliBAStore } from '../stores/emittentiFiscaliBA'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { motivoBloccoRiga, bloccoAttivo } from '../../core/utils/bloccoMotivo'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Badge from 'primevue/badge'

const { t, te } = useI18n()
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

const selectedBA = ref(null)
const adding = ref(false)

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
  searchTableOptions: { defaultSortField: 'billing_account_codice' },
})

// Pulsante "default" disabilitato se il default esiste a livello di emittente
// (qualsiasi pagina). La fonte di verita' e' il summary BE, non la pagina FE.
const hasDefault = computed(() => store.hasDefaultMapping)

async function addSpecificMapping() {
  if (!selectedBA.value?.id) {
    notify.warn(t('amministrazione.emittenti_fiscali.ba_select_required'))
    return
  }
  adding.value = true
  try {
    const esito = await execute(() => store.addMapping({ billing_account_id: selectedBA.value.id }))
    if (esito === null) return
    notify.success(t('amministrazione.emittenti_fiscali.ba_added'))
    selectedBA.value = null
    await caricaSummary()
  } finally {
    adding.value = false
  }
}

async function addDefaultMapping() {
  if (hasDefault.value) {
    notify.warn(t('amministrazione.emittenti_fiscali.ba_default_exists'))
    return
  }
  const esito = await execute(() => store.addMapping({}))
  if (esito === null) return
  notify.success(t('amministrazione.emittenti_fiscali.ba_default_added'))
  await caricaSummary()
}

function removeMapping(row) {
  confirmAction({
    header: t('common.confirm'),
    message: row.is_default
      ? t('amministrazione.emittenti_fiscali.ba_remove_default_confirm')
      : t('amministrazione.emittenti_fiscali.ba_remove_confirm', { codice: row.billing_account_codice || '-' }),
    danger: true,
    onAccept: async () => {
      // ⚠️ L'azione non restituisce niente (`undefined`): l'errore e' `null`.
      const esito = await execute(() => store.removeMapping(row.id))
      if (esito === null) return
      notify.success(t('amministrazione.emittenti_fiscali.ba_removed'))
      await caricaSummary()
    }
  })
}

// Scopo: il nome leggibile di una famiglia di documento (Fattura, DDT, …).
// ⚠️ Vocabolario APERTO: le famiglie stanno in `vendite.famiglie_documento` e
//    una nuova arriva con un seed, non con un rilascio del frontend. Quindi
//    `labelOrCode` con ripiego sulla `descrizione` che il database manda
//    accanto al codice: una famiglia senza chiave i18n si vede col suo nome di
//    catalogo, non sparisce e non mostra il path della chiave.
function nomeFamiglia(voce) {
  const codice = String(voce?.famiglia ?? '')
  return labelOrCode(
    t, te,
    `vendite.famiglie_documento.${codice}`,
    voce?.descrizione || codice,
  )
}

// Scopo: azioni di riga mapping BA (rimozione con conferma), nascoste in readonly.
//
// ⭐ IL MOTIVO ARRIVA DAL DATABASE, non si ricalcola qui. Un billing account
//    che ha gia' un documento NUMERATO su un registro non cambia piu'
//    emittente, e togliere il suo mapping lo farebbe ricadere sul gestore
//    globale: e' un cambio di emittente, e viene rifiutato. Fino al 2026-08-27
//    il cestino era acceso lo stesso e l'operatore lo scopriva premendo — dopo
//    aver confermato un dialog. Ora la riga porta `can_remove` e il motivo del
//    primo blocco, prodotti da `script.fn_check_ba_cambio_emittente`: la STESSA
//    funzione che la madre chiama per rifiutare, quindi tooltip ed errore non
//    possono divergere (`linee-guida-sql` 12.5).
// ⚠️ «Numerato», non «fatture o commesse»: dal 2026-08-31 DDT, ordini, resi e
//    commesse prendono il numero dagli stessi registri delle fatture, e la
//    storia si deriva da `vendite.famiglie_documento`. Una frase che ne nomina
//    due manderebbe a cercare fatture a un cliente bloccato da un DDT.
// ⛔ Permesso => nascondi, stato => disabilita col motivo (12.1): qui e' uno
//    stato — la storia del cliente puo' solo crescere, ma il mapping resta a
//    video con la sua spiegazione invece di sparire senza dire niente.
// ⚠️ Il campo si chiama `tooltip`, non `motivo`: RowActionsMenu legge solo
//    quello, e da li' ricava sia il tooltip inline sia la riga sotto la voce
//    nel kebab.

// Scopo: il motivo del blocco in testo leggibile — chiave i18n se c'e',
//        altrimenti il codice macchina. Stesso ripiego di `useDrawerActions`.
//
// ⭐ E QUANDO IL DATABASE MANDA L'ELENCO, IL TOOLTIP DICE QUANTO DICE IL
//    RIFIUTO. Fino al 2026-08-31 il tooltip diceva «ha documenti numerati» e
//    il 409 diceva «Fattura: 3, DDT: 1»: due gradi di dettaglio sulla stessa
//    condizione, e chi si fermava al tooltip non sapeva DOVE guardare. Ora
//    `rimozione_blocco_storia` porta le stesse righe da cui il DB compone la
//    frase del rifiuto, e le due superfici raccontano lo stesso fatto.
// ⛔ Il testo NON viaggia nel payload: viaggia il DATO (`{famiglia,
//    descrizione, n}`) e la frase si compone qui dai `locales` — e' la regola
//    di api.md §12.5.4, ed e' il motivo per cui questa funzione esiste invece
//    di stampare una stringa gia' pronta.
// ⚠️ L'elenco e' un'AGGIUNTA, non una sostituzione: la frase del motivo resta
//    la prima cosa che si legge. Senza `storia` — la riga del gestore globale,
//    il cui blocco e' il singleton e non la storia — si degrada da se' alla
//    sola frase, che li' e' la risposta completa.
function motivoBlocco(data) {
  // ⭐ La frase base la compone il BB `bloccoMotivo` (regola del 2, 2026-09-01):
  //    e' la stessa lettura che fa la maschera dei registri di numerazione, su
  //    un verbo diverso. Qui resta solo cio' che e' PROPRIO di questo tab —
  //    l'elenco dei documenti che bloccano.
  const frase = motivoBloccoRiga(t, te, data, 'rimozione_blocco')
  // ⚠️ `Array.isArray` e non `?.length`: se un domani il repository smettesse
  //    di decodificare il jsonb, `storia` sarebbe una STRINGA — che ha una
  //    `.length` e si lascia iterare a caratteri. Il guard sul tipo e' l'unico
  //    che distingue «non c'e' storia» da «e' arrivata nella forma sbagliata».
  const storia = Array.isArray(data.rimozione_blocco_storia)
    ? data.rimozione_blocco_storia
    : []
  if (!storia.length) return frase
  const elenco = storia.map((v) => `${nomeFamiglia(v)}: ${v?.n ?? '?'}`).join(', ')
  // ⛔ `filter(Boolean)` e non `${frase} ${elenco}`: concatenare due pezzi a
  //    mano stampa uno spazio in testa quando il primo manca. E' la stessa
  //    regola che `shape_indirizzi_context` scrive per i template.
  return [frase, t('amministrazione.emittenti_fiscali.ba_blocco.elenco', { elenco })]
    .filter(Boolean)
    .join(' ')
}

function buildRowActions(data) {
  const bloccato = bloccoAttivo(data, 'rimozione_blocco', 'can_remove')
  return [
    {
      key: 'rimuovi-mapping',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      disabled: bloccato,
      // Fail-visible su DUE livelli, ed e' lo stesso ripiego di
      // `useDrawerActions`: senza CHIAVE si mostra il codice macchina (che
      // dice comunque qualcosa), con la chiave ma senza traduzione ci pensa
      // `labelOrCode`. ⛔ La chiave si guarda PRIMA di passarla: il database
      // puo' emettere un motivo senza `reason_key`, e chiedere a `te()` di
      // controllare un valore nullo non e' una domanda che ha senso fare.
      tooltip: bloccato ? motivoBlocco(data) : '',
      command: () => removeMapping(data),
    },
  ]
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
    <!-- L'inserimento del mapping ha una form SOPRA la lista, non un drawer:
         e' il motivo per cui lo scaffolding non riceve `onNew` e per cui il
         BB espone lo slot `testata`. -->
    <template #testata>
      <div v-if="!isReadonly" class="form-grid-2col">
        <BillingAccountLookup
          v-model="selectedBA"
          :placeholder="t('amministrazione.emittenti_fiscali.ba_search_placeholder')"
        />
        <div>
          <Button
            :label="t('amministrazione.emittenti_fiscali.ba_add_specific')"
            :icon="MANAGE_ICONS.ADD"
            :loading="adding"
            :disabled="!selectedBA?.id"
            @click="addSpecificMapping"
          />
          <Button
            :label="t('amministrazione.emittenti_fiscali.ba_add_default')"
            :icon="MANAGE_ICONS.PREDEFINITO"
            severity="secondary"
            :disabled="hasDefault"
            @click="addDefaultMapping"
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
         lo slot serve solo a tenere il Badge al posto del "Si'/No". -->
    <template #cell-is_default="{ data }">
      <Badge v-if="data.is_default" :value="t('common.default')" severity="info" />
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

    <!-- v-if sul TEMPLATE dello slot: senza slot `actions` ne' il BB ne'
         <ListaConfigurabile> montano la colonna, come la <Column v-if>
         pre-conversione. -->
    <template v-if="!isReadonly" #actions="{ data }">
      <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
    </template>

    <template #empty>
      <div class="app-empty-state">{{ t('amministrazione.emittenti_fiscali.ba_empty') }}</div>
    </template>
  </DrawerTabLista>
</template>
