<script setup>
// Scopo: Sezione integrazione preventivo — push commessa (fatturazione), genera pratica, pratiche collegate.
// Visibilita' governata dal flag BE `can_push_commessa` (gating del parent
// PreventiviDrawer): ACCETTATO con righe ancora pushable e EVASO post-push
// completato. La pratica e' opzionale: il preventivo puo' essere eseguito
// anche senza pratica (fatturazione diretta via commessa).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useNotify } from '../../../core/composables/useNotify'
import { usePreventiviStore } from '../stores/preventivi'
import { statoPraticaSeverity } from '../../../core/utils/severity'
import { displayDate } from '../../../core/utils/date'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  preventivoId: { type: Number, required: true }
})
// `push-completato` notifica il drawer padre che il push e' andato a buon
// fine (totale o parziale) e che testata + capabilities vanno ricaricate:
// la transizione automatica ACCETTATO -> EVASO (BE-driven, vedi
// preventivi_service.push_a_commessa) si vede solo dopo un loadDetail.
const emit = defineEmits(['push-completato'])

const statoFatturazione = ref(null)
const pratiche = ref([])
const loadingFatt = ref(false)
const loadingPratiche = ref(false)

// Scopo: il pulsante "Invia a fatturazione" si disabilita quando le righe
// sono gia' tutte in commessa (push completato e idempotente). Previene
// re-click superflui senza nascondere il pulsante (utile resta lo stato
// visuale "fatto"). `tutte_in_commessa` true se totale=0 e' edge case
// (preventivo senza righe), quindi richiediamo totale>0.
const tutteRighePushate = computed(() => {
  const sf = statoFatturazione.value
  if (!sf) return false
  // BE espone `righe_totali` (vw_preventivi_stato_fatturazione). Il nome
  // FE precedente `totale_righe` era un disallineamento silente: undefined
  // → totale=0 → pulsante mai nascosto. Fix 2026-05-10.
  const totale = sf.righe_totali ?? 0
  const inCommessa = sf.righe_in_commessa ?? 0
  return totale > 0 && inCommessa >= totale
})

// Scopo: Carica stato fatturazione e pratiche collegate.
async function loadIntegrazione() {
  if (!props.preventivoId) return
  loadingFatt.value = true
  loadingPratiche.value = true
  try {
    statoFatturazione.value = await store.loadStatoFatturazione(props.preventivoId)
  } finally {
    loadingFatt.value = false
  }
  try {
    pratiche.value = await store.loadPratiche(props.preventivoId)
  } finally {
    loadingPratiche.value = false
  }
}

watch(() => props.preventivoId, loadIntegrazione, { immediate: true })

