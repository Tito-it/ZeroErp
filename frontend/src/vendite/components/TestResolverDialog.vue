<script setup>
// Scopo: Dialog diagnostico resolver pricing v5 (POST /vendite/pricing/resolve/).
//        Esegue risoluzione 3 stadi PROMO → CONTRATTO → CATEGORIA/LISTINO e
//        mostra il prezzo finale con l'origine del match.
//        Nessun side effect: pura lettura deterministica.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import { useArticoloUomOptions } from '../../catalogo/composables/useArticoloUomOptions'
import { extractApiError } from '../../core/utils/apiError'
import { resolvePrezzoV5, diagnoseConfigurazionePricing } from '../api/listini'
import { pricingOrigineSeverity } from '../../core/utils/severity'
import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { DATE_FORMAT, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { toDateString, oggiAziendale } from '../../core/utils/date'

const { t } = useI18n()
const { loading, campiErrati } = useApiHandler()

// Stesso default usato dal drawer nuovo listino: il parametro DEFAULT_UTILITY
// salva codice_interno e viene risolto a id tramite lookup utilities-per-emittente.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])

const form = ref({
  articolo_obj: null,
  uom_id: null,
  data_riferimento: oggiAziendale(),
  ba_obj: null,
  utility_id: null,
  classe_utenza_id: null,
  // Opzionale: UUID articolo padre composito per attivare lo STADIO BUNDLE
  // del resolver (modello unificato BoM 2026-05-13). Quando valorizzato, il
  // resolver cerca prima il prezzo bundle in listini_righe_componenti per
  // la coppia (padre, figlio); fallback su standalone se non trovato.
  articolo_padre_obj: null,
})
const result = ref(null)
const errorMsg = ref(null)
// Diagnostica configurazione asset (popolata dopo errore resolver oppure
// on-demand quando l'admin vuole vedere il path applicato anche in successo).
const diagnose = ref(null)
const diagnoseLoading = ref(false)

// Scopo: la spia di uno stadio della diagnosi, in un punto per i tre stadi.
// ⛔ Il «non applicabile» e' neutro, non rosso: lo stadio non si pone per quel
//    contesto, non e' fallito (`STATUS_ICONS.NON_APPLICABILE`).
function spiaStadio(applicabile) {
  return {
    class: applicabile ? STATUS_ICONS.OK : STATUS_ICONS.NON_APPLICABILE,
    style: `color: var(${applicabile ? '--app-success-color' : '--app-text-muted'}); margin-right: 0.4rem;`,
  }
}

const utilityLockedByBa = computed(() => !!form.value.ba_obj?.utility_id)

// UoM operative dell'articolo selezionato. Composable centralizzato
// (`useArticoloUomOptions`) — usa l'endpoint cross-dominio
// `/catalogo/articoli/<id>/uom/lookup/` (skip_area_check) cosi' anche operatori
// solo-vendite (Senior pricing) possono usare il resolver di test senza dover
// avere LETTURA su catalogo.
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId,
} = useArticoloUomOptions()

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('vendite.listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

// Wrapper thin: il composable e' fetch puro; qui applichiamo l'autopick
// base se il caller non ha gia' un valore (criterio specifico del dialog).
async function loadUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (!form.value.uom_id) {
    form.value.uom_id = pickBaseUomId(list)
  }
}

async function applyDefaultUtility({ force = false } = {}) {
  await loadUtilityDefault()
  if (utilityLockedByBa.value) return
  if (force || !form.value.utility_id) {
    form.value.utility_id = utilityDefaultId.value
  }
}

watch(
  () => form.value.articolo_obj?.id,
  (newId, oldId) => {
    if (newId === oldId) return
    form.value.uom_id = null
    loadUomConPickBase(newId)
  },
)

// Il BA determina univocamente la utility (FK unique su (istanza, utility)).
// Quando l'utente seleziona/cambia BA, allineiamo form.utility_id al valore
// del BA per evitare test incoerenti (BA di una utility + utility diversa
// passata al resolver). Se il BA viene svuotato, la utility resta libera
// (eventualmente selezionabile a mano).
watch(
  () => form.value.ba_obj,
  async (newBa, oldBa) => {
    if (newBa?.utility_id) {
      form.value.utility_id = newBa.utility_id
    } else if (newBa?.id || oldBa?.id) {
      await applyDefaultUtility({ force: true })
    }
  },
)

