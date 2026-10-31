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
//            prezzi suggeriti + flag obbligatorio + esposizione_in_fattura
//            + attivo (obbligatori TRUE, opzionali FALSE per default DB).
//         3. Operatore valorizza prezzi mancanti, attiva opzionali,
//            modifica suggeriti dove ammesso.
//         4. Conferma -> emit('confirm', { overrides, summary }).
//            Annulla -> emit('cancel') senza propagare.
//        Il drawer padre raccoglie il payload e include `componenti_overrides`
//        nel Save (`componenti_attivazioni` non piu' modificabile: decisione
//        di dominio 2026-05-13 — BoM contratto immutabile per documento).
//
//        Form atomic: NO persistenza dei figli finche' la riga padre
//        non viene salvata. Tutto vive nel client.
//
//        Listini bundle: stesso Dialog parametrizzato (decisione
//        2026-05-13). Le prop `showPrezzoSuggerito=false` e
//        `i18nPrefix='vendite.componenti.bundle'` consentono al caller
//        listino di adattare il Dialog (no colonna prezzo suggerito,
//        no colonna origine, titoli/hint dedicati). I prezzi sono
//        autoritativi (nessun resolver alle spalle), persistenza
//        assoluta lato caller via API listino bundle.
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEsposizioniComponente, severitaEsposizione } from '../../../catalogo/composables/useEsposizioniComponente'
// DataTable grezza: i componenti BoM della riga in composizione, dall'anteprima
// (`apiPreview`) e valorizzati nel client fino al salvataggio del padre — un
// form atomico in un dialog, non paginato e non configurabile.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import Tag from 'primevue/tag'
import AppDialog from '../../../core/components/AppDialog.vue'
import Message from 'primevue/message'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { formatCurrency, PRICE_EPSILON } from '../../../core/utils/format'
import { pricingOrigineSeverity, pricingOrigineLabelKey } from '../../../core/utils/severity'
import { useAuthStore } from '../../../stores/auth'
import { PRICING_ACTIONS } from '../../constants'

import { STATUS_ICONS } from '../../../core/constants'
import { useFotografiaDialog } from '../../../core/composables/useFotografiaDialog'
const { t, te } = useI18n()
// Il modo di esposizione in fattura per esteso, con l'etichetta dal DB.
const { etichetta: etichettaEsposizione } = useEsposizioniComponente()
const notify = useNotify()
const auth = useAuthStore()

const props = defineProps({
  // v-model:visible per gestione apertura/chiusura standard PrimeVue
  visible: { type: Boolean, default: false },
  // Articolo composito padre selezionato nel drawer riga
  // Oggetto: { id, codice, descrizione, is_composito }
  articolo: { type: Object, default: null },
  // ID del documento padre (preventivo, ordine, contratto, ddt) o
  // della versione listino per il caso bundle (modello unificato).
  // Generico — la callback apiPreview riceve questo come primo argomento.
  documentoId: { type: Number, required: true },
  uomOperativaId: { type: Number, default: null },
  quantita: { type: [Number, String], default: 1 },
  // Callback fetch preview iniettata dal caller (sorgente-specific).
  // Firma: (documentoId, {articolo_id, uom_operativa_id, quantita})
  //   -> Promise<axiosResponse con response.data.data = lista componenti>
  // Per preventivi: passare previewRigaComponenti da preventiviApi.
  // Per ordini/contratti/ddt: l'omologa di quella sorgente.
  // Per listino bundle: API che ritorna BoM + prezzi già definiti.
  // FE-D1/D2 (brief-ddt-righe-senza-prezzo): il documento pretende un prezzo
  // sui componenti? Il DDT in conto visione no — il kit viaggia senza prezzi.
  // ⭐ `default: true` NON e' pigrizia: preventivi, ordini, contratti e listino
  // bundle non passano la prop e restano identici bit per bit. E' la stessa
  // scelta fatta dal team DB sul trigger C3 — non si tocca il codice condiviso,
  // si cambia solo quando la regola si applica.
  prezzoRichiesto: { type: Boolean, default: true },
  apiPreview: { type: Function, required: true },
  // Payload corrente (se l'operatore riapre la Dialog dopo conferma)
  // per ripristinare lo stato precedente
  initialPayload: { type: Object, default: null },
  // Mostra colonna "Prezzo suggerito" (default true). False per i caller
  // che non hanno un resolver pricing alle spalle (es. listino bundle:
  // l'admin definisce il prezzo, non c'e' suggerimento da pre-popolare).
  showPrezzoSuggerito: { type: Boolean, default: true },
  // Namespace i18n del Dialog (default `vendite.componenti`). Override
  // per varianti contestuali: per il listino bundle viene passato
  // `vendite.componenti.bundle`. Le chiavi non definite nel namespace
  // override fanno fallback automatico al namespace base (vedi
  // `localizedKey` sotto).
  i18nPrefix: { type: String, default: 'vendite.componenti' },
  // Modalita' emissione overrides nel payload di confirm:
  //   - false (default, preventivi/ordini/contratti/ddt): SOLO i prezzi
  //     diversi dal `prezzo_suggerito` (resolver listino). Semantica delta.
  //   - true (listino bundle): TUTTI i prezzi non-null, anche invariati.
  //     Necessario perche' il caller BE fa tabula rasa idempotente
  //     (soft-delete + re-insert): senza tutti i prezzi, il composito si
  //     svuoterebbe ad ogni re-conferma senza modifiche.
  emitAllPrices: { type: Boolean, default: false },
})

