<script setup>
// Scopo: Building block riusabile per la valorizzazione dei componenti BoM
//        di un articolo composito (modello unificato 2026-05-13).
//        Costituisce il blocco UI per le 4 sorgenti documento commerciale
//        (preventivi, ordini, contratti, ddt) — la variabilita' tra le
//        sorgenti vive solo in 2 prop:
//          * apiPreview(documentoId, params) -> Promise<axiosResponse>
//          * documentoId (Number)
//
//        Lifecycle:
//         1. Drawer riga apre la Dialog quando l'operatore seleziona un
//            articolo composito (auto-open).
//         2. Mount della Dialog -> chiama apiPreview, popola tabella con
//            prezzi suggeriti + flag obbligatorio + esposto_in_fattura
//            + attivo (obbligatori TRUE, opzionali FALSE per default DB).
//         3. Operatore valorizza prezzi mancanti, attiva opzionali,
//            modifica suggeriti dove ammesso.
//         4. Conferma -> emit('confirm', { overrides, attivazioni, summary }).
//            Annulla -> emit('cancel') senza propagare.
//        Il drawer padre raccoglie il payload e lo include in
//        `componenti_overrides` + `componenti_attivazioni` del Save.
//
//        Form atomic: NO persistenza dei figli finche' la riga padre
//        non viene salvata. Tutto vive nel client.
//
//        NOTA listini bundle: NON usa questo Dialog. La UX listini ha
//        contesto diverso (versione listino, no data documento, no BA,
//        no utility, no delta) — sara' un Dialog separato in Fase G/H.
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { formatCurrency, PRICE_EPSILON } from '../../../core/utils/format'
import { pricingOrigineSeverity, pricingOrigineLabelKey } from '../../../core/utils/severity'
import { useAuthStore } from '../../../stores/auth'
import { PRICING_ACTIONS } from '../../constants'

const { t } = useI18n()
const notify = useNotify()
const auth = useAuthStore()

