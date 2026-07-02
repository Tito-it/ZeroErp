<script setup>
// Scopo: vista-racconto del percorso pratica per l'operatore (brief FE
// "percorso narrativo"). Il percorso e' i template_flussi del tipo_prestazione;
// la fn DB dice per ciascuno lo stato del ramo (`ramo`). La vista racconta il
// viaggio in tre fasce — FATTI (✓), ADESSO (1..N azioni), POI (testo) —
// nascondendo grafo, stati-macchina, sequenza e rami morti.
//
//   ramo COMPLETATO  → FATTI      (con descrizione + esito umano)
//   ramo PERCORRIBILE→ ADESSO     (1..N passi attivi: istanza in corso o step
//                                  pronto da creare; una azione primaria ciascuno)
//   ramo FUTURO      → POI        (solo come testo leggero)
//   ramo RAMO_CHIUSO → nascosto   (bivio non preso)
//
// Le regole (prerequisiti esito-aware, ripetibilita', rami) restano a DB con
// errore parlante: qui nessuna logica di business duplicata.
//
// Modalita' tecnica (super-admin, B5): quando il flag iniettato e' attivo, la
// vista ri-espone il "plumbing" del motore — codici, sequenza, stati-macchina,
// rami — nel rendering a card orizzontali (ramo `tecnico` sotto). Default: spento.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { RAMO_STEP, STATO_FLUSSO } from '../../core/constants'
import { useInjectTechnicalMode } from '../../core/composables/useTechnicalMode'
import { getUiActivity } from '../uiActivityRegistry'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()

// Flag modalita' tecnica (default false = vista operatore). Provider + toggle
// ADMIN (auth.isSuperAdmin) montati in PraticheDashboard (provideTechnicalMode).
const tecnico = useInjectTechnicalMode()

