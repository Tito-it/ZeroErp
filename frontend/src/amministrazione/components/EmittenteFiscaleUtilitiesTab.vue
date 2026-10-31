<script setup>
// Scopo: Tab autonomo riusabile per la matrice utility -> emittente fiscale.
// Pattern slot/override: la lista mostra TUTTE le utility ammesse per il ruolo EF
// (LEFT JOIN con config.utilities_tipi_ruolo). Per ogni riga l'operatore puo':
//   - Configurare (POST): crea il record in emittenti_fiscali_utilities
//   - Modificare (PATCH): aggiorna parametri esistenti
//   - Rimuovere configurazione (DELETE): elimina il record, la riga torna "non configurata"
// Editing inline multi-riga: piu' righe possono essere in modifica contemporaneamente.
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
import ToggleSwitch from 'primevue/toggleswitch'
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
//        si vedono utility da configurare.
function goToMatriceUtilitiesRuoli() {
  router.push({ name: 'amm-software-matrice-utilities-ruoli' })
}

const props = defineProps({
  emittenteId: { type: Number, required: true },
  // Stato attivo del padre: serve per il vincolo DB ATTIVO_require (figlio non puo'
  // essere attivo se il padre e' disattivato). Se false, blocchiamo l'attivazione
  // delle righe lato UI per evitare l'errore di trigger.
  emittenteAttivo: { type: Boolean, default: true }
})

// `metodo_arrotondamento_importi`: Select riusabile EmittenteRoundingModeSelect
// (Fase 3 — A6). 4 codici allineati al CHECK constraint DB
// `chk_emittenti_fiscali_utilities_metodo_arrotondamento` (UP/DOWN/HALF_UP/HALF_DOWN).
// `arrotondamento_importi_dec`: range in `ROUNDING_DECIMALI_RANGE` (constants.js),
// specchio del CHECK chk_emittenti_fiscali_utilities_arrotondamento_dec (0..2).

// ⚠️ I tre `InputNumber` della riga hanno anche `@input`, oltre al v-model:
//    PrimeVue aggiorna il v-model SOLO all'uscita dal campo (blur) o con le
//    frecce, mentre il «Salva riga» si accende da `isRowValid`, che legge il
//    modello. Senza, scelto il metodo e scritti i decimali, il Salva restava
//    spento finche' il cursore stava nel campo — e cliccare un pulsante
//    disabilitato non toglie il fuoco, quindi non si accendeva mai
//    (segnalazione di Tid, 2026-10-31; presidio: lo spec di questo file).
// Stato editing per riga: chiave = utility_id, valore = oggetto editabile.
// Permette multi-riga: piu' righe possono essere in editing contemporaneamente.
// Niente default: i campi sono vuoti finche' l'utente non li compila.
const editing = reactive({})

function isEditing(row) {
  return editing[row.utility_id] !== undefined
}

function isConfigured(row) {
  return row.record_id != null
}

// Inizializza il form di editing per una riga.
// Se la riga e' configurata copia i valori esistenti, altrimenti parte vuoto.
// Se il padre e' disattivo, forziamo attivo=false (vincolo DB ATTIVO_require).
function startEdit(row) {
  const defaultAttivo = props.emittenteAttivo
  editing[row.utility_id] = isConfigured(row)
    ? {
        minimo_soglia_min: row.minimo_soglia_min,
        minimo_soglia_max: row.minimo_soglia_max,
        arrotondamento_importi_dec: row.arrotondamento_importi_dec,
        metodo_arrotondamento_importi: row.metodo_arrotondamento_importi,
        attivo: props.emittenteAttivo ? (row.record_attivo ?? true) : false
      }
    : {
        minimo_soglia_min: null,
        minimo_soglia_max: null,
        arrotondamento_importi_dec: null,
        metodo_arrotondamento_importi: null,
        attivo: defaultAttivo
      }
}

function cancelEdit(row) {
  delete editing[row.utility_id]
}

// Validazione: per salvare la riga servono ALMENO i due campi obbligatori
// (decimali + metodo arrotondamento). Le soglie sono opzionali.
function isRowValid(row) {
  const e = editing[row.utility_id]
  if (!e) return false
  const hasDec = e.arrotondamento_importi_dec != null
                 && e.arrotondamento_importi_dec >= ROUNDING_DECIMALI_RANGE.MIN
                 && e.arrotondamento_importi_dec <= ROUNDING_DECIMALI_RANGE.MAX
  const hasMetodo = !!e.metodo_arrotondamento_importi
  return hasDec && hasMetodo
}

// Salva la riga: POST se non configurata, PATCH se gia' configurata.
// ⛔ Fino al 2026-10-23 qui non c'era `execute`, «errori gestiti
//    dall'interceptor axios globale»: ma l'interceptor di `core/api.js` non
//    mostra toast, e un rifiuto restava muto. `execute` accetta anche l'azione
//    di uno store (il dato gia' estratto): il «doppio unwrap» che si temeva
//    tocca solo un payload con una chiave `data`, e la riga utility non ce l'ha.
async function saveRow(row) {
  if (!isRowValid(row)) {
    notify.warn(t('amministrazione.emittenti_fiscali.ut_validation_required'))
    return
  }
  const e = editing[row.utility_id]
  const payload = {
    minimo_soglia_min: e.minimo_soglia_min,
    minimo_soglia_max: e.minimo_soglia_max,
    arrotondamento_importi_dec: e.arrotondamento_importi_dec,
    metodo_arrotondamento_importi: e.metodo_arrotondamento_importi,
    attivo: e.attivo
  }
  const configurata = isConfigured(row)
  if (!configurata) payload.utility_id = row.utility_id
  const esito = await execute(() => (configurata
    ? store.patchUtilityRecord(props.emittenteId, row.record_id, payload)
    : store.addUtilityRecord(props.emittenteId, payload)))
  if (esito === null) return
  notify.success(configurata
    ? t('amministrazione.emittenti_fiscali.ut_saved')
    : t('amministrazione.emittenti_fiscali.ut_added'))
  cancelEdit(row)
  await caricaMatrice(props.emittenteId)
}

