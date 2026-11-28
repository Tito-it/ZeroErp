<script setup>
// Scopo: Tab autonomo riusabile: le utility che un'azienda (emittente fiscale)
// GESTISCE (brief-db-utility-gestite-dall-emittente §10 R-3, D-U-5, D-U-8, B-8).
// La lista mostra TUTTE le utility che la matrice ammette per il ruolo EF
// (dal BB del DB `anagrafiche.fn_utilities_emittente`). Per ogni riga il
// SUPER_ADMIN puo':
//   - Attivare (POST col solo `utility_id`): l'azienda gestisce l'utility, e da
//     li' puo' averne clienti e documenti
//   - Modificare i parametri (PATCH): tutti facoltativi, un campo vuoto = vale
//     la policy dell'azienda o il valore di sistema (si vede l'effettivo)
//   - Togliere i parametri (PATCH a NULL): l'utility resta gestita
//   - Disattivare (DELETE): il DB lo rifiuta se un billing account o un
//     documento usa l'utility
// ⛔ Non c'e' un interruttore `attivo`: la riga non ha uno stato suo (D-U-11).
// Editing inline multi-riga: piu' righe possono essere in modifica insieme.
// Reagisce automaticamente al cambio di emittenteId.
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { ROUNDING_DECIMALI_RANGE } from '../constants'
import Column from 'primevue/column'
import MatriceCatalogo from '../../core/components/MatriceCatalogo.vue'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import EmittenteRoundingModeSelect from './EmittenteRoundingModeSelect.vue'

const { t } = useI18n()
const router = useRouter()
const store = useEmittentiFiscaliStore()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()

// Scopo: Naviga alla pagina admin matrice utilities/ruoli da empty
//        state. La matrice e' prerequisito di questo drawer: senza
//        righe per ruolo EF lato `config.utilities_tipi_ruolo` qui non
//        si vedono utility da attivare.
function goToMatriceUtilitiesRuoli() {
  router.push({ name: 'amm-software-matrice-utilities-ruoli' })
}

const props = defineProps({
  emittenteId: { type: Number, required: true },
  // Sotto un emittente spento non nasce niente: niente attivazioni (lo dice
  // anche la capability `can_attivare` del BE, che resta l'autorita').
  emittenteAttivo: { type: Boolean, default: true }
})

// I quattro parametri d'importo della riga, tutti facoltativi.
const PARAMETRI = [
  'minimo_soglia_min',
  'minimo_soglia_max',
  'arrotondamento_importi_dec',
  'metodo_arrotondamento_importi',
]

// `metodo_arrotondamento_importi`: Select riusabile EmittenteRoundingModeSelect
// (Fase 3 — A6). 4 codici allineati al CHECK constraint DB
// `chk_emittenti_fiscali_utilities_metodo_arrotondamento` (UP/DOWN/HALF_UP/HALF_DOWN).
// `arrotondamento_importi_dec`: range in `ROUNDING_DECIMALI_RANGE` (constants.js),
// specchio del CHECK chk_emittenti_fiscali_utilities_arrotondamento_dec (0..2).

// ⚠️ I tre `InputNumber` della riga hanno anche `@input`, oltre al v-model:
//    PrimeVue aggiorna il v-model SOLO all'uscita dal campo (blur) o con le
//    frecce, mentre il «Salva riga» si accende da `isRowValid`, che legge il
//    modello. Senza, il Salva restava fermo finche' il cursore stava nel campo
//    (segnalazione di Tid, 2026-10-31; presidio: lo spec di questo file).
// Stato editing per riga: chiave = utility_id, valore = i parametri scritti.
const editing = reactive({})

function isEditing(row) {
  return editing[row.utility_id] !== undefined
}

function isGestita(row) {
  return row.record_id != null
}

// Il valore che vale per la riga: quello scritto, altrimenti l'effettivo che
// il BB del DB risolve (policy dell'azienda, poi sistema). `scritto` dice se
// viene dalla riga: l'effettivo si mostra sottotono (B-8: fino al 2026-11-27
// la matrice mostrava solo il valore grezzo, e un vuoto non diceva cosa valeva).
function valore(row, campo) {
  const scritto = row[campo]
  if (scritto != null) return { testo: scritto, scritto: true }
  const effettivo = row[`effettivo_${campo}`]
  return { testo: effettivo ?? '—', scritto: false }
}

function startEdit(row) {
  editing[row.utility_id] = Object.fromEntries(PARAMETRI.map(k => [k, row[k] ?? null]))
}

function cancelEdit(row) {
  delete editing[row.utility_id]
}

