<script setup>
// Scopo: Drawer creazione/modifica anagrafica emittente fiscale (admin only).
// Solo Dati fiscali base + Soggetto (resolver in crea, banner in modifica).
// Billing Account e Utilities sono drawer dedicati separati (vedi
// EmittenteFiscaleBillingAccountDrawer / EmittenteFiscaleUtilitiesDrawer),
// richiamati dai pulsanti azione della lista.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, TIPO_RUOLO, MANAGE_ICONS, FIELD_LENGTH } from '../../core/constants'
import { getEmittenteFormDefaults } from '../api/amministrazione'
import { paramBool, paramNumber, paramString } from '../../core/utils/parameterCast'
import { blockNonAlphanumeric, normalizeUpperNoSpaces } from '../../core/utils/string'
import { displayTimestamp } from '../../core/utils/date'
import SoggettoResolver from '../../anagrafiche/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import EmittenteRoundingModeSelect from './EmittenteRoundingModeSelect.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import Button from 'primevue/button'



// Valori del campo rounding_policy: 4 codici (UP/DOWN/HALF_UP/HALF_DOWN)
// allineati al CHECK chk_emittenti_fiscali_rounding_policy. Single source of
// truth lato BE; il FE consuma via EmittenteRoundingModeSelect (Fase 3 — A6).

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  emittenteId: { type: Number, default: null }
})


const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Dati dettaglio caricato dal backend (sostituisce store.currentEmittente per evitare
// race condition tra drawer aperti consecutivamente).
const detail = ref(null)

// Titolo drawer: in modifica mostra "Modifica EF — <ragione sociale>".
// Il codice tecnico e' visibile dentro al form (campo Codice), nel titolo
// usiamo solo la ragione sociale per leggibilita'.
const drawerTitle = computed(() => {
  if (!isEdit.value) return t('amministrazione.emittenti_fiscali.create_title')
  const base = t('amministrazione.emittenti_fiscali.edit_title')
  const rs = detail.value?.ragione_sociale_completa
  return rs ? `${base} — ${rs}` : base
})

// Resolver soggetto (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Stato form neutro. I valori dei campi fiscali (`bollo_auto`, `bollo_soglia`,
// `rounding_policy`) vengono popolati via `applyFormDefaults()` da
// `config.parameters` con cascata user->group->default (Fase 3 — A5).
// Il campo `attivo` ha sempre `true` lato FE: la colonna DB ha gia' DEFAULT
// true, non passa per parameters (vedi note brief DB 2026-04-29).
// `descrizione` non fa piu' parte del form dal 2026-08-02: la colonna e' stata
// droppata (`20260802-22`) e la denominazione dell'emittente e' la ragione
// sociale del SOGGETTO selezionato sopra — si cambia di la', non qui.
// Vedi `brief-emittente-ragione-sociale-dal-soggetto.md`.
function defaultForm() {
  return {
    codice: '',
    attivo: true,
    // Codice del catalogo `config.regimi_fiscali` (FK). In creazione si
    // SCEGLIE: nessun precompilato, perche' il default RF01 del DB vale per
    // chi non dichiara il regime — e un emittente che nasce cosi' finisce nel
    // presidio dei regimi da confermare.
    regime_fiscale_rf: null,
    bollo_auto: false,
    bollo_soglia: null,
    rounding_policy: null,
    // valuta_id: livello 3 della catena resolve_valuta_default (vedi
    // backend/apps/anagrafiche/services/valuta_resolver.py). Se non
    // valorizzata, i form-defaults preventivi/contratti senza BA partono
    // con valuta vuota.
    valuta_id: null
  }
}

const form = ref(defaultForm())

// ⭐ LA CONFERMA DEL REGIME FISCALE (R-2 di brief-db-esigibilita-iva-per-cassa-
//    emittente, §10). Mandare `regime_fiscale_rf` al backend E' dichiararlo:
//    il database deriva la conferma (data e autore) da ogni scrittura che
//    nomina il regime, anche con lo stesso valore. Per
//    questo il regime viaggia SOLO quando l'operatore lo ha cambiato, o ha
//    confermato quello che c'e' (`confermaRegime`): un salvataggio che tocca
//    il bollo non deve confermare un regime che nessuno ha guardato.
const confermaRegime = ref(false)
const regimeConfermato = computed(() => !!detail.value?.regime_fiscale_confermato_il)
// La voce del regime dell'emittente come la conosce il dettaglio: la combo
// propone i soli regimi ATTIVI, e uno disattivato dopo che l'emittente l'ha
// preso resta suo (Tid, 2026-10-01) — senza questa voce il campo apparirebbe
// vuoto. Stessi campi dell'elenco del lookup.
const voceRegimeCorrente = computed(() => {
  const d = detail.value
  if (!d?.regime_fiscale_rf) return null
  return {
    codice_interno: d.regime_fiscale_rf,
    codice: d.regime_fiscale_rf,
    descrizione: d.regime_fiscale_descrizione,
  }
})
const regimeCambiato = computed(() =>
  isEdit.value && form.value.regime_fiscale_rf !== (detail.value?.regime_fiscale_rf ?? null))
const regimeDaDichiarare = computed(() =>
  isEdit.value ? (regimeCambiato.value || confermaRegime.value) : !!form.value.regime_fiscale_rf)

// Modifiche non salvate: fotografia all'apertura (anche in creazione), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve). In
// creazione il soggetto scelto sta fuori dal form: il confronto ne raccoglie l'id.
// La conferma del regime e' una modifica: senza, «Conferma» e poi chiudere
// non chiederebbe niente.
const formSalvato = computed(() => ({
  ...form.value,
  soggetto_id: soggettoSelezionato.value?.id ?? null,
  conferma_regime: confermaRegime.value,
}))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSalvato, { visibile: () => props.visible })