const props = defineProps({
  percorso: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  praticaId: { type: Number, default: null },
  // Contesto cliente della pratica (BA derivato + istanza): gating affordance
  // "apri documento" + payload ereditato dal drawer. { billingAccountId, istanzaUtilityId }.
  praticaContext: { type: Object, default: () => ({}) },
  // Azione in corso (create/open): blocca i click per evitare doppia creazione.
  busy: { type: Boolean, default: false },
  // Pratica in stato terminale (CHIUSA/ANNULLATA): sola lettura. Gli step "da
  // creare" non sono cliccabili (niente nuovi flussi), i flussi esistenti
  // restano apribili ma il drawer li mostra in sola lettura.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['open-flusso', 'create-flusso', 'open-attivita'])

// --- Fasce della vista-racconto (derivate dal `ramo` calcolato dal DB) ---
// Regola di presentazione: un'istanza APERTA (DA_ESEGUIRE/IN_CORSO/SOSPESO) e'
// SEMPRE lavoro vivo → fascia ADESSO, qualunque sia il `ramo` del template.
// Copre due casi reali che il solo `ramo` nasconderebbe:
//  - ramo COMPLETATO con nuova istanza aperta dopo "Ripeti" (la fn di chiusura
//    vede l'istanza chiusa precedente e vince nel CASE);
//  - ramo RAMO_CHIUSO con istanza gia' avviata prima che il bivio prendesse
//    l'altra strada (il ramo si nasconde, il lavoro in corso no).
const STATI_ISTANZA_APERTA = [
  STATO_FLUSSO.DA_ESEGUIRE, STATO_FLUSSO.IN_CORSO, STATO_FLUSSO.SOSPESO,
]
function istanzaAperta(step) {
  return Boolean(step.flusso_id) && STATI_ISTANZA_APERTA.includes(step.stato_codice_interno)
}
const fatti = computed(
  () => props.percorso.filter(s => s.ramo === RAMO_STEP.COMPLETATO && !istanzaAperta(s)),
)
const adesso = computed(
  () => props.percorso.filter(s => s.ramo === RAMO_STEP.PERCORRIBILE || istanzaAperta(s)),
)
const poi = computed(() => props.percorso.filter(s => s.ramo === RAMO_STEP.FUTURO))
const percorsoVuoto = computed(
  () => !fatti.value.length && !adesso.value.length && !poi.value.length,
)
// Passi ADESSO con l'affordance di dominio pre-risolta (una volta per step,
// non 3 lookup a registry per render dentro il v-for).
const adessoConAttivita = computed(
  () => adesso.value.map(step => ({ step, attivita: uiActivityFor(step) })),
)
// "Poi …" come testo: descrizioni degli step futuri in sequenza. Senza segnale
// certo-vs-condizionale dal DB (P0.3 non consegnata), elenca i FUTURO come testo;
// i rami chiusi non compaiono comunque.
const poiTesto = computed(() => poi.value.map(stepTitolo).join(', '))

// Titolo umano dello step: descrizione (fallback codice).
function stepTitolo(step) {
  return step.template_flusso_descrizione || step.template_flusso_codice
}
// Severity dal codice interno dello stato (invariata: unico valore mappato).
function statoSev(step) {
  return step.flusso_id ? statoFlussoSeverity(step.stato_codice_interno) : 'secondary'
}

// Attività UI di dominio offribile dallo step (azione_ui_key dal template):
// affordance "apri documento" diretta, gemella del pulsante nel FlussoDrawer.
// Gating: non readonly, attività registrata, e (se richiesto) cliente attivo.
function uiActivityFor(step) {
  if (props.readonly) return null
  const act = getUiActivity(step.template_azione_ui_key)
  if (!act) return null
  if (act.requiresActiveClient && props.praticaContext?.billingAccountId == null) return null
  return act
}
function onApriAttivita(step) {
  if (props.busy) return
  emit('open-attivita', {
    key: step.template_azione_ui_key,
    praticaId: props.praticaId,
    billingAccountId: props.praticaContext?.billingAccountId ?? null,
    istanzaUtilityId: props.praticaContext?.istanzaUtilityId ?? null,
    // Aggancio per-flusso: il documento si lega al flusso d'origine di QUESTO
    // step. Lo step puo' non avere ancora un'istanza (flusso_id null → l'host la
    // crea); l'host legge lo stato reale dal BE e avvia il flusso se serve.
    flussoId: step.flusso_id ?? null,
    templateFlussoId: step.template_flusso_id,
  })
}

// Azione primaria generica dello step ADESSO (quando non c'e' un'affordance di
// dominio): apri l'istanza esistente, oppure creala ed eseguila.
function onClick(step) {
  if (props.busy) return
  if (step.flusso_id) { emit('open-flusso', step.flusso_id); return }
  if (props.readonly) return
  emit('create-flusso', step.template_flusso_id)
}
// Un passo ADESSO e' azionabile con la primaria generica se: ha gia' un'istanza
// (sempre apribile, anche readonly → drawer in sola lettura) OPPURE e' creabile
// (non readonly). In readonly senza istanza → non azionabile (niente nuovo flusso).
function canActGenerico(step) {
  return Boolean(step.flusso_id) || !props.readonly
}

// Ripeti (workflow v2 D3): un'istanza chiusa esiste E una nuova e' creabile ORA.
// Decisione interamente del DB (`ripetibile_adesso`). Offerta come link discreto
// sia sul passo FATTO sia sulla card ADESSO: un'istanza ANNULLATO/ERRORE lascia
// lo step percorribile (→ ADESSO) e il retry deve restare raggiungibile.
function canRipeti(step) {
  return !props.readonly && Boolean(step.flusso_id) && step.ripetibile_adesso === true
}
function onRipeti(step) {
  if (props.busy) return
  emit('create-flusso', step.template_flusso_id)
}

// --- Helpers usati SOLO dal rendering tecnico (super-admin) ---
function statoLabel(step) {
  return step.flusso_id ? step.stato_codice_interno : t('pratiche.percorso_da_creare')
}
function isRamoChiuso(step) {
  return step.ramo === RAMO_STEP.RAMO_CHIUSO
}
</script>

<template>
  <div class="percorso-panel">
    <div v-if="!praticaId" class="percorso-empty" />

    <div v-else-if="loading" class="percorso-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <template v-else>
      <div class="percorso-header">{{ t('pratiche.percorso_titolo') }}</div>

      <!-- ============================ VISTA OPERATORE (racconto) ============================ -->
      <div v-if="!tecnico" class="rac">
        <div v-if="percorsoVuoto" class="rac-vuoto">{{ t('pratiche.percorso_vuoto') }}</div>

        <template v-else>
          <!-- FATTI: passi conclusi, compatti, con esito umano -->
          <div v-if="fatti.length" class="rac-fatti">
            <div v-for="step in fatti" :key="step.template_flusso_id" class="rac-fatto">
              <i class="pi pi-check-circle rac-fatto-icon" />
              <span class="rac-fatto-title">{{ stepTitolo(step) }}</span>
              <span v-if="step.esito_descrizione" class="rac-fatto-esito">· {{ step.esito_descrizione }}</span>
              <span
                v-if="canRipeti(step)"
                class="rac-ripeti"
                :title="t('pratiche.percorso_ripeti_hint')"
                @click="onRipeti(step)"
              >
                <i class="pi pi-replay" /> {{ t('pratiche.percorso_ripeti') }}
              </span>
            </div>
          </div>

          <!-- ADESSO: 1..N passi attivi, ciascuno con una azione primaria -->
          <div v-for="{ step, attivita } in adessoConAttivita" :key="step.template_flusso_id" class="rac-adesso">
            <div class="rac-adesso-head">
              <span class="rac-adesso-label">{{ t('pratiche.percorso_adesso') }}</span>
              <Tag
                v-if="step.flusso_id && step.stato_descrizione"
                :value="step.stato_descrizione"
                :severity="statoSev(step)"
                size="small"
              />
            </div>
            <div class="rac-adesso-title">{{ stepTitolo(step) }}</div>
            <div class="rac-adesso-actions">
              <!-- Affordance di dominio (apri documento) se dichiarata dal template… -->
              <Button
                v-if="attivita"
                :label="t(attivita.label)"
                :icon="attivita.icon"
                size="small"
                :disabled="busy"
                @click="onApriAttivita(step)"
              />
              <!-- Azione generica: primaria se non c'e' attivita' di dominio;
                   secondaria (testuale) accanto all'attivita' quando l'istanza
                   esiste — registrare esito/sospendere/assegnare passa dal
                   drawer del passo e deve restare raggiungibile. -->
              <Button
                v-if="!attivita && canActGenerico(step)"
                :label="step.flusso_id ? t('pratiche.percorso_apri') : t('pratiche.percorso_crea')"
                :icon="step.flusso_id ? 'pi pi-folder-open' : 'pi pi-plus-circle'"
                size="small"
                :disabled="busy"
                @click="onClick(step)"
              />
              <Button
                v-else-if="attivita && step.flusso_id"
                :label="t('pratiche.percorso_apri')"
                icon="pi pi-folder-open"
                size="small"
                text
                :disabled="busy"
                @click="onClick(step)"
              />
              <!-- Retry di un'istanza ANNULLATO/ERRORE ancora percorribile -->
              <span
                v-if="canRipeti(step)"
                class="rac-ripeti"
                :title="t('pratiche.percorso_ripeti_hint')"
                @click="onRipeti(step)"
              >
                <i class="pi pi-replay" /> {{ t('pratiche.percorso_ripeti') }}
              </span>
              <span v-if="!attivita && !canActGenerico(step)" class="rac-locked">
                <i class="pi pi-lock" /> {{ t('pratiche.percorso_non_disponibile') }}
              </span>
            </div>
          </div>

          <!-- POI: prossimi passi come testo leggero (non card cliccabili) -->
          <div v-if="poi.length" class="rac-poi">
            <span class="rac-poi-label">{{ t('pratiche.percorso_poi') }}:</span> {{ poiTesto }}
          </div>
        </template>
      </div>

      <!-- ===================== VISTA TECNICA (super-admin, B5) — plumbing motore ===================== -->
      <div v-else class="percorso-steps">
        <template v-for="(step, i) in percorso" :key="step.template_flusso_id">
          <div
            class="percorso-step"
            :class="{
              'percorso-step-done': step.stato_codice_interno === STATO_FLUSSO.COMPLETATO,
              'percorso-step-todo': !step.flusso_id,
              'percorso-step-busy': busy,
              'percorso-step-ramo-chiuso': isRamoChiuso(step),
              'percorso-step-disabled': !canActGenerico(step),
            }"
            @click="onClick(step)"
          >
            <div class="percorso-step-top">
              <span class="percorso-step-seq">#{{ step.sequenza }}</span>
              <Tag :value="statoLabel(step)" :severity="statoSev(step)" size="small" />
            </div>
            <div class="percorso-step-title">
              {{ step.template_flusso_codice }}
              <i
                v-if="step.has_handler"
                class="pi pi-bolt percorso-handler"
                :title="t('pratiche.percorso_handler')"
              />
            </div>
            <div v-if="step.esito" class="percorso-step-esito">
              {{ t('pratiche.flusso_esito') }}: <strong>{{ step.esito }}</strong>
            </div>
            <div v-if="isRamoChiuso(step)" class="percorso-step-action percorso-ramo-chiuso">
              <i class="pi pi-ban" :title="t('pratiche.percorso_ramo_chiuso_hint')" />
              {{ t('pratiche.percorso_ramo_chiuso') }}
            </div>
            <div v-else-if="!canActGenerico(step)" class="percorso-step-action">
              <i class="pi pi-lock" :title="t('pratiche.percorso_non_disponibile')" />
              {{ t('pratiche.percorso_non_disponibile') }}
            </div>
            <div v-else class="percorso-step-action">
              <i :class="step.flusso_id ? 'pi pi-folder-open' : 'pi pi-plus-circle'" />
              {{ step.flusso_id ? t('pratiche.percorso_apri') : t('pratiche.percorso_crea') }}
              <span
                v-if="canRipeti(step)"
                class="percorso-ripeti"
                :title="t('pratiche.percorso_ripeti_hint')"
                @click.stop="onRipeti(step)"
              >
                <i class="pi pi-replay" /> {{ t('pratiche.percorso_ripeti') }}
              </span>
            </div>
            <div
              v-if="uiActivityFor(step)"
              class="percorso-step-action percorso-attivita"
              :title="t(uiActivityFor(step).label)"
              @click.stop="onApriAttivita(step)"
            >
              <i :class="uiActivityFor(step).icon" /> {{ t(uiActivityFor(step).label) }}
            </div>
          </div>
          <i v-if="i < percorso.length - 1" class="pi pi-angle-right percorso-arrow" />
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.percorso-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--surface-card);
}

