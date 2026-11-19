<script setup>
// Scopo: Drawer dedicato per gestione indirizzi di un soggetto o ruolo.
// Riutilizzabile da: SoggettoDrawer (context='soggetto'), ClienteDrawer (context='ruolo').
// Context 'soggetto': lista piatta + form aggiungi/cambia (via matrice).
// Context 'ruolo': cascata 3 livelli (istanza→ruolo→soggetto) con fonte badge.

import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useFormInline } from '../../core/composables/useFormInline'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useIndirizzoSoggettoForm } from '../composables/useIndirizzoSoggettoForm'
import { collegaIndirizzoSoggettoForm } from '../composables/collegaIndirizzoSoggettoForm'
import { raccogliFormInline } from '../composables/raccogliFormInline'
import {
  listSoggettoIndirizzi, createSoggettoIndirizzo, replaceSoggettoIndirizzo,
  listRuoloIndirizzi, createRuoloIndirizzo, replaceRuoloIndirizzo, deleteRuoloIndirizzo,
  listSoggettoTipiIndirizzo, listRuoloTipiIndirizzo,
  copiaSoggettoIndirizzo, copiaRuoloIndirizzo,
} from '../api/anagrafiche'
import { useAzioneRiga } from '../../core/composables/useAzioneRiga'
import { DRAWER_WIDTH, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { sortByFonte } from '../../core/utils/string'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'
import CopiaIndirizzoDialog from './CopiaIndirizzoDialog.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()
const indirizzo = useIndirizzoSoggettoForm()
const legameIndirizzo = collegaIndirizzoSoggettoForm(indirizzo)

// Context 'soggetto' (default) o 'ruolo': determina quale set di API usare.
// Per 'soggetto': soggettoId = soggetto UUID. Per 'ruolo': soggettoId = soggetto_ruolo_id (int).
// istanzaUtilityId: opzionale, usato in context 'ruolo' per cascata a 3 livelli.
const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: [String, Number], default: null },
  context: { type: String, default: 'soggetto' },
  istanzaUtilityId: { type: Number, default: null },
  // Modalita' SELEZIONE (drawer gestione indirizzi documento): aggiunge per
  // riga l'azione "usa questo" che emette `select(riga)`. I flussi anagrafici
  // esistenti (aggiungi/cambia/elimina) restano invariati. Default off:
  // nessun impatto sui consumatori attuali (ClienteDrawer/SoggettoDrawer).
  selectable: { type: Boolean, default: false },
  selectTooltip: { type: String, default: '' },
})

const isRuolo = computed(() => props.context === 'ruolo')

const emit = defineEmits(['update:visible', 'saved', 'select'])

// Lista indirizzi esistenti
const indirizziList = ref([])
const listLoading = ref(false)
const matriceCompleta = ref([])

// Modalita' form: null = lista, 'create' = aggiungi, 'edit' = cambia. La
// macchina e' il BB core `useFormInline` (sede unica, ok Tid 2026-09-28).
// ⭐ «Cambia» e' lo stato 'edit' della macchina: il form si apre su un
//    indirizzo esistente. Che il salvataggio lo SOSTITUISCA (replace, o
//    cancella + crea sul ruolo) e' il verbo del dominio, e resta qui. Fino a
//    quel giorno gli stati erano 'new'/'replace'.
const { formMode, formAperto, rigaInModifica, nuovaRiga, apriRiga, chiudiForm, ancoraForm } = useFormInline({
  // D-8: cambiare riga col form modificato chiede (il getter e' letto al clic).
  confermaCambio: (p) => chiudiInlineConConferma(p),
})
// L'indirizzo soggetto da sostituire (in modifica).
const replaceId = computed(() => rigaInModifica.value?.id ?? null)
const replaceLabel = ref('')
const comuneInitialItem = ref(null)

// Modifiche non salvate (BB useDrawerFormPreserve) sul form inline
// dell'indirizzo: conta solo a form aperto, e la fotografia si azzera quando
// torna la lista. Chiudere il drawer o annullare il form con modifiche chiede conferma.
const formIndirizzo = computed(() => raccogliFormInline({ indirizzo }))
const {
  fissa: fissaInline,
  modificato: modificatoInline,
  chiudiConConferma: chiudiInlineConConferma,
} = useDrawerFormPreserve(formIndirizzo, { visibile: () => props.visible && formAperto.value })