// Pulizia stato al close del dialog.
watch(
  () => props.visible,
  async (v) => {
    if (!v) {
      result.value = null
      errorMsg.value = null
      diagnose.value = null
      return
    }
    await applyDefaultUtility()
  },
)

const canTest = computed(() => (
  !!form.value.articolo_obj?.id
  && !!form.value.uom_id
  && !!form.value.ba_obj?.id
  && !!form.value.utility_id
  && !!form.value.data_riferimento
))

async function doTest() {
  result.value = null
  errorMsg.value = null
  diagnose.value = null
  const payload = {
    articolo_id: form.value.articolo_obj.id,
    uom_id: form.value.uom_id,
    ba_id: form.value.ba_obj.id,
    utility_id: form.value.utility_id,
    data_riferimento: toDateString(form.value.data_riferimento),
  }
  if (form.value.classe_utenza_id) {
    payload.classe_utenza_id = form.value.classe_utenza_id
  }
  if (form.value.articolo_padre_obj?.id) {
    payload.articolo_padre_contesto = form.value.articolo_padre_obj.id
  }
  try {
    const apiRes = await resolvePrezzoV5(payload)
    result.value = apiRes.data.data
  } catch (err) {
    errorMsg.value = extractApiError(err) || t('vendite.listini.resolver_errore')
    // Su errore resolver, lancia anche la diagnostica per spiegare all'admin
    // cosa manca nella configurazione e quali azioni intraprendere. Best-effort:
    // se anche il diagnose fallisce, mostriamo solo l'errore originale.
    await runDiagnose(payload)
  }
}