// Carica defaults da BE (cast tipi gia' applicato lato server) e li applica
// al form. Best-effort: errori di rete non bloccano il form (l'utente compila
// manualmente). Chiamata solo in modalita' `create` (in `edit` il populate
// arriva dal detail dell'emittente esistente).
//
// Cast defensive via parameterCast.js (pattern catalogo Fase 1):
// se il BE in futuro cambiasse la serializzazione (es. bool come stringa, Decimal
// non parsabile), gli helper proteggono il form da NaN/leak di stringhe sporche.
//
// Race cancellation: se l'utente chiude e riapre il drawer in edit prima che la
// fetch completi, la mutazione post-await si applicherebbe a un'istanza in edit,
// sovrascrivendo i valori del detail. Il guard `!props.visible || isEdit.value`
// blocca l'update se il contesto non e' piu' "create con drawer aperto".
async function applyFormDefaults() {
  try {
    const res = await getEmittenteFormDefaults()
    if (!props.visible || isEdit.value) return  // race guard
    const d = res?.data?.data?.defaults || {}
    form.value.bollo_auto = paramBool(d.bollo_auto, false)
    // bollo_soglia: BE serializza Decimal come stringa (es. "100.00") o null.
    form.value.bollo_soglia = paramNumber(d.bollo_soglia, null)
    form.value.rounding_policy = paramString(d.rounding_policy, null)
  } catch (err) {
    // Best-effort: in caso di errore l'utente compila manualmente.
    // Console warning aiuta il debug senza disturbare l'utente.
    console.warn('[EmittenteFiscaleDrawer] form-defaults non disponibili', err)
  }
}

function resetForm() {
  soggettoSelezionato.value = null
  detail.value = null
  confermaRegime.value = false
  form.value = defaultForm()
}

function populateFormFromDetail(d) {
  confermaRegime.value = false
  form.value = {
    codice: d.codice || '',
    attivo: !!d.attivo,
    regime_fiscale_rf: d.regime_fiscale_rf ?? null,
    bollo_auto: !!d.bollo_auto,
    bollo_soglia: d.bollo_soglia,
    rounding_policy: d.rounding_policy || null,
    valuta_id: d.valuta_id ?? null
  }
}

// Validazione P.IVA del soggetto selezionato (requisito legale per emittente fiscale).
// Il backend rifiuta comunque la creazione, qui blocchiamo lato UI per UX migliore.
const soggettoHasPartitaIva = computed(() => {
  const s = soggettoSelezionato.value
  if (!s) return false
  const piva = s.partita_iva || s.piva || ''
  return typeof piva === 'string' && piva.trim().length > 0
})