.percorso-empty,
.percorso-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.percorso-header {
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-color-secondary);
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-50);
  flex-shrink: 0;
}

/* ---------------- Vista-racconto (operatore) ---------------- */
.rac {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.75rem;
  overflow-y: auto;
  flex: 1;
  /* Senza min-height:0 il figlio flex non scende sotto l'altezza del contenuto
     (min-height:auto) → overflow-y non si attiva e il pannello (overflow:hidden)
     taglia il fondo del racconto. Con min-height:0 scrolla dentro i suoi 230px. */
  min-height: 0;
}

.rac-vuoto {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  padding: 0.5rem 0;
}

/* FATTI */
.rac-fatti {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.rac-fatto {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: var(--text-color-secondary);
}

.rac-fatto-icon {
  color: var(--app-success-color);
  font-size: 0.9rem;
}

.rac-fatto-title { font-weight: 500; }
.rac-fatto-esito { font-style: italic; }

.rac-ripeti {
  margin-left: 0.35rem;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: var(--p-primary-color);
  font-weight: 600;
  cursor: pointer;
}
.rac-ripeti:hover { text-decoration: underline; }

/* ADESSO */
.rac-adesso {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.75rem;
  border: 1px solid var(--p-primary-color);
  border-radius: 8px;
  background: var(--surface-0);
}

.rac-adesso-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rac-adesso-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--p-primary-color);
}

