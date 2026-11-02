<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form di UNA riga di documento interno — la posizione contata
//        (inventario) o la correzione dichiarata (rettifica): articolo,
//        quantita', costo, e la posizione (ubicazione · lotto · seriale).
//        UN form con la famiglia in prop (Q-1): la quantita' si chiama
//        `qta_contata` o `qta_delta` e il motivo c'e' solo sulla rettifica —
//        lo dice `FAMIGLIE[famiglia]`, non un `if` qui.
//
// ⭐ LA VISIBILITA' DEI TRE CAMPI DI POSIZIONE LA DECIDONO I FLAG LETTI, mai
//    ricalcolati: l'ubicazione solo se il MAGAZZINO `usa_ubicazioni` (D-L2-m,
//    dal dettaglio del documento), il lotto solo se l'ARTICOLO `requires_lotto`,
//    il seriale solo se `requires_serial` — dalla riga scelta nel picker
//    (`ArticoloLookup` porta la riga intera) o dalla riga in modifica.
//
// ⭐ L'ANTEPRIMA DEI MOTIVI (Q-3, Tid 2026-09-18): al cambio di (articolo,
//    lotto, seriale, ubicazione) si chiede a `righe/motivi/` — cioe' a
//    `script.fn_check_riga_magazzino`, la STESSA funzione che il piano e la
//    primitiva usano — e il primo motivo si mostra in giallo. ⛔ Non blocca il
//    Salva: il DB accetta la riga in DRAFT (C8 b) e il piano la dichiara
//    `NON_POSTABILE`; un rifiuto qui sarebbe una regola piu' stretta del
//    modello, scritta fuori dal DB. E' best-effort: se non risponde, il form
//    resta com'e' — l'autorita' e' il posting, questa chiamata serve a far
//    VEDERE. Anti-race con `useFetchVersion` (si cambia articolo piu' in fretta
//    della risposta).
//
// ⚠️ L'articolo resta modificabile anche in edit: un conteggio digitato
//    sull'articolo sbagliato si corregge in posto (il PATCH lo accetta), non
//    cancellando e riscrivendo la riga. La regola «articolo immutabile in edit»
//    del master-detail di vendita nasce dal pricing (UoM, componenti), che qui
//    non c'e'.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'

