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
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { ROUNDING_METHODS, ROUNDING_DECIMALI_RANGE } from '../constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  emittenteId: { type: Number, required: true },
  // Stato attivo del padre: serve per il vincolo DB ATTIVO_require (figlio non puo'
  // essere attivo se il padre e' disattivato). Se false, blocchiamo l'attivazione
  // delle righe lato UI per evitare l'errore di trigger.
  emittenteAttivo: { type: Boolean, default: true }
})

// Costanti centralizzate (vedi amministrazione/constants.js): allineate al CHECK
// constraint DB su anagrafiche.emittenti_fiscali_utilities.
// Riusate anche da EmittenteFiscaleDrawer.vue per il campo rounding_policy.

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
// Pattern: store action gia' unwrappate, NIENTE useApiHandler.execute()
// (l'execute mostrerebbe un toast errore spurio per via del double-unwrap).
// Errori reali sono gestiti dall'interceptor axios globale.
async function saveRow(row) {
  if (!isRowValid(row)) {
    notify.warn(t('amm_emittenti_fiscali.ut_validation_required'))
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
  try {
    if (isConfigured(row)) {
      await store.patchUtilityRecord(props.emittenteId, row.record_id, payload)
      notify.success(t('amm_emittenti_fiscali.ut_saved'))
    } else {
      payload.utility_id = row.utility_id
      await store.addUtilityRecord(props.emittenteId, payload)
      notify.success(t('amm_emittenti_fiscali.ut_added'))
    }
    cancelEdit(row)
  } catch {
    // Errore gia' notificato dall'interceptor axios globale: nessuna azione qui.
  }
}

function removeConfig(row) {
  confirmAction({
    title: t('common.confirm'),
    message: t('amm_emittenti_fiscali.ut_remove_config_confirm', { codice: row.utility_codice }),
    danger: true,
    onAccept: async () => {
      try {
        await store.removeUtilityRecord(props.emittenteId, row.record_id)
        notify.success(t('amm_emittenti_fiscali.ut_removed'))
      } catch {
        // Errore gia' notificato dall'interceptor axios globale.
      }
    }
  })
}

// Scopo: azioni di riga matrice utility — non in modalita' edit (che usa
// pulsanti inline form Salva/Annulla). Azioni differenti per stato:
//   - riga configurata: Modifica + Rimuovi (danger)
//   - riga non configurata: Configura (primary)
function buildRowActions(row) {
  const configured = isConfigured(row)
  return [
    {
      key: 'modifica',
      label: t('amm_emittenti_fiscali.ut_action_modifica'),
      icon: 'pi pi-pencil',
      visible: configured,
      command: () => startEdit(row),
    },
    {
      key: 'rimuovi',
      label: t('amm_emittenti_fiscali.ut_action_rimuovi_config'),
      icon: 'pi pi-trash',
      severity: 'danger',
      visible: configured,
      command: () => removeConfig(row),
    },
    {
      key: 'configura',
      label: t('amm_emittenti_fiscali.ut_action_configura'),
      icon: 'pi pi-plus',
      severity: 'primary',
      visible: !configured,
      command: () => startEdit(row),
    },
  ]
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
  try {
    await store.fetchUtilitiesRecords(id)
  } catch (e) {
    store.clearUtilitiesRecords()
  }
}, { immediate: true })
</script>