// Helper risoluzione i18n con fallback al namespace base. Permette di
// definire `vendite.componenti.bundle.*` solo per le chiavi che
// differiscono (titolo, hint, conferma, prezzo_finale, summary).
// Le chiavi comuni (col_codice, col_qta, col_esposto, ecc.) restano
// solo in `vendite.componenti.*` e cadono qui per fallback automatico.
function localizedKey(key) {
  const prefixed = `${props.i18nPrefix}.${key}`
  return te(prefixed) ? prefixed : `vendite.componenti.${key}`
}

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

// ── Stato locale ──────────────────────────────────────────────────

const componenti = ref([])       // lista preview dal BE
const loading = ref(false)
const errore = ref(null)

// Mappa componente_id -> prezzo override (modificato dall'operatore)
// Inizializzato col suggerito al fetch; rimane editabile.
// Decisione di dominio 2026-05-13: la BoM e' contratto immutabile per
// documento — l'operatore non sceglie la composizione, solo i prezzi
// override (con gating L1). Nessun toggle attivo/inattivo qui.
const prezzoOverrides = ref({})

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
    errore.value = extractApiError(err, t(localizedKey('errore_caricamento')))
    componenti.value = []
  } finally {
    if (tk === _previewToken) loading.value = false
  }
}

// Inizializza prezzoOverrides dai dati preview.
// Se initialPayload fornito (riapertura) -> ripristina lo stato precedente.
function initPayloadDaPreview(rows) {
  const initOverrides = {}
  const restoreOverrides = props.initialPayload?.overrides || {}
  for (const c of rows) {
    const restored = restoreOverrides[c.componente_id]
    if (restored != null && restored !== '') {
      initOverrides[c.componente_id] = Number(restored)
    } else if (c.prezzo_suggerito != null) {
      initOverrides[c.componente_id] = Number(c.prezzo_suggerito)
    } else {
      initOverrides[c.componente_id] = null  // resolver fail -> operatore deve valorizzare
    }
  }
  prezzoOverrides.value = initOverrides
  fotografia.fissa()
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
  // Tutti i componenti BoM finiscono nella riga (decisione di dominio
  // 2026-05-13: BoM contratto immutabile). Verifica:
  //   - obbligatori: prezzo non-null e non zero
  //   - opzionali: prezzo non-null (zero ammesso)
  return componenti.value.filter((c) => {
    const prezzo = getPrezzoCorrente(c)
    // FE-D1: con `prezzoRichiesto = false` il prezzo assente NON e' un difetto
    // — e' l'esito normale di un documento che non vende. Lo zero invece resta
    // invalido sugli obbligatori anche li': zero e' un prezzo che qualcuno ha
    // scritto, e su una riga obbligatoria e' quasi sempre uno sbaglio.
    if (prezzo == null) return props.prezzoRichiesto
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
  // Tutti i componenti BoM partecipano al totale (decisione di dominio
  // 2026-05-13: BoM contratto immutabile per documento).
  let totale = 0
  let nComponenti = 0
  for (const c of componenti.value) {
    const prezzo = getPrezzoCorrente(c)
    if (prezzo == null) continue
    const qta = Number(c.quantita_componente || 0)
    totale += prezzo * qta
    nComponenti += 1
  }
  // qtaPadre: snapshot della qty padre al confirm, permette al caller di
  // scalare il totale lato suo se la qty cambia post-confirm senza dover
  // riaprire la Dialog (il prezzo unitario del componente non dipende
  // dalla qty padre — solo `quantita_componente = coeff × qty_padre`).
  return {
    n: nComponenti,
    total: totale,
    qtaPadre: Number(props.quantita) || 0,
  }
})

// ── Build payload + emit ──────────────────────────────────────────

// Payload per il drawer padre:
//   overrides: { componente_id: prezzo } -- include SOLO i prezzi
//     modificati rispetto al suggerito (o senza suggerito).
// La selezione attivo/inattivo non e' piu' modificabile dall'operatore
// (BoM contratto immutabile, decisione di dominio 2026-05-13): il
// payload non include `componenti_attivazioni`.
function buildPayload() {
  const overrides = {}
  for (const c of componenti.value) {
    const prezzoLocale = getPrezzoCorrente(c)
    if (prezzoLocale == null) continue
    if (props.emitAllPrices) {
      // Caller fa tabula rasa idempotente lato BE (es. listino bundle):
      // serve sempre l'elenco completo dei prezzi non-null, anche invariati.
      overrides[c.componente_id] = String(prezzoLocale)
      continue
    }
    // Semantica delta (preventivi/ordini/contratti/ddt): invia solo se
    // diverso dal `prezzo_suggerito`. PRICE_EPSILON centralizzato in
    // core/utils/format (mezzo step del 6° decimale, coerente con
    // InputNumber max-fraction-digits=6).
    const suggerito = c.prezzo_suggerito != null ? Number(c.prezzo_suggerito) : null
    if (suggerito == null || Math.abs(prezzoLocale - suggerito) >= PRICE_EPSILON) {
      overrides[c.componente_id] = String(prezzoLocale)
    }
  }
  return {
    overrides: Object.keys(overrides).length > 0 ? overrides : null,
    summary: summaryTotale.value,  // utile al drawer padre per il riepilogo
  }
}

function handleConfirm() {
  if (!canConfirm.value) {
    notify.warn(t(localizedKey('obbligatorio_mancante')))
    return
  }
  emit('confirm', buildPayload())
  emit('update:visible', false)
}

function handleCancel() {
  emit('cancel')
  emit('update:visible', false)
}

// D-14 (rilievo di Tid): i prezzi dei componenti sono lavoro dell'operatore; la fotografia si fissa a preview caricata, sui prezzi suggeriti o ripristinati.
const fotografia = useFotografiaDialog(() => ({ prezzi: prezzoOverrides.value }), { visibile: () => props.visible, fissaAllApertura: false })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="props.visible"
    @update:visible="(v) => emit('update:visible', v)"
    :header="articolo
      ? t(localizedKey('dialog_titolo'), {
          codice: articolo.codice || '',
          descrizione: articolo.descrizione || '',
        })
      : ''"
    width="xl"
    :save-disabled="!canConfirm"
    @save="handleConfirm"
    @cancel="handleCancel"
  >
    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
      <small class="app-text-muted">{{ t(localizedKey('dialog_hint')) }}</small>

      <div v-if="loading" style="padding: 1rem; text-align: center;">
        <i :class="STATUS_ICONS.CARICAMENTO" style="margin-right: 0.5rem;" />
        {{ t(localizedKey('dialog_caricamento')) }}
      </div>

      <Message v-else-if="errore" severity="error" :closable="false">
        {{ errore }}
      </Message>

      <Message v-else-if="componenti.length === 0" severity="warn" :closable="false">
        {{ t(localizedKey('bom_vuota')) }}
      </Message>

      <DataTable
        v-else
        :value="componenti"
        size="small"
        class="app-datatable"
        data-key="componente_id"
        responsive-layout="scroll"
      >
        <Column :header="t(localizedKey('col_codice'))" style="width: 140px;">
          <template #body="{ data }">
            <div style="display: flex; flex-direction: column; gap: 0.15rem;">
              <strong>{{ data.componente_codice }}</strong>
              <Tag
                v-if="isObbligatorio(data)"
                severity="danger"
                :value="t(localizedKey('col_obbligatorio_tag'))"
                class="app-tag-xs"
              />
              <Tag
                v-else
                severity="secondary"
                :value="t(localizedKey('col_opzionale_tag'))"
                class="app-tag-xs"
              />
            </div>
          </template>
        </Column>

        <Column
          field="componente_descrizione"
          :header="t(localizedKey('col_descrizione'))"
          style="min-width: 200px;"
        />

        <Column :header="t(localizedKey('col_qta'))" style="width: 90px;">
          <template #body="{ data }">{{ data.quantita_componente }}</template>
        </Column>

        <Column field="uom_codice" :header="t(localizedKey('col_uom'))" style="width: 70px;" />

        <Column v-if="showPrezzoSuggerito" :header="t(localizedKey('col_prezzo_suggerito'))" style="width: 140px;">
          <template #body="{ data }">
            <span v-if="data.prezzo_suggerito != null">
              {{ formatCurrency(data.prezzo_suggerito) }}
            </span>
            <Tag
              v-else
              severity="warn"
              :value="t(localizedKey('preview_listino_mancante'))"
              class="app-tag-xs"
            />
          </template>
        </Column>

        <Column :header="t(localizedKey('col_prezzo_finale'))" style="width: 170px; min-width: 170px;">
          <template #body="{ data }">
            <InputNumber
              :model-value="prezzoOverrides[data.componente_id]"
              mode="currency"
              currency="EUR"
              locale="it-IT"
              :min-fraction-digits="2"
              :max-fraction-digits="6"
              :disabled="!canOverride && data.prezzo_suggerito != null"
              :class="{
                'p-invalid': prezzoOverrides[data.componente_id] == null
                  || (isObbligatorio(data) && Number(prezzoOverrides[data.componente_id]) === 0)
              }"
              @update:model-value="(v) => setPrezzo(data.componente_id, v)"
              :input-style="{ width: '100%' }"
              style="width: 150px;"
            />
          </template>
        </Column>

        <Column v-if="showPrezzoSuggerito" :header="t(localizedKey('col_origine'))" style="width: 100px;">
          <template #body="{ data }">
            <Tag
              v-if="data.origine_prezzo && badgeOrigine(data.origine_prezzo)"
              :severity="badgeOrigine(data.origine_prezzo).severity"
              :value="t(badgeOrigine(data.origine_prezzo).key)"
              class="app-tag-xs"
            />
          </template>
        </Column>

        <Column :header="t(localizedKey('col_esposto'))" style="width: 150px;">
          <!-- Il modo per esteso (NASCOSTO / DESCRITTIVO / VALORIZZATO), con
               l'etichetta che il DB dichiara: dal 2026-10-01 non e' piu' un si'/no. -->
          <template #body="{ data }">
            <Tag
              :severity="severitaEsposizione(data.esposizione_in_fattura)"
              :value="etichettaEsposizione(data.esposizione_in_fattura)"
              class="app-tag-xs"
            />
          </template>
        </Column>
      </DataTable>

      <Message
        v-if="!loading && !errore && obbligatoriInvalidi.length > 0"
        severity="warn"
        :closable="false"
      >
        {{ t(localizedKey('obbligatorio_mancante')) }}
      </Message>

      <div
        v-if="!loading && !errore && componenti.length > 0"
        style="display: flex; justify-content: flex-end; padding-top: 0.5rem; font-size: 0.9rem;"
      >
        <span v-if="summaryTotale.n > 0">
          {{ t(localizedKey('summary'), {
            n: summaryTotale.n,
            total: formatCurrency(summaryTotale.total),
          }) }}
        </span>
        <span v-else class="app-text-muted">
          {{ t(localizedKey('summary_zero')) }}
        </span>
      </div>
    </div>
  </AppDialog>
</template>

<style scoped>
.app-tag-xs {
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
}
</style>