// Scopo: Push preventivo in commessa per fatturazione.
//
// Toast differenziato per `result.stato` dell'orchestrator (HTTP 200 risponde
// anche con esito PARZIALE/ERRORE per riga, quindi non basta il successMessage
// generico di useApiHandler — qui gestiamo manualmente):
//   COMPLETATO  -> success con push_log_id
//   PARZIALE    -> warn con push_log_id
//   ERRORE      -> error con primo errore di handler
//   SKIPPED     -> warn ("push gia' in corso")
//
// Se il preventivo ha `fatturazione_immediata=TRUE` aggiunge un info hint
// che chiarisce all'utente che l'emit verso AF avverra' al prossimo run
// pipeline lotto (PR2 implementera' il servizio "emissione immediata"
// dedicato — vedi WIP sviluppo-push-singolo-preventivo §9).
function onPushCommessa() {
  confirmAction({
    message: t('preventivi.conferma_push_commessa'),
    onAccept: async () => {
      const result = await execute(
        () => store.inviaACommessa(props.preventivoId),
        // No successMessage: gestiamo il toast in base a result.stato sotto.
      )
      if (result === null) return  // errore HTTP gia' gestito da useApiHandler

      const stato = result?.stato
      const pushLogId = result?.push_log_id
      // righe pushate effettive = somma `created` + `updated` di tutti gli
      // handler (di solito 1 per push singolo). Se non disponibile, fallback
      // su righe_pushable diagnostico (count dichiarato pre-push).
      const righe = result?.handlers?.reduce(
        (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
        0,
      ) ?? result?.righe_pushable ?? 0

      if (stato === 'COMPLETATO') {
        notify.success(t('preventivi.push_commessa_ok_dettaglio', { righe, push_log_id: pushLogId }))
      } else if (stato === 'PARZIALE') {
        notify.warn(t('preventivi.push_commessa_parziale', { righe, push_log_id: pushLogId }))
      } else if (stato === 'ERRORE') {
        // Fallback string per evitare frase troncata ("Push fallito: ") quando
        // l'orchestrator ha stato ERRORE ma errors[] di un handler e' vuoto
        // (caso limite: errore aggregato senza dettaglio per riga).
        const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.generic_error')
        notify.error(t('preventivi.push_commessa_errore', { primo_errore: firstError }))
      } else if (stato === 'SKIPPED') {
        notify.warn(t('preventivi.push_commessa_skipped'))
      } else {
        // Fallback: stato sconosciuto, evita silenzio.
        notify.success(t('preventivi.push_commessa_ok'))
      }

      // Hint informativo (non bloccante) per fatturazione immediata: il BE
      // include il flag dalla testata nel payload. Quando arrivera' la PR2
      // (servizio emissione immediata) questo blocco diventera' inutile e
      // potra' essere rimosso.
      if (result?.fatturazione_immediata) {
        // useNotify non espone severity 'info' dedicata: usiamo warn (gialla)
        // come "avviso non bloccante".
        notify.warn(t('preventivi.push_commessa_immediata_hint'))
      }

      await loadIntegrazione()
      // Reload testata padre solo per esiti che possono cambiare stato/capabilities:
      // COMPLETATO -> ACCETTATO->EVASO; PARZIALE -> conteggi righe push_log.
      // SKIPPED/ERRORE: niente cambio dati, nessun reload.
      if (stato === 'COMPLETATO' || stato === 'PARZIALE') {
        emit('push-completato')
      }
    }
  })
}

defineExpose({ loadIntegrazione })
</script>

<template>
  <div class="form-grid">
    <!-- Stato fatturazione -->
    <h4 style="margin: 0;">{{ t('preventivi.section_fatturazione') }}</h4>

    <div v-if="statoFatturazione" style="display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;">
      <div class="form-field" style="flex: 0 0 auto;">
        <label>{{ t('preventivi.fatt_totale_righe') }}</label>
        <span>{{ statoFatturazione.righe_totali ?? '-' }}</span>
      </div>
      <div class="form-field" style="flex: 0 0 auto;">
        <label>{{ t('preventivi.fatt_in_commessa') }}</label>
        <span>{{ statoFatturazione.righe_in_commessa ?? '-' }}</span>
      </div>
      <div class="form-field" style="flex: 0 0 auto;">
        <label>{{ t('preventivi.fatt_fatturate') }}</label>
        <span>{{ statoFatturazione.righe_fatturate ?? '-' }}</span>
      </div>
    </div>
    <div v-else-if="!loadingFatt" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('preventivi.fatt_non_disponibile') }}
    </div>

    <Button v-if="!tutteRighePushate" icon="pi pi-send" :label="t('preventivi.push_commessa')"
      severity="info" size="small" :loading="loading" @click="onPushCommessa"
      style="align-self: flex-start;" />
    <div v-else class="push-commessa-fatto">
      <i class="pi pi-check-circle" />
      <span>{{ t('preventivi.push_commessa_gia_fatto') }}</span>
    </div>

    <!-- Pratiche collegate (opzionale) -->
    <h4 style="margin: 1rem 0 0;">{{ t('preventivi.section_pratiche') }}</h4>
    <p style="margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">
      {{ t('preventivi.pratiche_opzionali') }}
    </p>

    <DataTable v-if="pratiche.length" :value="pratiche" striped-rows size="small"
      class="app-datatable" scrollable scrollHeight="150px" data-key="id">
      <Column field="pratica_codice" :header="t('preventivi.pratica_codice')" style="width: 120px;" />
      <Column field="stato_descrizione" :header="t('preventivi.pratica_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoPraticaSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="tipo_prestazione_descrizione" :header="t('preventivi.pratica_tipo')" style="min-width: 160px;" />
      <Column field="data_apertura" :header="t('preventivi.pratica_data')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_apertura) }}</template>
      </Column>
    </DataTable>
    <div v-else-if="!loadingPratiche" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('preventivi.nessuna_pratica') }}
    </div>
  </div>
</template>

<style scoped>
.push-commessa-fatto {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--p-green-600, var(--text-color));
  font-size: 0.85rem;
  font-style: italic;
  align-self: flex-start;
}
.push-commessa-fatto .pi-check-circle {
  font-size: 1rem;
}
</style>