import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { RISULTATI, useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { componiBloccoMotivo } from '../../core/utils/bloccoMotivo'
import { lookupAssets, lookupLotti, lookupUbicazioni, motiviRiga } from '../api/magazzino'
import { useDocumentiInterniStore } from '../stores/documentiInterni'
import { FAMIGLIE } from '../vocabolari'

const props = defineProps({
  famiglia: { type: String, required: true, validator: (v) => v in FAMIGLIE },
  // Il dettaglio della testata: `id`, `magazzino_id`, `magazzino_usa_ubicazioni`.
  documento: { type: Object, required: true },
  // La riga in modifica; `null` = nuova.
  riga: { type: [Object, null], default: null },
})
const emit = defineEmits(['salvata', 'annulla'])

const { t, te } = useI18n()
const f = FAMIGLIE[props.famiglia]
const store = useDocumentiInterniStore(f.codice)
const { execute, loading, campiErrati } = useApiHandler()
// Un secondo handler per l'anteprima: silenzioso, e non deve azzerare i
// `campiErrati` del Salva a ogni cambio di campo.
const { execute: leggiMotivi } = useApiHandler()
const versioneMotivi = useFetchVersion()

const isEdit = computed(() => props.riga?.id != null)
const usaUbicazioni = computed(() => props.documento?.magazzino_usa_ubicazioni === true)

const form = ref(defaultForm())

function defaultForm() {
  return {
    // L'articolo e' l'OGGETTO del lookup: porta i flag che decidono i campi.
    articolo: null,
    qta: null,
    motivo: '',
    costo_unitario: null,
    ubicazione_id: null,
    lotto_id: null,
    asset_id: null,
  }
}

// I flag letti dall'articolo scelto — `false` finche' non c'e' un articolo.
const richiedeLotto = computed(() => form.value.articolo?.requires_lotto === true)
const richiedeSeriale = computed(() => form.value.articolo?.requires_serial === true)
const nonGestito = computed(
  () => form.value.articolo != null && form.value.articolo.gestito_a_magazzino === false,
)

// ── i tre lookup di posizione, coi tre stati ─────────────────────
const ubicazioni = useLetturaTreStati(lookupUbicazioni, { estrai: RISULTATI, vuoto: [] })
const lotti = useLetturaTreStati(lookupLotti, { estrai: RISULTATI, vuoto: [] })
const assets = useLetturaTreStati(lookupAssets, { estrai: RISULTATI, vuoto: [] })

// L'id dell'articolo per cui lotti e seriali a video sono validi. ⚠️ E' una
// variabile e non un ref: serve solo a distinguere «l'articolo l'ha cambiato
// l'operatore» da «il form e' stato ricostruito da una riga», e non deve
// rendere niente.
let articoloDellaPosizione = null

// Scopo: azzera e — se l'articolo li pretende — ricarica lotti e seriali.
function ricaricaPosizione(articoloId) {
  lotti.azzera()
  assets.azzera()
  if (!articoloId) return
  if (richiedeLotto.value) lotti.carica(articoloId)
  if (richiedeSeriale.value) assets.carica(articoloId, props.documento.magazzino_id)
}

// Scopo: la riga in modifica nel form; l'articolo si ricostruisce dalla riga,
//        che porta codice, descrizione e i due flag. Lotto e seriale della riga
//        restano: sono di QUESTO articolo.
watch(
  () => props.riga,
  (r) => {
    form.value = r
      ? {
          articolo: {
            id: r.articolo_id,
            codice: r.articolo_codice,
            descrizione: r.articolo_descrizione,
            requires_lotto: r.articolo_requires_lotto,
            requires_serial: r.articolo_requires_serial,
          },
          qta: r[f.campoQta] != null ? Number(r[f.campoQta]) : null,
          motivo: r.motivo || '',
          costo_unitario: r.costo_unitario != null ? Number(r.costo_unitario) : null,
          ubicazione_id: r.ubicazione_id ?? null,
          lotto_id: r.lotto_id ?? null,
          asset_id: r.asset_id ?? null,
        }
      : defaultForm()
    articoloDellaPosizione = form.value.articolo?.id ?? null
    ricaricaPosizione(articoloDellaPosizione)
    // Dopo il giro di watch: anche la creazione conta.
    nextTick(() => fissa())
  },
  { immediate: true },
)

// ⭐ D-13 (2026-10-03, analisi-fe-chrome-drawer): la fotografia della riga.
//    Fino a quel giorno non c'era: una riga in compilazione si perdeva senza
//    domanda cambiando riga o uscendo dal drawer. Il contenitore la legge da
//    `defineExpose`. ⚠️ `visibile` sempre vero: il form esiste solo mentre e'
//    aperto, e allo smontaggio la fotografia se ne va con lui.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => true })

// Scopo: l'operatore ha cambiato articolo: lotti e seriali erano di un ALTRO
//        articolo, si azzerano e si ricaricano se il nuovo li pretende.
// ⚠️ Il confronto con `articoloDellaPosizione` distingue il gesto dalla
//    ricostruzione del form (watch sopra), che lotto e seriale li ha appena
//    scritti e non deve vederseli cancellare.
watch(
  () => form.value.articolo?.id ?? null,
  (id) => {
    if (id === articoloDellaPosizione) return
    articoloDellaPosizione = id
    form.value.lotto_id = null
    form.value.asset_id = null
    ricaricaPosizione(id)
  },
)

// Le ubicazioni sono del MAGAZZINO, una volta per form.
onMounted(() => {
  if (usaUbicazioni.value) ubicazioni.carica(props.documento.magazzino_id)
})

// ── l'anteprima dei motivi ──────────────────────────────────────
const motivi = ref([])
const primoMotivo = computed(() => motivi.value[0] ?? null)
const fraseMotivo = computed(() => {
  const m = primoMotivo.value
  if (!m) return null
  return componiBloccoMotivo(t, te, {
    reason: m.codice, reasonKey: m.reason_key, dettaglio: m.dettaglio,
  })
})
// Il campo che il primo motivo indica (`dettaglio.campo`): si accende, come
// per `campiErrati`, cosi' si vede DOVE guardare.
const campoMotivo = computed(() => primoMotivo.value?.dettaglio?.campo ?? null)

watch(
  () => [
    form.value.articolo?.id ?? null,
    form.value.lotto_id, form.value.asset_id, form.value.ubicazione_id,
  ],
  async ([articoloId, lottoId, assetId, ubicazioneId]) => {
    if (!articoloId) { motivi.value = []; return }
    const mia = versioneMotivi.tag()
    const params = { magazzino_id: props.documento.magazzino_id, articolo_id: articoloId }
    if (lottoId != null) params.lotto_id = lottoId
    if (assetId != null) params.asset_id = assetId
    if (ubicazioneId != null) params.ubicazione_id = ubicazioneId
    const esito = await leggiMotivi(() => motiviRiga(params), { silent: true })
    if (!versioneMotivi.isCurrent(mia)) return
    // Best-effort: se non risponde, nessun motivo — non un motivo inventato.
    motivi.value = Array.isArray(esito?.motivi) ? esito.motivi : []
  },
  { immediate: true },
)

// ── il salvataggio ───────────────────────────────────────────────
// ⚠️ La regola della quantita' e' della FAMIGLIA (`qtaZeroAmmessa`, `qtaMin`:
//    lo specchio del `CHECK` di riga): l'inventario accetta lo zero (una
//    posizione contata VUOTA e' un dato) e non il negativo, la rettifica il
//    contrario. Il form non propone cio' che verrebbe rifiutato — e non lo
//    decide con un `if` sul nome del campo.
const qtaValida = computed(() => {
  const q = form.value.qta
  if (q == null || Number.isNaN(Number(q))) return false
  const n = Number(q)
  if (n === 0) return f.qtaZeroAmmessa
  return f.qtaMin == null || n >= f.qtaMin
})
const canSave = computed(() => form.value.articolo?.id != null && qtaValida.value)

function buildPayload() {
  const payload = {
    articolo_id: form.value.articolo.id,
    [f.campoQta]: form.value.qta,
    costo_unitario: form.value.costo_unitario,
    // ⚠️ I campi di posizione viaggiano SEMPRE, anche a `null`: in modifica
    //    `null` AZZERA (togliere il lotto), e alla nascita `null` e' NULL. Un
    //    campo non mostrato si manda `null`, cosi' un valore rimasto in
    //    memoria da un articolo precedente non arriva al database.
    ubicazione_id: usaUbicazioni.value ? form.value.ubicazione_id : null,
    lotto_id: richiedeLotto.value ? form.value.lotto_id : null,
    asset_id: richiedeSeriale.value ? form.value.asset_id : null,
  }
  if (f.conMotivo) payload.motivo = form.value.motivo?.trim() || null
  return payload
}

async function onSalva() {
  const payload = buildPayload()
  const esito = await execute(
    () => (isEdit.value
      ? store.aggiornaRiga(props.documento.id, props.riga.id, payload)
      : store.creaRiga(props.documento.id, payload)),
    { successMessage: t('magazzino.documenti_interni.riga.salvata') },
  )
  if (esito !== null) emit('salvata')
}

// Il campo si accende se il BACKEND lo indica (`campiErrati`) o se l'anteprima
// dei motivi lo nomina: due sorgenti, un solo bordo.
function acceso(campo) {
  return campiErrati.value.includes(campo) || campoMotivo.value === campo
}

defineExpose({ modificato, chiudiConConferma })
</script>

<template>
  <div class="app-drawer-section">
    <h4>
      {{ isEdit
        ? t('magazzino.documenti_interni.riga.modifica')
        : t('magazzino.documenti_interni.riga.nuova') }}
    </h4>
  </div>

  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('magazzino.documenti_interni.riga.campo_articolo') }} *</label>
      <!-- R-5: il picker propone SOLO gli articoli gestiti a magazzino — un
           articolo non gestito non e' registrabile, e proporlo e' mandare
           l'operatore a costruire una riga che il piano bocciera'. ⚠️ Il
           riquadro qui sotto resta: una riga scritta PRIMA del filtro, o da
           un client qualunque, va comunque spiegata a chi la rilegge. -->
      <ArticoloLookup
        v-model="form.articolo"
        :filtri="{ gestitiAMagazzino: 'solo' }"
        :placeholder="t('magazzino.documenti_interni.riga.campo_articolo_placeholder')"
        :invalid="acceso('articolo_id')"
      />
      <!-- ⭐ L'articolo NON gestito a magazzino si dice subito: la riga si
           salva (Q-3), ma il piano la dichiarera' NON_POSTABILE e la
           registrazione rifiutera' tutto. Il flag e' quello letto. -->
      <small v-if="nonGestito" class="app-text-muted">
        {{ t('magazzino.documenti_interni.riga.articolo_non_gestito') }}
      </small>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t(`magazzino.documenti_interni.riga.campo_${f.campoQta}`) }} *</label>
        <InputNumber
          v-model="form.qta"
          :min-fraction-digits="0"
          :max-fraction-digits="6"
          :min="f.qtaMin ?? undefined"
          :invalid="acceso(f.campoQta)"
        />
        <small class="app-text-muted">
          {{ t(`magazzino.documenti_interni.riga.aiuto_${f.campoQta}`) }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('magazzino.documenti_interni.riga.campo_costo') }}</label>
        <InputNumber
          v-model="form.costo_unitario"
          mode="currency"
          currency="EUR"
          locale="it-IT"
          :min="0"
          :max-fraction-digits="6"
          :invalid="acceso('costo_unitario')"
        />
        <!-- Vuoto = alla media corrente del registro: e' il caso normale. -->
        <small class="app-text-muted">
          {{ t('magazzino.documenti_interni.riga.aiuto_costo') }}
        </small>
      </div>
    </div>

    <div v-if="f.conMotivo" class="form-field">
      <label>{{ t('magazzino.documenti_interni.riga.campo_motivo') }}</label>
      <InputText v-model="form.motivo" maxlength="200" :invalid="acceso('motivo')" />
    </div>

    <!-- ══ La posizione: solo i campi che magazzino e articolo pretendono ══ -->
    <div v-if="usaUbicazioni || richiedeLotto || richiedeSeriale" class="form-grid-2col">
      <div v-if="usaUbicazioni" class="form-field">
        <label>{{ t('magazzino.documenti_interni.riga.campo_ubicazione') }} *</label>
        <Select
          v-model="form.ubicazione_id"
          :options="ubicazioni.dati.value"
          option-label="codice"
          option-value="id"
          :loading="ubicazioni.loading.value"
          :placeholder="t('magazzino.documenti_interni.riga.campo_ubicazione_placeholder')"
          :invalid="acceso('ubicazione_id')"
          filter
          show-clear
        />
        <small v-if="ubicazioni.caricati.value && ubicazioni.errore.value" class="app-text-muted">
          {{ t('magazzino.documenti_interni.riga.lookup_non_letto') }}
        </small>
      </div>
      <div v-if="richiedeLotto" class="form-field">
        <label>{{ t('magazzino.documenti_interni.riga.campo_lotto') }} *</label>
        <Select
          v-model="form.lotto_id"
          :options="lotti.dati.value"
          option-label="codice"
          option-value="id"
          :loading="lotti.loading.value"
          :placeholder="t('magazzino.documenti_interni.riga.campo_lotto_placeholder')"
          :invalid="acceso('lotto_id')"
          filter
          show-clear
        />
        <small v-if="lotti.caricati.value && lotti.errore.value" class="app-text-muted">
          {{ t('magazzino.documenti_interni.riga.lookup_non_letto') }}
        </small>
        <!-- Nessun lotto attivo per l'articolo: si dice, e si dice dove si
             crea (il pannello config, tabella `magazzino.lotti`). -->
        <small v-else-if="lotti.caricati.value && !lotti.dati.value.length" class="app-text-muted">
          {{ t('magazzino.documenti_interni.riga.nessun_lotto') }}
        </small>
      </div>
      <div v-if="richiedeSeriale" class="form-field">
        <label>{{ t('magazzino.documenti_interni.riga.campo_seriale') }} *</label>
        <Select
          v-model="form.asset_id"
          :options="assets.dati.value"
          option-label="seriale"
          option-value="id"
          :loading="assets.loading.value"
          :placeholder="t('magazzino.documenti_interni.riga.campo_seriale_placeholder')"
          :invalid="acceso('asset_id')"
          filter
          show-clear
        />
        <small v-if="assets.caricati.value && assets.errore.value" class="app-text-muted">
          {{ t('magazzino.documenti_interni.riga.lookup_non_letto') }}
        </small>
        <small v-else-if="assets.caricati.value && !assets.dati.value.length" class="app-text-muted">
          {{ t('magazzino.documenti_interni.riga.nessun_seriale') }}
        </small>
      </div>
    </div>

    <!-- ⭐ L'anteprima: il primo motivo per cui la riga, cosi' com'e', non
         passera' la registrazione. Giallo, non rosso: non e' un rifiuto, e'
         un avviso — la riga si salva lo stesso. -->
    <Message v-if="fraseMotivo" severity="warn" :closable="false" size="small">
      {{ t('magazzino.documenti_interni.riga.non_postabile', { motivo: fraseMotivo }) }}
    </Message>
  </div>

  <FormFooter
    :loading="loading"
    :disabled="!canSave"
    @save="onSalva"
    @cancel="chiudiConConferma(() => emit('annulla'))"
  />
</template>