<template>
  <div class="app-tab-content">
    <Message severity="info" :closable="false" class="mb-3">
      {{ t('amm_emittenti_fiscali.ut_help_matrix') }}
    </Message>

    <Message v-if="!emittenteAttivo" severity="warn" :closable="false" class="mb-3">
      {{ t('amm_emittenti_fiscali.ut_parent_inactive_warn') }}
    </Message>

    <DataTable
      :value="store.utilitiesRecords"
      striped-rows
      scrollable
      class="app-datatable ut-matrix-table"
      data-key="utility_id"
      table-style="min-width: 1260px"
    >
      <Column :header="t('amm_emittenti_fiscali.ut_col_stato')" style="width: 140px; min-width: 140px;">
        <template #body="{ data }">
          <Tag
            v-if="isConfigured(data)"
            :value="t('amm_emittenti_fiscali.ut_stato_configurata')"
            severity="success"
          />
          <Tag
            v-else
            :value="t('amm_emittenti_fiscali.ut_stato_non_configurata')"
            severity="secondary"
          />
        </template>
      </Column>

      <Column field="utility_codice" :header="t('amm_emittenti_fiscali.ut_col_codice')" style="width: 100px; min-width: 100px;" />
      <Column field="utility_descrizione" :header="t('amm_emittenti_fiscali.ut_col_descrizione')" style="min-width: 180px;" />

      <Column :header="t('amm_emittenti_fiscali.ut_col_soglia_min')" style="width: 150px; min-width: 150px;">
        <template #body="{ data }">
          <InputNumber
            v-if="isEditing(data)"
            v-model="editing[data.utility_id].minimo_soglia_min"
            :min-fraction-digits="2" :max-fraction-digits="6"
            fluid
            class="ut-cell-input"
            :input-class="'ut-cell-input-el'"
          />
          <span v-else>{{ data.minimo_soglia_min ?? '—' }}</span>
        </template>
      </Column>

      <Column :header="t('amm_emittenti_fiscali.ut_col_soglia_max')" style="width: 150px; min-width: 150px;">
        <template #body="{ data }">
          <InputNumber
            v-if="isEditing(data)"
            v-model="editing[data.utility_id].minimo_soglia_max"
            :min-fraction-digits="2" :max-fraction-digits="6"
            fluid
            class="ut-cell-input"
            :input-class="'ut-cell-input-el'"
          />
          <span v-else>{{ data.minimo_soglia_max ?? '—' }}</span>
        </template>
      </Column>

      <Column :header="t('amm_emittenti_fiscali.ut_col_dec')" style="width: 120px; min-width: 120px;">
        <template #body="{ data }">
          <InputNumber
            v-if="isEditing(data)"
            v-model="editing[data.utility_id].arrotondamento_importi_dec"
            :min="ROUNDING_DECIMALI_RANGE.MIN" :max="ROUNDING_DECIMALI_RANGE.MAX"
            showButtons
            buttonLayout="stacked"
            fluid
            class="ut-cell-input"
            :input-class="'ut-cell-input-el'"
          />
          <span v-else>{{ data.arrotondamento_importi_dec ?? '—' }}</span>
        </template>
      </Column>

      <Column :header="t('amm_emittenti_fiscali.ut_col_metodo')" style="width: 170px; min-width: 170px;">
        <template #body="{ data }">
          <Select
            v-if="isEditing(data)"
            v-model="editing[data.utility_id].metodo_arrotondamento_importi"
            :options="ROUNDING_METHODS"
            option-label="label"
            option-value="value"
            fluid
            class="ut-cell-input"
          />
          <span v-else>{{ data.metodo_arrotondamento_importi ?? '—' }}</span>
        </template>
      </Column>

      <Column :header="t('amm_emittenti_fiscali.ut_col_attivo')" style="width: 90px; min-width: 90px;">
        <template #body="{ data }">
          <ToggleSwitch
            v-if="isEditing(data)"
            v-model="editing[data.utility_id].attivo"
            :disabled="!emittenteAttivo"
            v-tooltip.bottom="!emittenteAttivo ? t('amm_emittenti_fiscali.ut_parent_inactive_tooltip') : null"
          />
          <Tag
            v-else-if="data.record_attivo === true"
            :value="t('amm.stato_attivo')"
            severity="success"
          />
          <Tag
            v-else-if="data.record_attivo === false"
            :value="t('amm.stato_inattivo')"
            severity="danger"
          />
          <span v-else>—</span>
        </template>
      </Column>

      <Column
        v-if="!isReadonly"
        :header="t('common.col_azioni')"
        class="app-col-actions"
        :exportable="false"
        frozen
        alignFrozen="right"
      >
        <template #body="{ data }">
          <!-- Editing in corso: Salva + Annulla restano inline (form affordance,
               non azioni di riga). Devono essere sempre visibili su ogni device. -->
          <template v-if="isEditing(data)">
            <Button
              icon="pi pi-check"
              text rounded size="small"
              severity="success"
              :disabled="!isRowValid(data)"
              v-tooltip.bottom="t('amm_emittenti_fiscali.ut_action_salva_riga')"
              @click="saveRow(data)"
            />
            <Button
              icon="pi pi-times"
              text rounded size="small"
              severity="secondary"
              v-tooltip.bottom="t('amm_emittenti_fiscali.ut_action_annulla')"
              @click="cancelEdit(data)"
            />
          </template>
          <!-- Stato normale: azioni standard via RowActionsMenu. -->
          <RowActionsMenu v-else :actions="buildRowActions(data)" />
        </template>
      </Column>

      <template #empty>
        <div class="app-empty">{{ t('amm_emittenti_fiscali.ut_empty_matrix') }}</div>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
/* Vincola gli input PrimeVue (InputNumber, Select) alla larghezza della cella della
   matrice utility. Senza questo, in editing l'input wrapper sfora la colonna perche'
   il min-width interno del componente prevale sul width della Column. */
.ut-matrix-table :deep(.ut-cell-input) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  display: flex;
}
.ut-matrix-table :deep(.ut-cell-input .p-inputnumber-input),
.ut-matrix-table :deep(.ut-cell-input-el) {
  width: 100%;
  min-width: 0;
}
/* InputNumber con showButtons stacked: i bottoni hanno larghezza fissa, l'input
   deve restringersi per stare nel resto della cella. */
.ut-matrix-table :deep(.ut-cell-input.p-inputnumber) {
  flex-wrap: nowrap;
}
</style>
