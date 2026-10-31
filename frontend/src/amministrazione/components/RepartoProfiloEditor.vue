<script setup>
// Scopo: drawer editor profilo permessi di un reparto, PER AREA.
//
// ⭐ PER AREA COME IL PANNELLO DELL'OPERATORE (2026-10-31, decisione Tid):
//    l'elenco delle aree a sinistra (livello, azioni abilitate, modifiche non
//    salvate, azioni limitate dall'area) e l'area scelta a destra — il suo
//    livello e le sue azioni di processo. Fino a quel giorno erano due tabelle
//    lunghe (tutte le aree, poi tutte le azioni) in due fisarmoniche: le azioni
//    di un'area stavano lontane dal livello che le governa. Il layout e' il BB
//    `ElencoDettaglio`, lo stesso di `OperatorePermessiTab`.
// ⭐ Le griglie sono matrici limitate dal catalogo (`MatriceCatalogo`): tutte
//    le aree e tutte le azioni, ognuna col suo valore. NON `MatriceOverride`:
//    il profilo di un reparto e' COMPLETO (`config.fn_scrivi_profilo_accesso`
//    lo sostituisce intero) e non eredita da niente — e' la sorgente da cui
//    eredita l'operatore. Niente oggetti: il profilo ha solo aree e azioni.
// ⛔ Ricerca e scelta dell'area restringono la VISTA, mai il modello: il Salva
//    manda sempre il profilo intero (`profiloDaSalvare`).
//
// ⭐ IL TETTO D'AREA: un'azione abilitata vale solo se la sua area arriva al
//    `livello_minimo_area` dell'azione (sede: `script.fn_area_consente_azione`).
//    ⛔ SOLA REGOLA DB (decisione Tid, 2026-10-31): sui valori SALVATI
//    l'avviso legge `limitata_da_area`, che la lettura del profilo calcola a DB
//    chiamando quella funzione. La copia di `tettoArea.js` serve SOLO
//    all'anteprima di cio' che l'admin sta cambiando, e lo dice
//    («anteprima: non ancora salvato») — come nel pannello dell'operatore.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRepartiStore } from '../stores/reparti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useLookup } from '../../core/composables/useLookup'
import { listAreeFunzionali, listAzioniProcesso } from '../api/amministrazione'
import { LIVELLO_ACCESSO, buildLivelloOptions, getLivelloLabel, getLivelloSeverity } from '../constants'
import { areaConsenteAzione } from '../tettoArea'
import { DRAWER_WIDTH, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ElencoDettaglio from '../../core/components/ElencoDettaglio.vue'
import MatriceCatalogo from '../../core/components/MatriceCatalogo.vue'
import Badge from 'primevue/badge'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const repartiStore = useRepartiStore()
const { execute, loading } = useApiHandler()
const { confirmSave } = useConfirmAction()
const areeFunzionali = useLookup(listAreeFunzionali, { immediate: true })
const azioniProcesso = useLookup(listAzioniProcesso, { immediate: true })

const props = defineProps({
  visible: Boolean,
  uoId: { type: Number, default: null },
  uoNome: { type: String, default: '' },
  // Sola lettura locale: si somma (OR) a quella ereditata dalla vista
  // (`useReadonlyMode(AMM_SOFTWARE)`), non la sostituisce.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const livelloOptions = buildLivelloOptions(t)

// ⚠️ La catena del dominio arriva gia' ad AppDrawer (corpo `app-readonly`,
// niente Salva), ma i controlli si spengono QUI: un Select che sembra
// attivo dice all'operatore che puo' cambiare cio' che non salvera'.
const isReadonlyEreditato = useInjectReadonly()
const isReadOnlyEffective = computed(() => props.readonly || isReadonlyEreditato.value)

const localAree = ref([])
const localAzioni = ref([])
// Il segno del profilo: chi riceve il reparto deve usare il secondo fattore.
const localRichiedeSecondoFattore = ref(false)
// I valori SALVATI, per il segno «modificata» di ogni area nell'elenco.
const salvatiAree = ref(new Map())
const salvateAzioni = ref(new Map())
// Le azioni che il DB dice limitate dall'area, sul profilo salvato.
const limitateSalvate = ref(new Set())

// Modifiche non salvate: i due elenchi raccolti in cio' che il Salva manda.
const profiloDaSalvare = computed(() => ({
  aree: localAree.value.map(a => ({ area_id: a.area_id, livello: a.livello })),
  azioni: localAzioni.value.map(a => ({ azione_id: a.azione_id, abilitata: a.abilitata })),
  richiede_secondo_fattore: localRichiedeSecondoFattore.value,
}))
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(profiloDaSalvare, { visibile: () => props.visible })

// La vista si azzera a ogni apertura (e a ogni reparto: il drawer si riapre).
const areaScelta = ref(null)
const termine = ref('')

watch(() => props.visible, async (val) => {
  if (!val || !props.uoId) return
  areaScelta.value = null
  termine.value = ''
  await repartiStore.fetchProfilo(props.uoId)

  const profilo = repartiStore.currentProfilo
  if (profilo) {
    // Inizializza con tutte le aree, precompilando quelle gia' configurate
    const existingMap = new Map((profilo.aree || []).map(a => [a.area_id, a.livello]))
    localAree.value = (areeFunzionali.items.value || []).map(af => ({
      area_id: af.id,
      area_codice: af.codice,
      area_descrizione: af.descrizione,
      livello: existingMap.get(af.id) || LIVELLO_ACCESSO.BLOCCATO
    }))

    const existingAzioni = new Map((profilo.azioni || []).map(a => [a.azione_id, a.abilitata]))
    localAzioni.value = (azioniProcesso.items.value || []).map(ap => ({
      azione_id: ap.id,
      permission_codename: ap.permission_codename,
      azione_descrizione: ap.descrizione,
      area_id: ap.area_id,
      area_codice: ap.area_codice,
      livello_minimo_area: ap.livello_minimo_area,
      pericolosa: ap.pericolosa,
      abilitata: existingAzioni.get(ap.id) || false
    }))
    localRichiedeSecondoFattore.value = !!profilo.richiede_secondo_fattore
    salvatiAree.value = new Map(localAree.value.map(a => [a.area_id, a.livello]))
    salvateAzioni.value = new Map(localAzioni.value.map(a => [a.azione_id, a.abilitata]))
    limitateSalvate.value = new Set(
      (profilo.azioni || []).filter(a => a.limitata_da_area).map(a => a.azione_id)
    )
    fissa()
  }
})

function onSave() {
  confirmSave(async () => {
    // Lo stesso payload che la fotografia confronta: una definizione sola.
    const { aree, azioni, richiede_secondo_fattore } = profiloDaSalvare.value
    const result = await execute(
      () => repartiStore.saveProfilo(props.uoId, aree, azioni, richiede_secondo_fattore),
      { successMessage: t('notifications.save_success') }
    )
    if (result !== null) emit('saved')
  }, t('amministrazione.profilo_save_confirm'))
}

// ═══ LA NAVIGAZIONE PER AREA ══════════════════════════════════════════════
// ⭐ Ogni azione APPARTIENE a un'area (`azioni_processo.area_id` NOT NULL):
//    raggrupparle e' rendere visibile una relazione del modello, e da quando
//    l'area e' un tetto e' anche la gerarchia che il DB applica.
const azioniPerArea = computed(() => {
  const m = {}
  for (const az of localAzioni.value) (m[az.area_id] ||= []).push(az)
  return m
})
const livelloArea = computed(() =>
  Object.fromEntries(localAree.value.map(a => [a.area_id, a.livello]))
)

const azioneModificata = (az) => az.abilitata !== salvateAzioni.value.get(az.azione_id)
const areaModificata = (areaId) => livelloArea.value[areaId] !== salvatiAree.value.get(areaId)

// Scopo: Stato del tetto di un'azione: `{ limitata, anteprima }`.
//        Nulla cambiato su azione e area → il DB (`limitata_da_area`);
//        altrimenti l'anteprima con la copia dichiarata della regola.
function statoTetto(az) {
  if (!azioneModificata(az) && !areaModificata(az.area_id)) {
    return { limitata: limitateSalvate.value.has(az.azione_id), anteprima: false }
  }
  return {
    limitata: az.abilitata && !areaConsenteAzione(livelloArea.value[az.area_id], az.livello_minimo_area),
    anteprima: true,
  }
}
const limitata = (az) => statoTetto(az).limitata

function riassuntoArea(area) {
  const azioni = azioniPerArea.value[area.area_id] || []
  return {
    modificata: area.livello !== salvatiAree.value.get(area.area_id) || azioni.some(azioneModificata),
    abilitate: azioni.filter(az => az.abilitata).length,
    limitate: azioni.filter(limitata).length,
  }
}
const riassunti = computed(() =>
  Object.fromEntries(localAree.value.map(a => [a.area_id, riassuntoArea(a)]))
)

const _q = computed(() => termine.value.trim().toLowerCase())
const _corrisponde = (...testi) =>
  testi.some(x => typeof x === 'string' && x.toLowerCase().includes(_q.value))
const _areaCorrisponde = (area) => _corrisponde(area.area_descrizione, area.area_codice)

// Le azioni di un'area a vista. Se la ricerca colpisce l'area, tutte.
function azioniVisibili(area) {
  const azioni = azioniPerArea.value[area.area_id] || []
  if (!_q.value || _areaCorrisponde(area)) return azioni
  return azioni.filter(az => _corrisponde(az.azione_descrizione, az.permission_codename))
}
const areeVisibili = computed(() =>
  localAree.value.filter(area =>
    !_q.value || _areaCorrisponde(area) || azioniVisibili(area).length > 0)
)

function tettoAzione(az) {
  const stato = statoTetto(az)
  if (!stato.limitata) return null
  return t('amministrazione.profilo_reparto_limitata_da_area', {
    minimo: getLivelloLabel(t, az.livello_minimo_area),
    area: getLivelloLabel(t, livelloArea.value[az.area_id]),
  }) + (stato.anteprima ? ` ${t('amministrazione.tetto_anteprima')}` : '')
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). XLARGE come la scheda permessi
       dell'operatore: stesso layout per area. -->
  <AppDrawer
    :visible="props.visible"
    :title="t('amministrazione.profilo_reparto', { nome: uoNome })"
    :icon="NAV_ICONS.PROFILI_REPARTO"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.XLARGE"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :readonly="isReadOnlyEffective"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >
    <div class="form-field">
      <label for="tg-richiede-secondo-fattore">{{ t('amministrazione.secondo_fattore.richiesto_dal_profilo') }}</label>
      <div class="app-form-inline-toggle">
        <ToggleSwitch v-model="localRichiedeSecondoFattore" input-id="tg-richiede-secondo-fattore"
          :disabled="isReadOnlyEffective" />
        <small class="app-field-hint">{{ t('amministrazione.secondo_fattore.richiesto_dal_profilo_aiuto') }}</small>
      </div>
    </div>

    <ElencoDettaglio
      v-model="areaScelta"
      :voci="areeVisibili"
      :chiave="a => a.area_id"
      :etichetta="a => a.area_descrizione"
      :modificata="a => riassunti[a.area_id].modificata"
      :testo-vuoto="t('amministrazione.permessi_nessuna_area')"
    >
      <template #filtri>
        <InputText v-model="termine" :placeholder="t('amministrazione.profilo_reparto_cerca')" />
      </template>

      <template #segni="{ voce: area }">
        <i
          v-if="riassunti[area.area_id].limitate"
          v-tooltip.top="t('amministrazione.permessi_area_limitate', { n: riassunti[area.area_id].limitate })"
          :class="[STATUS_ICONS.ERRORE, 'app-permessi-tetto-icona']"
        />
        <Badge
          v-if="riassunti[area.area_id].abilitate"
          v-tooltip.top="t('amministrazione.profilo_reparto_azioni_abilitate')"
          :value="riassunti[area.area_id].abilitate"
          severity="info"
        />
        <Tag :value="getLivelloLabel(t, area.livello)" :severity="getLivelloSeverity(area.livello)" />
      </template>

      <template #dettaglio="{ voce: area }">
        <h4>{{ area.area_descrizione }}</h4>

        <MatriceCatalogo :voci="[area]" :chiave="a => a.area_id"
          :label-voce="t('amministrazione.permessi_livello_area')" :readonly="isReadOnlyEffective">
          <template #voce>{{ t('amministrazione.permessi_livello_area') }}</template>
          <template #colonne>
            <Column :header="t('amministrazione.col_livello')" style="width: 12rem">
              <template #body="{ data }">
                <Select v-model="data.livello" :options="livelloOptions"
                  option-label="label" option-value="value" :disabled="isReadOnlyEffective" />
              </template>
            </Column>
          </template>
        </MatriceCatalogo>

        <template v-if="azioniVisibili(area).length">
          <h5>{{ t('amministrazione.permessi_azioni_area') }}</h5>
          <MatriceCatalogo :voci="azioniVisibili(area)" :chiave="a => a.azione_id"
            :label-voce="t('amministrazione.col_azione')" :readonly="isReadOnlyEffective">
            <template #voce="{ voce }">{{ voce.azione_descrizione }}</template>
            <template #colonne>
              <Column :header="t('amministrazione.col_abilitata')" style="width: 14rem">
                <template #body="{ data }">
                  <ToggleSwitch v-model="data.abilitata" :disabled="isReadOnlyEffective" />
                  <small v-if="tettoAzione(data)" class="app-permessi-tetto">{{ tettoAzione(data) }}</small>
                </template>
              </Column>
            </template>
          </MatriceCatalogo>
        </template>

        <p v-if="!(azioniPerArea[area.area_id] || []).length" class="app-permessi-nota">
          {{ t('amministrazione.profilo_reparto_area_senza_azioni') }}
        </p>
      </template>
    </ElencoDettaglio>
  </AppDrawer>
</template>

<style scoped>
h4 {
  margin: 0 0 0.5rem;
}
h5 {
  margin: 1rem 0 0.5rem;
}
.app-permessi-nota {
  font-size: 0.85rem;
  color: var(--app-text-muted);
  margin-top: 0.75rem;
}
</style>