function removeConfig(row) {
  confirmAction({
    header: t('common.confirm'),
    message: t('amministrazione.emittenti_fiscali.ut_remove_config_confirm', { codice: row.utility_codice }),
    danger: true,
    onAccept: async () => {
      // ⚠️ L'azione non restituisce niente (`undefined`): l'errore e' `null`.
      const esito = await execute(() => store.removeUtilityRecord(props.emittenteId, row.record_id))
      if (esito === null) return
      notify.success(t('amministrazione.emittenti_fiscali.ut_removed'))
      await caricaMatrice(props.emittenteId)
    }
  })
}

// Scopo: azioni di riga matrice utility — non in modalita' edit (che usa
// pulsanti inline form Salva/Annulla). Azioni differenti per stato:
//   - riga configurata: Modifica + Rimuovi (danger)
//   - riga non configurata: Configura (primary)
//
// Fase 4 — capability data-driven dal BE (`can_update`, `can_remove`,
// `can_configure`). Fallback alla derivazione locale `isConfigured(row)`
// se il BE non ha ancora popolato i campi (mock obsoleti, transizione,
// retrocompat). L'autorita' resta il trigger DB
// (`child_requires_active_parent`, `guard_utility_tipo_ruolo`).
function buildRowActions(row) {
  const configured = isConfigured(row)
  const canUpdate = row.can_update ?? configured
  const canRemove = row.can_remove ?? configured
  const canConfigure = row.can_configure ?? !configured
  return [
    {
      key: 'modifica',
      label: t('amministrazione.emittenti_fiscali.ut_action_modifica'),
      icon: MANAGE_ICONS.EDIT,
      visible: canUpdate,
      allowWhenInactive: true,
      command: () => startEdit(row),
    },
    {
      key: 'rimuovi',
      label: t('amministrazione.emittenti_fiscali.ut_action_rimuovi_config'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: canRemove,
      command: () => removeConfig(row),
    },
    {
      key: 'configura',
      label: t('amministrazione.emittenti_fiscali.ut_action_configura'),
      icon: MANAGE_ICONS.ADD,
      severity: 'primary',
      visible: canConfigure,
      command: () => startEdit(row),
    },
  ]
}

// Scopo: (ri)legge la matrice e, se non arriva, lo DICE (`execute`) e la svuota.
//        ⭐ Separata dalle scritture: una rilettura che fallisce dopo un POST
//        riuscito non fa sembrare fallito il POST.
// ⛔ Fino al 2026-10-23 l'errore finiva in un `catch` che svuotava e basta:
//    l'operatore vedeva una matrice vuota che sembrava una risposta.
async function caricaMatrice(id) {
  const esito = await execute(() => store.fetchUtilitiesRecords(id))
  if (esito === null) store.clearUtilitiesRecords()
}

// Carica matrice quando l'id dell'emittente cambia.
// La store action delega al backend che fa LEFT JOIN matrice + override.
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

    <!-- Matrice limitata dal catalogo (`MatriceCatalogo`, dal 2026-10-31): tutte
         le utility ammesse per il ruolo, configurate o no. NON `MatriceOverride`:
         una utility non configurata non eredita un valore da nessuno — e' solo
         da configurare. Modifica e salvataggio sono PER RIGA, nello slot azioni. -->
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
              v-if="isConfigured(data)"
              :value="t('amministrazione.emittenti_fiscali.ut_stato_configurata')"
              severity="success"
            />
            <Tag
              v-else
              :value="t('amministrazione.emittenti_fiscali.ut_stato_non_configurata')"
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
            <span v-else>{{ data.minimo_soglia_min ?? '—' }}</span>
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
            <span v-else>{{ data.minimo_soglia_max ?? '—' }}</span>
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
            <span v-else>{{ data.arrotondamento_importi_dec ?? '—' }}</span>
          </template>
        </Column>

        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_metodo')" style="width: 170px; min-width: 170px;">
          <template #body="{ data }">
            <EmittenteRoundingModeSelect
              v-if="isEditing(data)"
              v-model="editing[data.utility_id].metodo_arrotondamento_importi"
              class="ut-cell-input"
            />
            <span v-else>{{ data.metodo_arrotondamento_importi ?? '—' }}</span>
          </template>
        </Column>

        <Column :header="t('amministrazione.emittenti_fiscali.ut_col_attivo')" style="width: 90px; min-width: 90px;">
          <template #body="{ data }">
            <ToggleSwitch
              v-if="isEditing(data)"
              v-model="editing[data.utility_id].attivo"
              :disabled="!emittenteAttivo"
              v-tooltip.bottom="!emittenteAttivo ? t('amministrazione.emittenti_fiscali.ut_parent_inactive_tooltip') : null"
            />
            <Tag
              v-else-if="data.record_attivo === true"
              :value="t('amministrazione.stato_attivo')"
              severity="success"
            />
            <Tag
              v-else-if="data.record_attivo === false"
              :value="t('amministrazione.stato_inattivo')"
              severity="danger"
            />
            <span v-else>—</span>
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