// Validazione: ogni parametro e' facoltativo; i decimali, se scritti, stanno
// nell'intervallo del vincolo. La coppia delle soglie la giudica il DB (CHECK
// `chk_emittenti_fiscali_utilities_soglie_coppia`, tradotto dal BE).
function isRowValid(row) {
  const e = editing[row.utility_id]
  if (!e) return false
  const dec = e.arrotondamento_importi_dec
  return dec == null
    || (dec >= ROUNDING_DECIMALI_RANGE.MIN && dec <= ROUNDING_DECIMALI_RANGE.MAX)
}

// Scopo: (ri)legge la matrice dopo una scrittura riuscita.
async function dopoScrittura(row, messaggio) {
  notify.success(messaggio)
  if (row) cancelEdit(row)
  await caricaMatrice(props.emittenteId)
}

// Attiva l'utility per l'azienda: la riga nasce senza parametri.
// ⛔ `execute` sempre: l'interceptor di `core/api.js` non mostra toast, e un
//    rifiuto (utility non ammessa, emittente spento) resterebbe muto.
async function attiva(row) {
  const esito = await execute(() => store.addUtilityRecord(props.emittenteId, { utility_id: row.utility_id }))
  if (esito === null) return
  await dopoScrittura(null, t('amministrazione.emittenti_fiscali.ut_attivata', { codice: row.utility_codice }))
}

async function saveRow(row) {
  if (!isRowValid(row)) return
  const payload = { ...editing[row.utility_id] }
  const esito = await execute(() => store.patchUtilityRecord(props.emittenteId, row.record_id, payload))
  if (esito === null) return
  await dopoScrittura(row, t('amministrazione.emittenti_fiscali.ut_saved'))
}

// Toglie i parametri propri: tornano quelli dell'azienda e di sistema, e
// l'utility resta gestita. NON cancella la riga: quella e' la disattivazione.
function resetParametri(row) {
  confirmAction({
    header: t('common.confirm'),
    message: t('amministrazione.emittenti_fiscali.ut_reset_confirm', { codice: row.utility_codice }),
    onAccept: async () => {
      const payload = Object.fromEntries(PARAMETRI.map(k => [k, null]))
      const esito = await execute(() => store.patchUtilityRecord(props.emittenteId, row.record_id, payload))
      if (esito === null) return
      await dopoScrittura(null, t('amministrazione.emittenti_fiscali.ut_reset_done'))
    }
  })
}

// Disattiva: toglie l'utility all'azienda. Il DB la rifiuta se un billing
// account o un documento la usa (messaggio tradotto dal BE, D-U-9).
function disattiva(row) {
  confirmAction({
    header: t('common.confirm'),
    message: t('amministrazione.emittenti_fiscali.ut_disattiva_confirm', { codice: row.utility_codice }),
    danger: true,
    onAccept: async () => {
      // ⚠️ L'azione non restituisce niente (`undefined`): l'errore e' `null`.
      const esito = await execute(() => store.removeUtilityRecord(props.emittenteId, row.record_id))
      if (esito === null) return
      await dopoScrittura(null, t('amministrazione.emittenti_fiscali.ut_disattivata', { codice: row.utility_codice }))
    }
  })
}