const props = defineProps({
  // v-model:visible per gestione apertura/chiusura standard PrimeVue
  visible: { type: Boolean, default: false },
  // Articolo composito padre selezionato nel drawer riga
  // Oggetto: { id, codice, descrizione, is_composito }
  articolo: { type: Object, default: null },
  // ID del documento padre (preventivo, ordine, contratto, ddt).
  // Generico — la callback apiPreview riceve questo come primo argomento.
  documentoId: { type: Number, required: true },
  uomOperativaId: { type: Number, default: null },
  quantita: { type: [Number, String], default: 1 },
  // Callback fetch preview iniettata dal caller (sorgente-specific).
  // Firma: (documentoId, {articolo_id, uom_operativa_id, quantita})
  //   -> Promise<axiosResponse con response.data.data = lista componenti>
  // Per preventivi: passare previewRigaComponenti da preventiviApi.
  // Per ordini/contratti/ddt: l'omologa di quella sorgente.
  apiPreview: { type: Function, required: true },
  // Payload corrente (se l'operatore riapre la Dialog dopo conferma)
  // per ripristinare lo stato precedente
  initialPayload: { type: Object, default: null },
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

// ── Stato locale ──────────────────────────────────────────────────

const componenti = ref([])       // lista preview dal BE
const loading = ref(false)
const errore = ref(null)

// Mappa componente_id -> prezzo override (modificato dall'operatore)
// Inizializzato col suggerito al fetch; rimane editabile.
const prezzoOverrides = ref({})

// Mappa componente_id -> attivo (TRUE = incluso nella riga)
// Default: obbligatori TRUE, opzionali FALSE.
const attivazioni = ref({})

const canOverride = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

// ── Fetch preview ─────────────────────────────────────────────────

let _previewToken = 0

async function caricaPreview() {
  if (!props.articolo?.id || !props.uomOperativaId
      || !(Number(props.quantita) > 0)) {
    componenti.value = []
    return
  }
  const tk = ++_previewToken
  loading.value = true
  errore.value = null
  try {
    const res = await props.apiPreview(props.documentoId, {
      articolo_id: props.articolo.id,
      uom_operativa_id: props.uomOperativaId,
      quantita: props.quantita,
    })
    if (tk !== _previewToken) return
    const rows = res.data?.data ?? []
    componenti.value = rows
    initPayloadDaPreview(rows)
  } catch (err) {
    if (tk !== _previewToken) return
    errore.value = extractApiError(err, t('vendite.componenti.errore_caricamento'))
    componenti.value = []
  } finally {
    if (tk === _previewToken) loading.value = false
  }
}

// Inizializza prezzoOverrides + attivazioni dai dati preview.
// Se initialPayload fornito (riapertura) -> ripristina lo stato precedente.
function initPayloadDaPreview(rows) {
  const initOverrides = {}
  const initAttivi = {}
  const restoreOverrides = props.initialPayload?.overrides || {}
  const restoreAttivi = props.initialPayload?.attivazioni || {}
  for (const c of rows) {
    const restored = restoreOverrides[c.componente_id]
    if (restored != null && restored !== '') {
      initOverrides[c.componente_id] = Number(restored)
    } else if (c.prezzo_suggerito != null) {
      initOverrides[c.componente_id] = Number(c.prezzo_suggerito)
    } else {
      initOverrides[c.componente_id] = null  // resolver fail -> operatore deve valorizzare
    }
    // Attivazione: ripristino esplicito > default obbligatorio.
    if (c.componente_id in restoreAttivi) {
      initAttivi[c.componente_id] = !!restoreAttivi[c.componente_id]
    } else {
      // Modello unificato: obbligatori = TRUE, opzionali = FALSE.
      // La fn DB preview espone `obbligatorio` come boolean (no NULL).
      initAttivi[c.componente_id] = c.obbligatorio === true
    }
  }
  prezzoOverrides.value = initOverrides
  attivazioni.value = initAttivi
}

// Watch sui parametri chiave: se cambia articolo/uom/qta mentre la
// Dialog e' aperta -> ricarica preview. In pratica il caller non
// dovrebbe permetterlo (Dialog modale blocca), ma defense.
watch(
  () => [props.visible, props.articolo?.id, props.uomOperativaId, props.quantita],
  ([vis]) => {
    if (vis) caricaPreview()
  },
)

onMounted(() => {
  if (props.visible) caricaPreview()
})

// ── Helper template ───────────────────────────────────────────────

function isObbligatorio(comp) {
  // Modello unificato 2026-05-13: la fn DB preview ritorna sempre
  // boolean non-null. Comparazione stretta `=== true` coerente con
  // `initPayloadDaPreview` (record con obbligatorio=null/undefined
  // sono trattati come opzionali — opzione conservativa: default
  // attivo=FALSE invece di TRUE).
  return comp.obbligatorio === true
}

function isEsposto(comp) {
  return comp.esposto_in_fattura === true
}

function isAttivo(comp) {
  return !!attivazioni.value[comp.componente_id]
}

function setAttivo(componenteId, val) {
  attivazioni.value = { ...attivazioni.value, [componenteId]: !!val }
}

function setPrezzo(componenteId, val) {
  prezzoOverrides.value = { ...prezzoOverrides.value, [componenteId]: val }
}

function getPrezzoCorrente(comp) {
  const o = prezzoOverrides.value[comp.componente_id]
  return o == null ? null : Number(o)
}

function badgeOrigine(origine) {
  if (!origine) return null
  const key = pricingOrigineLabelKey(origine)
  if (!key) return null
  return { key, severity: pricingOrigineSeverity(origine) }
}

// ── Validazione ───────────────────────────────────────────────────

const obbligatoriInvalidi = computed(() => {
  // Obbligatori devono avere prezzo non-null e non zero.
  // Opzionali attivi devono avere prezzo non-null (zero ammesso).
  return componenti.value.filter((c) => {
    if (!isAttivo(c)) return false
    const prezzo = getPrezzoCorrente(c)
    if (prezzo == null) return true  // attivo senza prezzo
    if (isObbligatorio(c) && Number(prezzo) === 0) return true
    return false
  })
})

const canConfirm = computed(() => {
  if (loading.value) return false
  if (errore.value) return false
  if (componenti.value.length === 0) return false
  if (obbligatoriInvalidi.value.length > 0) return false
  return true
})

const summaryTotale = computed(() => {
  let totale = 0
  let nAttivi = 0
  for (const c of componenti.value) {
    if (!isAttivo(c)) continue
    const prezzo = getPrezzoCorrente(c)
    if (prezzo == null) continue
    const qta = Number(c.quantita_componente || 0)
    totale += prezzo * qta
    nAttivi += 1
  }
  // qtaPadre: snapshot della qty padre al confirm, permette al caller di
  // scalare il totale lato suo se la qty cambia post-confirm senza dover
  // riaprire la Dialog (il prezzo unitario del componente non dipende
  // dalla qty padre — solo `quantita_componente = coeff × qty_padre`).
  return {
    n: nAttivi,
    total: totale,
    qtaPadre: Number(props.quantita) || 0,
  }
})

// ── Build payload + emit ──────────────────────────────────────────

// Payload per il drawer padre:
//   overrides: { componente_id: prezzo } -- include SOLO i prezzi
//     modificati rispetto al suggerito (o senza suggerito).
//   attivazioni: { componente_id: bool } -- include SOLO le
//     differenze rispetto al default obbligatorio=TRUE/opzionale=FALSE.
function buildPayload() {
  const overrides = {}
  const attivazioniDelta = {}
  for (const c of componenti.value) {
    const prezzoLocale = getPrezzoCorrente(c)
    const suggerito = c.prezzo_suggerito != null ? Number(c.prezzo_suggerito) : null
    // Overrides: invia solo se prezzo locale != suggerito (o suggerito NULL).
    // PRICE_EPSILON centralizzato in core/utils/format (mezzo step del
    // 6° decimale, coerente con InputNumber max-fraction-digits=6).
    if (prezzoLocale != null) {
      if (suggerito == null || Math.abs(prezzoLocale - suggerito) >= PRICE_EPSILON) {
        overrides[c.componente_id] = String(prezzoLocale)
      }
    }
    // Attivazioni: invia solo se diverso dal default
    const defaultAttivo = isObbligatorio(c)  // obbligatori default TRUE
    const correnteAttivo = isAttivo(c)
    if (correnteAttivo !== defaultAttivo) {
      attivazioniDelta[c.componente_id] = correnteAttivo
    }
  }
  return {
    overrides: Object.keys(overrides).length > 0 ? overrides : null,
    attivazioni: Object.keys(attivazioniDelta).length > 0 ? attivazioniDelta : null,
    summary: summaryTotale.value,  // utile al drawer padre per il riepilogo
  }
}

function handleConfirm() {
  if (!canConfirm.value) {
    notify.warn(t('vendite.componenti.obbligatorio_mancante'))
    return
  }
  emit('confirm', buildPayload())
  emit('update:visible', false)
}

function handleCancel() {
  emit('cancel')
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    @update:visible="(v) => emit('update:visible', v)"
    :header="articolo
      ? t('vendite.componenti.dialog_titolo', {
          codice: articolo.codice || '',
          descrizione: articolo.descrizione || '',
        })
      : ''"
    modal
    :closable="false"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :pt="{ root: { class: 'app-dialog-componenti' } }"
  >
    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
      <small class="text-color-secondary">{{ t('vendite.componenti.dialog_hint') }}</small>

      <div v-if="loading" style="padding: 1rem; text-align: center;">
        <i class="pi pi-spin pi-spinner" style="margin-right: 0.5rem;" />
        {{ t('vendite.componenti.dialog_caricamento') }}
      </div>

      <Message v-else-if="errore" severity="error" :closable="false">
        {{ errore }}
      </Message>

      <Message v-else-if="componenti.length === 0" severity="warn" :closable="false">
        {{ t('vendite.componenti.bom_vuota') }}
      </Message>

      <DataTable
        v-else
        :value="componenti"
        size="small"
        class="app-datatable"
        data-key="componente_id"
        responsive-layout="scroll"
      >
        <Column :header="t('vendite.componenti.col_codice')" style="width: 140px;">
          <template #body="{ data }">
            <div style="display: flex; flex-direction: column; gap: 0.15rem;">
              <strong>{{ data.componente_codice }}</strong>
              <Tag
                v-if="isObbligatorio(data)"
                severity="danger"
                :value="t('vendite.componenti.col_obbligatorio_tag')"
                class="app-tag-xs"
              />
              <Tag
                v-else
                severity="secondary"
                :value="t('vendite.componenti.col_opzionale_tag')"
                class="app-tag-xs"
              />
            </div>
          </template>
        </Column>

        <Column
          field="componente_descrizione"
          :header="t('vendite.componenti.col_descrizione')"
          style="min-width: 200px;"
        />

        <Column :header="t('vendite.componenti.col_qta')" style="width: 90px;">
          <template #body="{ data }">{{ data.quantita_componente }}</template>
        </Column>

        <Column field="uom_codice" :header="t('vendite.componenti.col_uom')" style="width: 70px;" />

        <Column :header="t('vendite.componenti.col_prezzo_suggerito')" style="width: 140px;">
          <template #body="{ data }">
            <span v-if="data.prezzo_suggerito != null">
              {{ formatCurrency(data.prezzo_suggerito) }}
            </span>
            <Tag
              v-else
              severity="warn"
              :value="t('vendite.componenti.preview_listino_mancante')"
              class="app-tag-xs"
            />
          </template>
        </Column>

        <Column :header="t('vendite.componenti.col_prezzo_finale')" style="width: 170px;">
          <template #body="{ data }">
            <InputNumber
              :model-value="prezzoOverrides[data.componente_id]"
              mode="currency"
              currency="EUR"
              locale="it-IT"
              :min-fraction-digits="6"
              :max-fraction-digits="6"
              :disabled="!canOverride && data.prezzo_suggerito != null"
              :class="{
                'p-invalid': isAttivo(data) && (
                  prezzoOverrides[data.componente_id] == null
                  || (isObbligatorio(data) && Number(prezzoOverrides[data.componente_id]) === 0)
                )
              }"
              @update:model-value="(v) => setPrezzo(data.componente_id, v)"
              style="width: 100%;"
            />
          </template>
        </Column>

        <Column :header="t('vendite.componenti.col_origine')" style="width: 130px;">
          <template #body="{ data }">
            <Tag
              v-if="data.origine_prezzo && badgeOrigine(data.origine_prezzo)"
              :severity="badgeOrigine(data.origine_prezzo).severity"
              :value="t(badgeOrigine(data.origine_prezzo).key)"
              class="app-tag-xs"
            />
          </template>
        </Column>

        <Column :header="t('vendite.componenti.col_attivo')" style="width: 90px;">
          <template #body="{ data }">
            <Checkbox
              :model-value="isAttivo(data)"
              binary
              :disabled="isObbligatorio(data)"
              v-tooltip.top="isObbligatorio(data)
                ? t('vendite.componenti.attivo_disabilitato_tooltip')
                : null"
              @update:model-value="(v) => setAttivo(data.componente_id, v)"
            />
          </template>
        </Column>

        <Column :header="t('vendite.componenti.col_esposto')" style="width: 100px;">
          <template #body="{ data }">
            <i
              v-if="isEsposto(data)"
              class="pi pi-eye"
              style="color: var(--app-text-info, var(--primary-color))"
              v-tooltip.top="t('vendite.componenti.esposto_in_fattura_tooltip')"
            />
            <i
              v-else
              class="pi pi-eye-slash"
              style="color: var(--app-text-muted)"
              v-tooltip.top="t('vendite.componenti.esposto_no_tooltip')"
            />
          </template>
        </Column>
      </DataTable>

      <Message
        v-if="!loading && !errore && obbligatoriInvalidi.length > 0"
        severity="warn"
        :closable="false"
      >
        {{ t('vendite.componenti.obbligatorio_mancante') }}
      </Message>

      <div
        v-if="!loading && !errore && componenti.length > 0"
        style="display: flex; justify-content: flex-end; padding-top: 0.5rem; font-size: 0.9rem;"
      >
        <span v-if="summaryTotale.n > 0">
          {{ t('vendite.componenti.summary', {
            n: summaryTotale.n,
            total: formatCurrency(summaryTotale.total),
          }) }}
        </span>
        <span v-else class="text-color-secondary">
          {{ t('vendite.componenti.summary_zero') }}
        </span>
      </div>
    </div>

    <template #footer>
      <Button
        :label="t('vendite.componenti.dialog_annulla')"
        severity="secondary"
        @click="handleCancel"
      />
      <Button
        :label="t('vendite.componenti.dialog_conferma')"
        :disabled="!canConfirm"
        @click="handleConfirm"
      />
    </template>
  </Dialog>
</template>

<style scoped>
.app-tag-xs {
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
}
</style>