// Scopo: Carica indirizzi. In context 'ruolo' l'API ritorna indirizzi_ruolo + indirizzi_soggetto
//        con campo 'fonte'. In context 'soggetto' ritorna lista piatta.
async function loadIndirizzi() {
  if (!props.soggettoId) return
  listLoading.value = true
  try {
    if (isRuolo.value) {
      const listParams = props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId } : {}
      const res = await listRuoloIndirizzi(props.soggettoId, listParams)
      const payload = res.data?.data
      if (payload?.indirizzi_ruolo) {
        // Il backend gia' include 'fonte' (utility/ruolo/soggetto) nei dict
        indirizziList.value = sortByFonte([
          ...payload.indirizzi_ruolo,
          ...(payload.indirizzi_soggetto || []),
        ])
      } else {
        indirizziList.value = []
      }
    } else {
      const res = await listSoggettoIndirizzi(props.soggettoId)
      const payload = res.data?.data
      const items = payload?.results || payload || []
      // Ordina per tipo indirizzo alfabetico (coerente con context ruolo)
      indirizziList.value = items.sort((a, b) =>
        (a.tipo_indirizzo_descrizione || '').localeCompare(b.tipo_indirizzo_descrizione || '')
      )
    }
  } catch {
    indirizziList.value = []
  } finally {
    listLoading.value = false
  }
}

// Scopo: Carica i tipi di indirizzo proponibili dal picker del DB (R-2 di
//        brief-db-copia-indirizzo-soggetto): ogni tipo, con `obbligatorio`,
//        `ammesso` e il motivo di chi non lo e'.
//        Context soggetto: il picker del soggetto salvato (natura E tipi che ha gia').
//        Context ruolo: il picker del ruolo, o della sua istanza (`istanzaUtilityId`):
//        la chiave su cui la madre di creazione giudica il tipo gia' presente.
// ⛔ Fino al 2026-11-15 si leggeva la matrice della natura o del tipo di ruolo e si
//    toglievano a mano i tipi della lista: una copia della regola, gia' divergente
//    (ignorava la validita' delle righe di matrice, §3.1 del brief).
async function loadMatrice() {
  if (!props.soggettoId) return
  try {
    const res = isRuolo.value
      ? await listRuoloTipiIndirizzo(
        props.soggettoId,
        props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId } : {},
      )
      : await listSoggettoTipiIndirizzo(props.soggettoId)
    matriceCompleta.value = res.data?.data?.results || []
  } catch {
    matriceCompleta.value = []
  }
}

// La lista e i tipi proponibili insieme: dopo ogni scrittura il picker cambia
// (un tipo creato si spegne col motivo «gia' presente»).
async function ricarica() {
  await Promise.all([loadIndirizzi(), loadMatrice()])
}

// Tipi gia' associati (per filtrare in aggiungi)
const tipiEsistenti = computed(() =>
  new Set(indirizziList.value.map(i => i.tipo_indirizzo_codice_interno))
)

// I tipi che «Aggiungi» puo' proporre: quelli che il picker ammette. Il tipo gia'
// presente lo esclude il DB, col suo motivo.
const matriceDisponibile = computed(() =>
  matriceCompleta.value.filter(m => m.ammesso)
)

// Tipi obbligatori mancanti
const tipiMancanti = computed(() =>
  matriceCompleta.value.filter(m => m.obbligatorio && !tipiEsistenti.value.has(m.codice_interno))
)

// Carica dati quando drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  chiudiForm()
  indirizzo.reset()
  await ricarica()
})

// Blocca save se indirizzo da stradario non trovato (centralizzato in useIndirizzoBase).
// Aggiunge condizione locale: non in modalita' libera.
const addressNotFound = computed(() =>
  !indirizzo.isLibera.value && indirizzo.addressNotFound.value
)

// === Azioni ===

// «Copia come…» (R-4 di brief-db-copia-indirizzo-soggetto). Il motivo che la
// spegne lo dice il REGISTRO delle azioni di riga (BB `useAzioneRiga`): quali
// colonne della riga lo portano, e la sua chiave. Il layer decide il verbo:
// le righe del ruolo (e dell'istanza) col verbo del ruolo, quelle del soggetto
// — anche quando arrivano dalla cascata del ruolo — col verbo del soggetto.
const azioneCopiaSoggetto = useAzioneRiga('COPIA_INDIRIZZO_SOGGETTO')
const azioneCopiaRuolo = useAzioneRiga('COPIA_INDIRIZZO_RUOLO')
const rigaDelRuolo = (ind) => isRuolo.value && ind.fonte !== 'soggetto'