// Scopo: chiama l'endpoint diagnose con lo stesso payload del resolver.
//        Best-effort: errori silenziosi (loggati a console). Il caller
//        consuma `diagnose.value` per renderizzare la checklist a stadi.
async function runDiagnose(payload) {
  diagnoseLoading.value = true
  diagnose.value = null
  try {
    const res = await diagnoseConfigurazionePricing(payload)
    diagnose.value = res?.data?.data || null
  } catch {
    // Niente toast: il dialog mostra gia' l'errore del resolver.
  } finally {
    diagnoseLoading.value = false
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <!-- conferma-uscita: nessuna — strumento di prova del prezzo: i campi sono parametri di interrogazione, non si salva niente (D-14) -->
  <AppDialog :visible="visible" @update:visible="v => emit('update:visible', v)"
    :header="t('vendite.listini.test_prezzo')" width="lg" close-only @cancel="close">

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.listini.field_articolo') }} *</label>
        <ArticoloLookup v-model="form.articolo_obj" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_uom') }} *</label>
        <Select
          v-model="form.uom_id"
          :options="uomOptions"
          :option-label="uomLabel"
          option-value="uom_id"
          :loading="uomLoading"
          :placeholder="!form.articolo_obj?.id
            ? t('vendite.promo_articoli.field_uom_articolo_first')
            : t('catalogo.select_uom')"
          :disabled="!form.articolo_obj?.id"
          :invalid="campiErrati.includes('uom_id')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_ba') }} *</label>
        <BillingAccountLookup v-model="form.ba_obj" :placeholder="t('vendite.listini.select_ba')" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_utility') }} *</label>
        <UtilityPerRuoloSelect
          v-model="form.utility_id"
          :placeholder="t('vendite.listini.filtro_utility')"
          :disabled="utilityLockedByBa"
          apply-default
        />
        <small v-if="utilityLockedByBa" class="app-text-muted">
          {{ t('vendite.listini.field_utility_derived_from_ba') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_classe_utenza') }}</label>
        <LookupSelect
          v-model="form.classe_utenza_id"
          rel="config.classi_utenze"
          :placeholder="t('vendite.listini.field_classe_utenza_placeholder')"
          show-clear
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.listini.field_data_riferimento') }} *</label>
        <DatePicker v-model="form.data_riferimento" :dateFormat="DATE_FORMAT" showIcon showButtonBar
          :invalid="campiErrati.includes('data_riferimento')"
        />
      </div>
      <div class="form-field form-field-wide">
        <label>{{ t('vendite.listini.field_articolo_padre_contesto') }}</label>
        <ArticoloLookup
          v-model="form.articolo_padre_obj"
          :filtri="{ compositi: 'solo' }"
        />
        <small class="app-text-muted">
          {{ t('vendite.listini.field_articolo_padre_contesto_hint') }}
        </small>
      </div>
    </div>

    <div style="display: flex; justify-content: center; margin: 1rem 0;">
      <Button :label="t('vendite.listini.esegui_test')" :icon="MANAGE_ICONS.TEST_PREZZO" @click="doTest"
        :loading="loading" :disabled="!canTest" />
    </div>

    <div v-if="result" style="padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.listini.resolver_prezzo_finale') }}</label>
          <strong style="font-size: 1.4rem;">{{ result.prezzo_finale }}</strong>
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.resolver_origine') }}</label>
          <Tag :value="result.origine" :severity="pricingOrigineSeverity(result.origine)" />
        </div>
        <div class="form-field" v-if="result.prezzo_base_snapshot != null">
          <label>{{ t('vendite.listini.resolver_prezzo_base') }}</label>
          <span>{{ result.prezzo_base_snapshot }}</span>
        </div>
        <div class="form-field" v-if="result.tipo_variazione_applicata">
          <label>{{ t('vendite.listini.resolver_variazione') }}</label>
          <span>
            {{ result.tipo_variazione_applicata }}
            <strong v-if="result.valore_variazione_applicata != null">
              {{ result.valore_variazione_applicata }}
            </strong>
          </span>
        </div>
        <div class="form-field" v-if="result.listino_id">
          <label>{{ t('vendite.listini.resolver_listino') }}</label>
          <span>
            <strong v-if="result.listino_codice">{{ result.listino_codice }}</strong>
            <span v-if="result.listino_descrizione"> — {{ result.listino_descrizione }}</span>
            <span v-if="result.listino_versione_codice">
              · v.{{ result.listino_versione_codice }}
            </span>
          </span>
        </div>
        <div class="form-field" v-if="result.contratto_id">
          <label>{{ t('vendite.listini.resolver_contratto') }}</label>
          <span>
            <strong v-if="result.contratto_numero">{{ result.contratto_numero }}</strong>
          </span>
        </div>
        <div class="form-field" v-if="result.promo_id">
          <label>{{ t('vendite.listini.resolver_promo') }}</label>
          <span>
            <strong v-if="result.promo_codice">{{ result.promo_codice }}</strong>
            <span v-if="result.promo_descrizione"> — {{ result.promo_descrizione }}</span>
          </span>
        </div>
        <div class="form-field" v-if="result.categoria_cliente_id_snapshot">
          <label>{{ t('vendite.listini.resolver_categoria') }}</label>
          <span>
            <strong v-if="result.categoria_cliente_codice">{{ result.categoria_cliente_codice }}</strong>
            <span v-if="result.categoria_cliente_descrizione"> — {{ result.categoria_cliente_descrizione }}</span>
          </span>
        </div>
        <div class="form-field" v-if="result.classe_utenza_id_snapshot">
          <label>{{ t('vendite.listini.resolver_classe_utenza') }}</label>
          <span>
            <strong v-if="result.classe_utenza_descrizione">{{ result.classe_utenza_descrizione }}</strong>
          </span>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="app-field-error" style="padding: 0.75rem; text-align: center;">
      {{ errorMsg }}
    </div>

    <!-- Checklist diagnostica: appare quando il resolver ha sollevato errore.
         Mostra stato dei 3 stadi (PROMO/CONTRATTO/CATEGORIA) con icone ✓/✗
         e azioni operative suggerite per sbloccare la configurazione. -->
    <div v-if="diagnose" style="padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px; margin-top: 0.5rem;">
      <h4 style="margin: 0 0 0.5rem 0;">{{ t('vendite.listini.diagnose_titolo') }}</h4>

      <!-- BA + categoria (radice) -->
      <div class="form-field" style="margin-bottom: 0.5rem;">
        <i :class="STATUS_ICONS.OK" style="color: var(--app-success-color); margin-right: 0.4rem;"></i>
        <strong>{{ t('vendite.listini.diagnose_ba') }}</strong>:
        <span v-if="diagnose.ba.categoria_codice">
          {{ t('vendite.listini.diagnose_categoria') }}
          <strong>{{ diagnose.ba.categoria_codice }}</strong>
          <span v-if="diagnose.ba.categoria_descrizione"> — {{ diagnose.ba.categoria_descrizione }}</span>
          <Tag v-if="diagnose.ba.categoria_partecipa_promo" severity="info" :value="t('vendite.listini.diagnose_partecipa_promo')" style="margin-left: 0.4rem;" />
        </span>
        <span v-else class="app-text-muted">{{ t('vendite.listini.diagnose_no_categoria') }}</span>
      </div>

      <!-- Stadio 0 PROMO -->
      <div class="form-field" style="margin-bottom: 0.5rem;">
        <i v-bind="spiaStadio(diagnose.stadio_0_promo.applicabile)"></i>
        <strong>{{ t('vendite.listini.diagnose_stadio_0') }}</strong>
        <span v-if="diagnose.stadio_0_promo.applicabile">
          — <strong>{{ diagnose.stadio_0_promo.promo_codice }}</strong>
          <span v-if="diagnose.stadio_0_promo.promo_descrizione"> — {{ diagnose.stadio_0_promo.promo_descrizione }}</span>
        </span>
        <small v-else class="app-text-muted"> — {{ diagnose.stadio_0_promo.motivo }}</small>
      </div>

      <!-- Stadio 1 CONTRATTO -->
      <div class="form-field" style="margin-bottom: 0.5rem;">
        <i v-bind="spiaStadio(diagnose.stadio_1_contratto.applicabile)"></i>
        <strong>{{ t('vendite.listini.diagnose_stadio_1') }}</strong>
        <span v-if="diagnose.stadio_1_contratto.contratto_attivo">
          — <strong>{{ diagnose.stadio_1_contratto.contratto_numero }}</strong>
          <Tag :value="`${t('vendite.listini.diagnose_modalita')}: ${diagnose.stadio_1_contratto.modalita_pricing}`"
            severity="info" style="margin-left: 0.4rem;" />
        </span>
        <small v-if="diagnose.stadio_1_contratto.motivo" class="app-text-muted">
          — {{ diagnose.stadio_1_contratto.motivo }}
        </small>
      </div>

      <!-- Stadio 2 CATEGORIA → MATRICE -->
      <div class="form-field" style="margin-bottom: 0.5rem;">
        <i v-bind="spiaStadio(diagnose.stadio_2_categoria.applicabile)"></i>
        <strong>{{ t('vendite.listini.diagnose_stadio_2') }}</strong>
        <span v-if="diagnose.stadio_2_categoria.applicabile">
          — <strong>{{ diagnose.stadio_2_categoria.matrice_listino_codice }}</strong>
          <span v-if="diagnose.stadio_2_categoria.matrice_listino_descrizione">
            — {{ diagnose.stadio_2_categoria.matrice_listino_descrizione }}
          </span>
          <Tag v-if="diagnose.stadio_2_categoria.classe_match === 'FALLBACK_NULL'"
            severity="warn" :value="t('vendite.listini.diagnose_fallback_classe')" style="margin-left: 0.4rem;" />
        </span>
        <small v-else class="app-text-muted"> — {{ diagnose.stadio_2_categoria.motivo }}</small>
      </div>

      <!-- Azioni suggerite (lista ordinata) -->
      <div v-if="diagnose.azioni_suggerite && diagnose.azioni_suggerite.length"
        style="margin-top: 0.75rem; padding: 0.5rem; background: var(--app-content-bg); border-radius: 4px;">
        <strong>{{ t('vendite.listini.diagnose_azioni') }}</strong>
        <ul style="margin: 0.25rem 0 0 1.25rem; padding: 0;">
          <li v-for="(azione, idx) in diagnose.azioni_suggerite" :key="idx" style="margin-bottom: 0.25rem;">
            {{ azione }}
          </li>
        </ul>
      </div>
    </div>
  </AppDialog>
</template>