// Carica dati quando il drawer si apre.
// ⛔ Fino al 2026-10-23 la lettura stava fuori da `execute`, con un `catch` che
//    rimandava all'«interceptor axios globale»: ma quello non mostra toast, e un
//    dettaglio che non arrivava lasciava il drawer vuoto senza un motivo.
//    `execute` accetta anche l'azione di uno store (il dato gia' estratto).
watch(() => props.visible, async (val) => {
  if (!val) return
  if (isEdit.value && props.emittenteId) {
    const d = await execute(() => store.fetchDetail(props.emittenteId))
    if (d) {
      detail.value = d
      populateFormFromDetail(d)
      fissa()
    } else {
      detail.value = null
    }
  } else {
    resetForm()
    // Fase 3: applica defaults form da config.parameters (best-effort).
    // Pattern allineato a catalogo Fase 8 (ArticoloDrawer).
    await applyFormDefaults()
    // Fotografia DOPO i default: sono scritti dal codice, non dall'utente.
    if (props.visible && !isEdit.value) fissa()
  }
})

function onSoggettoSelezionato(data) { soggettoSelezionato.value = data }
function onSoggettoCreato(data) { soggettoSelezionato.value = data }
function clearSoggetto() { soggettoSelezionato.value = null }

// Vincolo bollo: se bollo automatico e' OFF, la soglia non e' applicabile
// e viene azzerata a null. L'input UI viene anche disabilitato.
watch(() => form.value.bollo_auto, (v) => {
  if (!v) form.value.bollo_soglia = null
})

// ⭐ LA FORMA DELLA SIGLA, e lo specchio di un vincolo che il DB ha davvero:
//    `chk_emittenti_fiscali_codice_forma` + il guard che da' la frase
//    (`anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma`, 2026-08-31).
// ⛔ I due numeri NON si scrivono qui: vengono da `FIELD_LENGTH`, che e' gia'
//    la sede dei vincoli di lunghezza campo (`IBAN_MAX`). Servono in tre punti
//    — regex, `maxlength` e la frase dell'hint — e tre letterali si allineano a
//    mano finche' qualcuno se ne dimentica.
// ⚠️ Perche' cosi' corta: dal 2026-08-31 la sigla sta DENTRO il codice commessa
//    — `CMM-<sigla>-<anno>-<9 cifre>` — che si legge separando sui trattini. E
//    il `codice` e' IMMUTABILE dopo la create: una sigla sbagliata non si
//    corregge piu'.
const CODICE_EMITTENTE_RE = new RegExp(
  `^[A-Z0-9]{${FIELD_LENGTH.EMITTENTE_CODICE_MIN},${FIELD_LENGTH.EMITTENTE_CODICE_MAX}}$`
)

// In EDIT non c'e' piu' un campo obbligatorio da validare (`descrizione` era
// l'unico): i restanti sono opzionali o hanno default, quindi il salvataggio e'
// sempre ammesso. In CREATE restano soggetto con P.IVA e codice.
const canSave = computed(() => {
  // Il regime e' NOT NULL a DB: in modifica non si svuota (il select non ha
  // «pulisci»), in creazione si sceglie.
  if (isEdit.value) return !!form.value.regime_fiscale_rf
  return !!soggettoSelezionato.value
      && soggettoHasPartitaIva.value
      && CODICE_EMITTENTE_RE.test(form.value.codice.trim())
      && !!form.value.regime_fiscale_rf
})