// Le azioni della card, nel kebab (RowActionsMenu): «Cambia» e «Elimina» dove
// la riga e' del layer che il drawer gestisce, «Copia come…» su ogni riga.
function azioniRiga(ind) {
  const visibile = !formMode.value && !isReadonly.value
  const editabile = !isRuolo.value || rigaDelRuolo(ind)
  const copia = rigaDelRuolo(ind) ? azioneCopiaRuolo : azioneCopiaSoggetto
  const labelCopia = t('anagrafiche.indirizzi.copia.azione')
  return [
    {
      key: 'cambia',
      label: t('anagrafiche.indirizzo_soggetto.cambia_indirizzo'),
      icon: MANAGE_ICONS.EDIT,
      visible: visibile && editabile,
      command: () => onStartReplace(ind),
    },
    {
      key: 'copia',
      label: labelCopia,
      icon: MANAGE_ICONS.CLONE,
      visible: visibile,
      disabled: copia.bloccata(ind),
      tooltip: copia.motivo(ind) || labelCopia,
      command: () => onStartCopia(ind),
    },
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: visibile && rigaDelRuolo(ind),
      command: () => onDeleteRuolo(ind),
    },
  ]
}

const copiaVisible = ref(false)
const copiaRiga = ref(null)
const copiaTipi = ref([])

// I tipi in cui copiare: il picker del layer della riga. Per il ruolo, la
// chiave e' la sua (ruolo o istanza della sorgente): la copia resta li'.
async function onStartCopia(ind) {
  const tipi = await execute(() => (rigaDelRuolo(ind)
    ? listRuoloTipiIndirizzo(
      props.soggettoId,
      ind.istanza_utility_id ? { istanza_utility_id: ind.istanza_utility_id } : {},
    )
    : listSoggettoTipiIndirizzo(isRuolo.value ? ind.soggetto_id : props.soggettoId)))
  if (tipi === null) return
  copiaRiga.value = ind
  copiaTipi.value = tipi?.results || []
  copiaVisible.value = true
}

// Scopo: Il titolare di una riga, come lo legge chi copia: il soggetto, il
//        ruolo o il servizio (l'istanza, col codice della sua utility).
function titolareRiga(ind) {
  if (!rigaDelRuolo(ind)) return t('anagrafiche.indirizzi.copia.titolare_soggetto')
  if (ind.fonte === 'istanza') {
    return ind.utility_codice
      ? t('anagrafiche.indirizzi.copia.titolare_servizio', { utility: ind.utility_codice })
      : t('anagrafiche.indirizzi.copia.titolare_servizio_generico')
  }
  return t('anagrafiche.indirizzi.copia.titolare_ruolo')
}
// Da dove e verso dove, per la dialog. ⚠️ La destinazione e' il titolare
// della SORGENTE: il verbo del DB copia nello stesso ruolo e nella stessa
// istanza della riga (`fn_copia_indirizzo_ruolo`), non sulla chiave del
// drawer. La copia sulla chiave del drawer e' la richiesta B al team DB
// (brief-db-copia-indirizzo-destinazione): quando c'e', cambia qui.
const copiaOrigine = computed(() => copiaRiga.value && {
  tipo: copiaRiga.value.tipo_indirizzo_descrizione,
  indirizzo: copiaRiga.value.indirizzo_display || copiaRiga.value.indirizzo_libero || '',
  titolare: titolareRiga(copiaRiga.value),
})
const copiaDestinazione = computed(() => (copiaRiga.value
  ? t('anagrafiche.indirizzi.copia.verso_come_origine', { titolare: titolareRiga(copiaRiga.value) })
  : ''))

async function onConfermaCopia(codici) {
  const ind = copiaRiga.value
  if (!ind || codici.length === 0) return
  const result = await execute(
    () => (rigaDelRuolo(ind)
      ? copiaRuoloIndirizzo(props.soggettoId, ind.id, codici)
      : copiaSoggettoIndirizzo(isRuolo.value ? ind.soggetto_id : props.soggettoId, ind.id, codici)),
    { successMessage: t('anagrafiche.indirizzi.copia.fatta', { n: codici.length }, codici.length) },
  )
  if (result !== null) {
    copiaVisible.value = false
    await ricarica()
    emit('saved')
  }
}