.rac-adesso-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.25;
}

.rac-adesso-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.rac-locked {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* POI */
.rac-poi {
  font-size: 0.82rem;
  color: var(--text-color-secondary);
  line-height: 1.4;
}
.rac-poi-label { font-weight: 600; }

/* ---------------- Vista tecnica (super-admin) — rendering a card orizzontali ---------------- */
.percorso-steps {
  display: flex;
  align-items: stretch;
  gap: 0.25rem;
  padding: 0.6rem 0.75rem;
  overflow-x: auto;
  flex: 1;
}

.percorso-step {
  flex: 0 0 auto;
  min-width: 150px;
  max-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-0);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.percorso-step:hover {
  background: var(--surface-hover);
  border-color: var(--p-primary-color);
}

.percorso-step-done { opacity: 0.8; }
.percorso-step-todo { border-style: dashed; }
.percorso-step-busy { pointer-events: none; opacity: 0.6; }
.percorso-step-disabled { cursor: not-allowed; opacity: 0.5; }
.percorso-step-disabled:hover { background: var(--surface-0); border-color: var(--surface-border); }
.percorso-step-ramo-chiuso { opacity: 0.5; border-style: dotted; }

.percorso-step-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.percorso-step-seq {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-color-secondary);
}

.percorso-step-title {
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.2;
}

.percorso-handler {
  font-size: 0.75rem;
  color: var(--p-warn-color, #f59e0b);
  margin-left: 0.2rem;
}

.percorso-step-esito {
  font-size: 0.74rem;
  color: var(--text-color-secondary);
}

.percorso-step-action {
  margin-top: auto;
  font-size: 0.74rem;
  color: var(--p-primary-color);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.percorso-ramo-chiuso { color: var(--text-color-secondary); }

.percorso-attivita {
  margin-top: 0.3rem;
  font-weight: 600;
  cursor: pointer;
}
.percorso-attivita:hover { text-decoration: underline; }

.percorso-ripeti {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-weight: 600;
}
.percorso-ripeti:hover { text-decoration: underline; }

.percorso-arrow {
  align-self: center;
  color: var(--text-color-secondary);
  font-size: 1rem;
  flex-shrink: 0;
}
</style>