async function save() {
  if (!canSave.value) return
  const payload = {
    attivo: form.value.attivo,
    bollo_auto: form.value.bollo_auto,
    bollo_soglia: form.value.bollo_soglia,
    rounding_policy: form.value.rounding_policy || null,
    valuta_id: form.value.valuta_id || null
  }
  // ⛔ Mai `null` ne' '' sul regime (NOT NULL a DB, 400 dal backend): o il
  //    codice scelto, o la chiave assente.
  if (regimeDaDichiarare.value) payload.regime_fiscale_rf = form.value.regime_fiscale_rf
  let result
  if (isEdit.value) {
    result = await execute(
      () => store.update(props.emittenteId, payload),
      { successMessage: t('amministrazione.emittenti_fiscali.updated') }
    )
  } else {
    payload.soggetto_id = soggettoSelezionato.value.id
    payload.codice = form.value.codice.trim()
    result = await execute(
      () => store.create(payload),
      { successMessage: t('amministrazione.emittenti_fiscali.created') }
    )
  }
  if (result !== null) { fissa(); emit('saved', result) }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="drawerTitle"
    :icon="isEdit ? MANAGE_ICONS.EDIT : MANAGE_ICONS.ADD"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    :save-label="isEdit ? t('common.save') : t('common.create')"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="save"
  >
      <div class="form-grid">
        <!-- ⚠️ Un emittente NON è solo una riga di anagrafica: senza i propri
             registri di numerazione la sua prima fattura si ferma con
             `E_CONFIG_MANCANTE`.
             Dal 2026-08-19 (P-6) ogni registro è intestato a un emittente e
             NON esiste più un registro generico di ripiego: è fail-closed, ed
             è voluto — meglio fermarsi che numerare sul progressivo di
             un'altra azienda. Ma l'operatore lo scoprirebbe solo al primo
             documento, cioè tardi e altrove: qui lo sa prima.
             ⛔ Non si creano i registri per conto suo: «quale serie» è una
             scelta fiscale (la serie significa CANALE, non azienda) e
             indovinarla è precisamente ciò che D-P6-2 evita. -->
        <Message
          v-if="!isEdit"
          severity="info"
          :closable="false"
        >
          {{ t('amministrazione.emittenti_fiscali.avviso_registri') }}
        </Message>

        <!-- Soggetto -->
        <h4>{{ t('amministrazione.emittenti_fiscali.field_soggetto') }}</h4>
        <template v-if="!isEdit">
          <div v-if="soggettoSelezionato">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale || soggettoSelezionato.ragione_sociale_completa"
              :id-fiscale="soggettoSelezionato.cf || soggettoSelezionato.codice_fiscale || soggettoSelezionato.piva || soggettoSelezionato.partita_iva"
            />
            <!-- Validazione P.IVA: requisito legale per emittente fiscale -->
            <Message
              v-if="!soggettoHasPartitaIva"
              severity="warn"
              :closable="false"
            >
              {{ t('amministrazione.emittenti_fiscali.soggetto_no_piva') }}
            </Message>
            <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else>
            <Button :label="t('resolver.open')" :icon="MANAGE_ICONS.RICERCA"
              outlined @click="resolverVisible = true" />
          </div>
        </template>
        <div v-if="isEdit && detail">
          <SoggettoMessageBanner
            :ragione-sociale="detail.ragione_sociale_completa"
            :id-fiscale="detail.codice_fiscale || detail.partita_iva"
          />
        </div>

        <!-- Sezioni dati emittente: visibili solo dopo selezione soggetto (create) o sempre (edit) -->
        <template v-if="isEdit || (soggettoSelezionato && soggettoHasPartitaIva)">
          <h4>{{ t('amministrazione.emittenti_fiscali.section_anagrafica') }}</h4>

          <!-- ⚠️ Il maiuscolo si ALZA, il trattino si RIFIUTA: e' la stessa
               asimmetria del guard DB. `normalizeUpperNoSpaces` porta `acme`
               a `ACME` (forma canonica, non un requisito da conoscere),
               mentre `blockNonAlphanumeric` non lascia nemmeno digitare il
               `-` invece di toglierlo dopo — togliere caratteri a un
               identificatore appena scritto e' una cosa che chi lo scrive
               deve sapere. -->
          <div class="form-field">
            <label>{{ t('amministrazione.emittenti_fiscali.field_codice') }} *</label>
            <InputText
              v-model="form.codice"
              class="app-codice-input"
              :disabled="isEdit"
              :maxlength="FIELD_LENGTH.EMITTENTE_CODICE_MAX"
              :invalid="campiErrati.includes('codice')"
              @keypress="blockNonAlphanumeric"
              @input="normalizeUpperNoSpaces(form, 'codice')"
            />
            <small v-if="!isEdit" class="app-field-hint">
              {{ t('amministrazione.emittenti_fiscali.field_codice_hint', {
                min: FIELD_LENGTH.EMITTENTE_CODICE_MIN,
                max: FIELD_LENGTH.EMITTENTE_CODICE_MAX,
              }) }}
            </small>
          </div>

          <!-- Nessun campo "descrizione": la denominazione dell'emittente e'
               la ragione sociale del soggetto, gia' mostrata dal
               SoggettoMessageBanner qui sopra (colonna droppata il
               2026-08-02, `brief-emittente-ragione-sociale-dal-soggetto.md`). -->

          <h4>{{ t('amministrazione.emittenti_fiscali.section_fiscale') }}</h4>

          <!-- Il regime entra nell'esigibilita' IVA delle fatture (un regime
               per cassa la rende differita: lo dice il catalogo, non il
               codice): si sceglie dal catalogo e si CONFERMA (vedi
               `confermaRegime` nello script). -->
          <div class="form-field">
            <label>{{ t('amministrazione.emittenti_fiscali.field_regime_fiscale_rf') }} *</label>
            <LookupSelect
              v-model="form.regime_fiscale_rf"
              rel="config.regimi_fiscali"
              value-field="codice_interno"
              show-code
              :voce-corrente="voceRegimeCorrente"
              :placeholder="t('amministrazione.emittenti_fiscali.field_regime_fiscale_rf')"
              :invalid="campiErrati.includes('regime_fiscale_rf')"
            />
            <small class="mt-1 app-text-muted">
              {{ t('amministrazione.emittenti_fiscali.regime_fiscale_rf_hint') }}
            </small>
            <template v-if="isEdit && detail">
              <small v-if="regimeCambiato" class="mt-1 app-field-hint">
                {{ t('amministrazione.emittenti_fiscali.regime_confermato_al_salvataggio') }}
              </small>
              <small v-else-if="regimeConfermato" class="mt-1 app-text-muted">
                {{ t('amministrazione.emittenti_fiscali.regime_confermato_il', {
                  data: displayTimestamp(detail.regime_fiscale_confermato_il),
                  utente: detail.regime_fiscale_confermato_da,
                }) }}
              </small>
              <Message v-else-if="confermaRegime" severity="info" size="small" class="mt-1">
                {{ t('amministrazione.emittenti_fiscali.regime_confermato_al_salvataggio') }}
              </Message>
              <Message v-else severity="warn" size="small" class="mt-1">
                {{ t('amministrazione.emittenti_fiscali.regime_non_confermato') }}
                <Button
                  v-if="!isReadonly"
                  :label="t('amministrazione.emittenti_fiscali.regime_conferma')"
                  size="small" text
                  @click="confermaRegime = true"
                />
              </Message>
            </template>
          </div>

          <h4>{{ t('amministrazione.emittenti_fiscali.section_bollo') }}</h4>

          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('amministrazione.emittenti_fiscali.field_bollo_auto') }}</label>
              <ToggleSwitch v-model="form.bollo_auto" />
            </div>
            <div class="form-field">
              <label>{{ t('amministrazione.emittenti_fiscali.field_bollo_soglia') }}</label>
              <!-- Editabile solo se bollo_auto = true; altrimenti azzerata via watch. -->
              <InputNumber
                v-model="form.bollo_soglia"
                :disabled="!form.bollo_auto"
                :min-fraction-digits="2" :max-fraction-digits="2"
              />
            </div>
          </div>

          <div class="form-field">
            <label>{{ t('amministrazione.emittenti_fiscali.field_rounding_policy') }}</label>
            <EmittenteRoundingModeSelect
              v-model="form.rounding_policy"
              :placeholder="t('amministrazione.emittenti_fiscali.field_rounding_policy')"
              show-clear
            />
          </div>

          <!-- Valuta di default: livello 3 della catena resolve_valuta_default
               usata da preventivi/contratti senza BA. Senza questo valore i
               form-defaults restituiscono valuta vuota. -->
          <div class="form-field">
            <label>{{ t('amministrazione.emittenti_fiscali.field_valuta') }}</label>
            <LookupSelect
              v-model="form.valuta_id"
              rel="config.valute"
              :placeholder="t('amministrazione.emittenti_fiscali.field_valuta')"
              show-clear
            />
            <small class="mt-1 app-text-muted">
              {{ t('amministrazione.emittenti_fiscali.field_valuta_hint') }}
            </small>
          </div>

          <!-- Attivo: ultimo elemento del form (richiesta UX) -->
          <div class="form-field">
            <label>{{ t('amministrazione.emittenti_fiscali.field_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo"
              :invalid="campiErrati.includes('attivo')"
            />
          </div>
        </template>
      </div>

    <!-- Sotto-drawer SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      :tipo-ruolo-codice="TIPO_RUOLO.EMITTENTE_FISCALE"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
    />
  </AppDrawer>
</template>