async function onStartNew() {
  nuovaRiga()
  comuneInitialItem.value = null
  indirizzo.reset()
  if (isRuolo.value) {
    // In context ruolo la lista porta anche i livelli della cascata (soggetto,
    // ruolo): i loro tipi restano proponibili sulla chiave del ruolo, ma non si
    // pre-selezionano.
    indirizzo.setMatrice(matriceCompleta.value, tipiEsistenti.value)
  } else {
    indirizzo.setMatrice(matriceDisponibile.value)
  }
  fissaInline()
}

async function onStartReplace(ind) {
  apriRiga(ind, async () => {
    replaceLabel.value = ind.tipo_indirizzo_descrizione
    indirizzo.reset()
    // La matrice per il replace ha solo il tipo da sostituire
    indirizzo.setMatrice([{
      codice_interno: ind.tipo_indirizzo_codice_interno,
      descrizione: ind.tipo_indirizzo_descrizione,
      obbligatorio: true,
    }])
    // Pre-popola tutti i campi dall'indirizzo esistente (se normalizzato).
    // withSuppressedChecks evita che il watcher scateni il check duplicato
    // (troverebbe lo stesso indirizzo che stiamo modificando).
    // Imposta l'id dettaglio esistente: evita il messaggio "indirizzo non presente"
    // (addressNotFound controlla existingDettaglioId).
    indirizzo.existingDettaglioId.value = ind.indirizzo_dettaglio_id || null
    indirizzo.withSuppressedChecks(() => {
      if (ind.det_comune_id && ind.stradario_id) {
        comuneInitialItem.value = { id: ind.det_comune_id, descrizione: ind.descrizione_comune }
        indirizzo.form.comune_id = ind.det_comune_id
        indirizzo.form.via_obj = {
          stradario_id: ind.stradario_id,
          indirizzo_normalizzato: ind.stradario_display || ind.indirizzo_display,
        }
        indirizzo.form.civico = ind.civico ?? null
        indirizzo.form.estensione_civico = (ind.estensione_civico || '').replace(/^\//, '')
        indirizzo.form.palazzina = ind.palazzina || ''
        indirizzo.form.scala = ind.scala || ''
        indirizzo.form.piano = ind.piano || ''
        indirizzo.form.interno = ind.interno || ''
      } else {
        comuneInitialItem.value = null
      }
    })
    // Fotografia DOPO i CAP: il watch del comune (useIndirizzoBase) gira dopo
    // `withSuppressedChecks`, azzera il CAP e, se il comune ne ha uno solo, lo
    // reimposta da se' a lookup arrivato. Fissare prima farebbe nascere il form
    // «modificato» senza che l'operatore abbia toccato niente.
    await nextTick()
    if (indirizzo.loadingCap.value) {
      await new Promise((fine) => {
        const stop = watch(indirizzo.loadingCap, (caricando) => {
          if (!caricando) { stop(); fine() }
        })
      })
    }
    if (formMode.value === 'edit' && replaceId.value === ind.id) fissaInline()
  })
}

function onCancelForm() {
  chiudiForm()
  comuneInitialItem.value = null
  indirizzo.reset()
}

async function onSaveForm() {
  const payloads = indirizzo.toPayloadArray()
  if (!payloads.length) return

  let success = true

  if (isRuolo.value && formMode.value === 'edit' && replaceId.value) {
    // Context ruolo + replace: il BE cancella e riscrive in UNA transazione
    // (PUT, gemello del soggetto). ⛔ Non DELETE + POST: dal 2026-11-17 la
    // DELETE dell'unico obbligatorio, giudicata da sola, e' rifiutata — e col
    // `silent` di allora il salvataggio falliva senza dire niente.
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    if (props.istanzaUtilityId) {
      payload.istanza_utility_id = props.istanzaUtilityId
    }
    const result = await execute(
      () => replaceRuoloIndirizzo(props.soggettoId, replaceId.value, payload),
      { successMessage: t('indirizzi.indirizzo_salvato') }
    )
    if (result === null) success = false
  } else if (isRuolo.value) {
    // Context ruolo + new: crea nuovo indirizzo
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    if (props.istanzaUtilityId) {
      payload.istanza_utility_id = props.istanzaUtilityId
    }
    const result = await execute(
      () => createRuoloIndirizzo(props.soggettoId, payload),
      { successMessage: t('indirizzi.indirizzo_creato') }
    )
    if (result === null) success = false
  } else if (formMode.value === 'edit') {
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    const result = await execute(
      () => replaceSoggettoIndirizzo(props.soggettoId, replaceId.value, payload),
      { successMessage: t('indirizzi.indirizzo_salvato') }
    )
    if (result === null) success = false
  } else {
    for (const p of payloads) {
      const result = await execute(
        () => createSoggettoIndirizzo(props.soggettoId, p),
        { successMessage: t('indirizzi.indirizzo_creato') }
      )
      if (result === null) { success = false; break }
    }
  }

  if (success) {
    chiudiForm()
    indirizzo.reset()
    await ricarica()
    emit('saved')
  }
}

// Scopo: Elimina indirizzo ruolo (solo context ruolo).
async function onDeleteRuolo(ind) {
  const result = await execute(
    () => deleteRuoloIndirizzo(props.soggettoId, ind.id),
    { successMessage: t('indirizzi.indirizzo_eliminato') }
  )
  if (result !== null) {
    await ricarica()
    emit('saved')
  }
}

const annullaForm = () => chiudiInlineConConferma(onCancelForm)
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('indirizzi.indirizzo') + ' - ' + t(`anagrafiche.indirizzo_soggetto.context_${context}`)"
    :icon="NAV_ICONS.INDIRIZZO"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificatoInline"
    :conferma-uscita="chiudiInlineConConferma"
    :footer="formMode ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- Loading -->
    <div v-if="listLoading" class="app-loading">
      <i :class="STATUS_ICONS.CARICAMENTO" />
    </div>

    <!-- Lista indirizzi esistenti (sempre visibile) -->
    <template v-if="!listLoading">
      <!-- Contenuto del caller sopra la lista (es. indirizzi gia' impostati
           sul documento in modalita' selezione). -->
      <slot name="pre-list" />
      <div v-if="indirizziList.length === 0 && !formMode" class="app-empty-state">
        <i :class="MANAGE_ICONS.INDIRIZZI" />
        <p>{{ t('anagrafiche.indirizzo_soggetto.nessun_indirizzo') }}</p>
      </div>

      <div v-else-if="indirizziList.length > 0" class="indirizzi-list">
        <div v-for="ind in indirizziList" :key="ind.id" class="indirizzo-select-row">
        <div
          class="indirizzo-card" :class="{ 'indirizzo-card-soggetto': ind.fonte === 'soggetto', 'indirizzo-card-ruolo': ind.fonte === 'ruolo' || ind.fonte === 'istanza' }">
          <div class="indirizzo-card-content">
            <div class="indirizzo-card-nome">
              <Tag v-if="ind.fonte" :value="ind.fonte === 'soggetto' ? t('common.soggetto') : (ind.fonte === 'istanza' && ind.utility_codice ? ind.utility_codice : t('common.ruolo'))"
                :severity="ind.fonte === 'soggetto' ? 'secondary' : 'info'" />
              <Tag :value="ind.tipo_indirizzo_descrizione" severity="info" />
            </div>
            <div class="indirizzo-card-detail">
              <span class="indirizzo-card-text">{{ ind.indirizzo_display || ind.indirizzo_libero }}</span>
              <span v-if="ind.comune_descrizione || ind.descrizione_comune" class="indirizzo-card-comune">
                {{ ind.comune_descrizione || ind.descrizione_comune }}
                <template v-if="ind.cap || ind.cap_codice"> — {{ ind.cap || ind.cap_codice }}</template>
                <template v-if="ind.provincia_sigla"> ({{ ind.provincia_sigla }})</template>
              </span>
            </div>
          </div>
          <!-- Azioni della card nel kebab (R-4): Cambia, Copia come… (spenta
               col motivo del registro), Elimina sulle righe del ruolo. -->
          <div v-if="!formMode && !isReadonly" class="indirizzo-card-actions">
            <RowActionsMenu :row="ind" :actions="azioniRiga(ind)" force-compact />
          </div>
        </div>
        <!-- Colonna ESTERNA "Usa" (modalita' selezione documento): fuori
             dalla card per non ereditare l'opacita' dei box soggetto. -->
        <Button
          v-if="selectable && !formMode && !isReadonly"
          :icon="MANAGE_ICONS.SELEZIONA"
          :label="t('anagrafiche.indirizzo_soggetto.usa')"
          outlined
          size="small"
          class="app-action-btn indirizzo-card-usa"
          :title="selectTooltip || t('anagrafiche.indirizzo_soggetto.usa_questo')"
          @click="emit('select', ind)"
        />
        </div>
      </div>

      <!-- Warning tipi mancanti -->
      <div v-if="tipiMancanti.length > 0 && !formMode" class="indirizzi-warning">
        <i :class="STATUS_ICONS.ERRORE" />
        {{ t('anagrafiche.indirizzo_soggetto.tipi_mancanti', { tipi: tipiMancanti.map(t => t.descrizione).join(', ') }) }}
      </div>

      <!-- Pulsante aggiungi: se il picker del DB ammette almeno un tipo, sul soggetto e sul
           ruolo (dal 2026-11-15 il ruolo legge il suo picker), mai in readonly -->
      <div v-if="!formMode && !isReadonly && matriceDisponibile.length > 0" class="mt-05">
        <Button
          :label="t('anagrafiche.indirizzo_soggetto.aggiungi_indirizzo')"
          :icon="MANAGE_ICONS.ADD"
          text
          size="small"
          class="app-action-btn"
          @click="onStartNew"
        />
        <!-- Azioni extra del caller accanto ad "aggiungi" (es. indirizzo
             libero una-tantum in modalita' selezione documento). -->
        <slot name="extra-actions" />
      </div>
    </template>

    <!-- Form (aggiungi o cambia) -->
    <template v-if="formMode">
      <div :ref="ancoraForm" class="app-drawer-section">
        <h4>{{ formMode === 'edit'
          ? t('anagrafiche.indirizzo_soggetto.cambia_indirizzo') + ': ' + replaceLabel
          : t('anagrafiche.indirizzo_soggetto.nuovo_indirizzo')
        }}</h4>
      </div>
      <!-- ⚠️ `address-not-found` spento DOPO il v-bind: l'avviso lo mostra il
           drawer (`replace_non_trovato`, sotto), e il form ne aggiungerebbe un
           secondo. Fino al 2026-11-18 la prop qui mancava e basta. -->
      <IndirizzoSoggettoForm
        v-bind="legameIndirizzo"
        :campi-errati="campiErrati"
        :tipi-esistenti="[...tipiEsistenti]"
        :comune-initial-item="comuneInitialItem"
        :address-not-found="false"
      />

      <Message v-if="addressNotFound" severity="warn" size="small" class="mt-1">
        {{ t('anagrafiche.indirizzo_soggetto.replace_non_trovato') }}
      </Message>

      <FormFooter
        :loading="loading"
        :disabled="!indirizzo.canSave.value || addressNotFound"
        @save="onSaveForm"
        @cancel="annullaForm"
      />
    </template>

    <CopiaIndirizzoDialog
      v-model:visible="copiaVisible"
      :tipi="copiaTipi"
      :sorgente="copiaRiga?.tipo_indirizzo_descrizione || ''"
      :origine="copiaOrigine"
      :destinazione="copiaDestinazione"
      :loading="loading"
      @confirm="onConfermaCopia"
    />
  </AppDrawer>
</template>

<style scoped>
.indirizzi-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.indirizzo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-sm, 4px);
  padding: 0.5rem 0.75rem;
}

.indirizzo-card-content {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.indirizzo-card-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.indirizzo-card-text {
  font-size: 0.85rem;
  color: var(--app-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.indirizzo-card-soggetto {
  border-color: var(--app-fonte-soggetto-color);
  opacity: 0.5;
}
.indirizzo-card-ruolo {
  border-color: var(--p-blue-300);
}

.indirizzo-card-nome {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.indirizzo-card-comune {
  font-size: 0.75rem;
  color: var(--app-text-muted);
}

.indirizzo-card-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.indirizzi-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-top: 0.5rem;
  background: var(--p-yellow-50);
  border: 1px solid var(--p-yellow-200);
  border-radius: var(--p-border-radius-sm, 4px);
  font-size: 0.8rem;
  color: var(--p-yellow-700);
}
.indirizzo-select-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.indirizzo-select-row .indirizzo-card {
  flex: 1 1 auto;
  min-width: 0;
}
.indirizzo-card-usa {
  flex: 0 0 auto;
}
</style>