// Scopo: azioni di riga — non in modifica (che usa Salva/Annulla inline).
//   - non gestita: Attiva
//   - gestita: Modifica parametri, Togli i parametri (se ne ha), Disattiva
// Le capability (`can_attivare`, `can_update`, `can_reset`, `can_remove`)
// vengono dal BE; l'autorita' resta il DB.
function buildRowActions(row) {
  return [
    {
      key: 'attiva',
      label: t('amministrazione.emittenti_fiscali.ut_action_attiva'),
      icon: MANAGE_ICONS.ADD,
      severity: 'primary',
      visible: !!row.can_attivare,
      command: () => attiva(row),
    },
    {
      key: 'modifica',
      label: t('amministrazione.emittenti_fiscali.ut_action_modifica'),
      icon: MANAGE_ICONS.EDIT,
      visible: !!row.can_update,
      allowWhenInactive: true,
      command: () => startEdit(row),
    },
    {
      key: 'reset',
      label: t('amministrazione.emittenti_fiscali.ut_action_reset'),
      icon: MANAGE_ICONS.RIPRISTINA_DEFAULT,
      visible: !!row.can_reset,
      allowWhenInactive: true,
      command: () => resetParametri(row),
    },
    {
      key: 'disattiva',
      label: t('amministrazione.emittenti_fiscali.ut_action_disattiva'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !!row.can_remove,
      allowWhenInactive: true,
      command: () => disattiva(row),
    },
  ]
}

// Scopo: (ri)legge la matrice e, se non arriva, lo DICE (`execute`) e la svuota.
//        ⭐ Separata dalle scritture: una rilettura che fallisce dopo un POST
//        riuscito non fa sembrare fallito il POST.
async function caricaMatrice(id) {
  const esito = await execute(() => store.fetchUtilitiesRecords(id))
  if (esito === null) store.clearUtilitiesRecords()
}

watch(() => props.emittenteId, async (id) => {
  if (!id) {
    store.clearUtilitiesRecords()
    return
  }
  // Reset editing state quando cambia emittente (le righe in editing perdono senso)
  for (const k of Object.keys(editing)) delete editing[k]
  await caricaMatrice(id)
}, { immediate: true })
</script>

<template>
  <div class="app-tab-content">
    <Message severity="info" :closable="false">
      {{ t('amministrazione.emittenti_fiscali.ut_help_matrix') }}
    </Message>

    <Message v-if="!emittenteAttivo" severity="warn" :closable="false">
      {{ t('amministrazione.emittenti_fiscali.ut_parent_inactive_warn') }}
    </Message>

    <!-- Matrice limitata dal catalogo (`MatriceCatalogo`): tutte le utility
         ammesse per il ruolo EF, gestite o no. NON `MatriceOverride`: una
         utility non gestita non eredita niente, si attiva. Modifica e
         salvataggio sono PER RIGA, nello slot azioni. -->
    <MatriceCatalogo
      :voci="store.utilitiesRecords"
      :chiave="r => r.utility_id"
      :label-voce="t('amministrazione.emittenti_fiscali.ut_col_descrizione')"
      class="ut-matrix-table"
    >
      <template #voce="{ voce }">
        {{ voce.utility_codice }} — {{ voce.utility_descrizione }}
      </template>
      <template #colonne>
        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_stato')" style="width: 140px; min-width: 140px;">
          <template #body="{ data }">
            <Tag
              v-if="isGestita(data)"
              :value="t('amministrazione.emittenti_fiscali.ut_stato_gestita')"
              severity="success"
            />
            <Tag
              v-else
              :value="t('amministrazione.emittenti_fiscali.ut_stato_non_gestita')"
              severity="secondary"
            />
          </template>
        </Column>
        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_soglia_min')" style="width: 150px; min-width: 150px;">
          <template #body="{ data }">
            <InputNumber
              v-if="isEditing(data)"
              v-model="editing[data.utility_id].minimo_soglia_min"
              @input="(e) => (editing[data.utility_id].minimo_soglia_min = e.value)"
              :min-fraction-digits="2" :max-fraction-digits="6"
              class="ut-cell-input"
              :input-class="'ut-cell-input-el'"
            />
            <span v-else :class="{ 'app-text-muted': !valore(data, 'minimo_soglia_min').scritto }">
              {{ valore(data, 'minimo_soglia_min').testo }}
            </span>
          </template>
        </Column>

        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_soglia_max')" style="width: 150px; min-width: 150px;">
          <template #body="{ data }">
            <InputNumber
              v-if="isEditing(data)"
              v-model="editing[data.utility_id].minimo_soglia_max"
              @input="(e) => (editing[data.utility_id].minimo_soglia_max = e.value)"
              :min-fraction-digits="2" :max-fraction-digits="6"
              class="ut-cell-input"
              :input-class="'ut-cell-input-el'"
            />
            <span v-else :class="{ 'app-text-muted': !valore(data, 'minimo_soglia_max').scritto }">
              {{ valore(data, 'minimo_soglia_max').testo }}
            </span>
          </template>
        </Column>

        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_dec')" style="width: 120px; min-width: 120px;">
          <template #body="{ data }">
            <InputNumber
              v-if="isEditing(data)"
              v-model="editing[data.utility_id].arrotondamento_importi_dec"
              @input="(e) => (editing[data.utility_id].arrotondamento_importi_dec = e.value)"
              :min="ROUNDING_DECIMALI_RANGE.MIN" :max="ROUNDING_DECIMALI_RANGE.MAX"
              showButtons
              buttonLayout="stacked"
              class="ut-cell-input ut-cell-input--dec"
              :input-class="'ut-cell-input-el'"
            />
            <span v-else :class="{ 'app-text-muted': !valore(data, 'arrotondamento_importi_dec').scritto }">
              {{ valore(data, 'arrotondamento_importi_dec').testo }}
            </span>
          </template>
        </Column>

        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_metodo')" style="width: 170px; min-width: 170px;">
          <template #body="{ data }">
            <EmittenteRoundingModeSelect
              v-if="isEditing(data)"
              v-model="editing[data.utility_id].metodo_arrotondamento_importi"
              show-clear
              class="ut-cell-input"
            />
            <span v-else :class="{ 'app-text-muted': !valore(data, 'metodo_arrotondamento_importi').scritto }">
              {{ valore(data, 'metodo_arrotondamento_importi').testo }}
            </span>
          </template>
        </Column>
      </template>
      <template #azioni="{ voce: data }">
        <!-- Editing in corso: Salva + Annulla restano inline (form affordance,
             non azioni di riga). Devono essere sempre visibili su ogni device. -->
        <template v-if="isEditing(data)">
          <Button
            :icon="MANAGE_ICONS.CONFIRM"
            text rounded size="small"
            severity="success"
            :disabled="!isRowValid(data)"
            v-tooltip.bottom="t('amministrazione.emittenti_fiscali.ut_action_salva_riga')"
            @click="saveRow(data)"
          />
          <Button
            :icon="MANAGE_ICONS.CANCEL"
            text rounded size="small"
            severity="secondary"
            v-tooltip.bottom="t('amministrazione.emittenti_fiscali.ut_action_annulla')"
            @click="cancelEdit(data)"
          />
        </template>
        <!-- Stato normale: azioni standard via RowActionsMenu. -->
        <RowActionsMenu v-else :row="data" :actions="buildRowActions(data)" />
      </template>
      <template #empty>
        <div class="app-empty-state">
          <i class="ut-empty-icon" :class="STATUS_ICONS.VUOTO" />
          <div class="ut-empty-msg">{{ t('amministrazione.emittenti_fiscali.ut_empty_matrix') }}</div>
          <div class="ut-empty-hint">{{ t('amministrazione.emittenti_fiscali.ut_empty_matrix_hint') }}</div>
          <Button
            v-if="!isReadonly"
            :label="t('amministrazione.emittenti_fiscali.ut_empty_matrix_cta')"
            :icon="MANAGE_ICONS.VAI_A"
            text
            size="small"
            @click="goToMatriceUtilitiesRuoli"
          />
        </div>
      </template>
    </MatriceCatalogo>
  </div>
</template>

<style scoped>
/* I campi della riga in modifica hanno una larghezza ESPLICITA, ed e' la
   larghezza a decidere la colonna. ⛔ Non `fluid` / `width: 100%`: la tabella
   e' `width: max-content` (`.app-datatable`), cioe' e' la cella a prendere la
   misura dal contenuto, e una percentuale del contenitore li' non limita
   niente — ogni input tornava alla sua larghezza naturale (~20 caratteri) e le
   sette colonne in modifica superavano il drawer: barra orizzontale appena si
   premeva «Configura» o «Modifica» (segnalazione di Tid, 2026-10-31). */
.ut-matrix-table :deep(.ut-cell-input-el) {
  width: 7rem;
  min-width: 0;
}
/* I decimali: due cifre di testo PIU' lo spazio delle frecce impilate.
   ⛔ Non un numero solo: con `buttonLayout="stacked"` PrimeVue mette le frecce
   SOPRA il campo (posizione assoluta, a destra) e gli riserva un margine
   interno pari alla loro larghezza piu' il padding. A 3.5rem (2026-10-31, una
   correzione sbagliata) il testo non aveva spazio: il numero non si vedeva e
   il clic cadeva sulle frecce, quindi non si riusciva a scrivere. La misura
   si compone dai token del tema, cosi' segue le frecce se cambiano. */
.ut-matrix-table :deep(.ut-cell-input--dec .ut-cell-input-el) {
  width: calc(2ch + var(--p-inputnumber-button-width, 2.5rem) + 2 * var(--p-form-field-padding-x, 0.75rem));
}
.ut-matrix-table :deep(.ut-cell-input.p-inputnumber) {
  flex-wrap: nowrap;
}
/* Il metodo: l'etichetta lunga («descrizione (codice)») si taglia coi puntini
   dentro il Select, invece di allargare la colonna. */
.ut-matrix-table :deep(.p-select.ut-cell-input) {
  width: 11rem;
}
/* Il contenitore e' `app-empty-state` (main.css): fino al 17/09 qui c'era una
 * copia identica, `.ut-empty`, accanto a un `app-empty` che non esisteva. */
.ut-empty-icon {
  font-size: 2rem;
  color: var(--app-text-muted);
}
.ut-empty-msg {
  font-weight: 500;
}
.ut-empty-hint {
  color: var(--app-text-muted);
  font-size: 0.9rem;
  max-width: 480px;
}
</style>
