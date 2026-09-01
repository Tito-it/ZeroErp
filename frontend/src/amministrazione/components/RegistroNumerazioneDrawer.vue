<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer autonomo di UN registro di numerazione — creazione e modifica.
//        Richiamabile dal tab dell'emittente e, un domani, da qualunque altra
//        superficie (`feedback_drawer_autonomi`).
//
// ⭐ IL PEZZO CHE VALE LA MASCHERA È LA FORMA DEL NUMERO. `prefisso`,
//    `suffisso` e `lunghezza_numero` sono l'unico posto in cui si può cambiare
//    come si chiamano i documenti: prima vivevano in `config.sistema_codici`,
//    che un pannello ce l'ha; dal 2026-08-31 vivono sul registro, che non ce
//    l'aveva. È la domanda che ha aperto tutto il cantiere del prefisso — «ho
//    visto ORD0000001, dov'è fisso ORD?» — e fino a oggi la risposta era un
//    campo che nessuno poteva leggere né correggere da nessuna schermata.
//
// ⛔ LA SOLA-LETTURA DELLA FORMA È PER RIGA, NON CATEGORICA. La decide
//    `forma_blocco_reason`, che arriva da `script.fn_check_registro_forma_
//    modificabile` — la STESSA funzione che il guard DB chiama per rifiutare.
//    Un registro che non ha mai consegnato un numero si modifica; uno che l'ha
//    fatto no, e il motivo si LEGGE: un campo grigio senza spiegazione è la
//    stessa promessa mancata del cestino spento senza tooltip.
//
// ⚠️ I TRE CAMPI FISCALI SOLO SU `FATTURA`, e non basta nasconderli: vanno
//    anche non spediti. Il `CHECK` chk_registri_fatturazione_famiglia_regole_
//    fattura li rifiuta sulle altre quattro famiglie, e un `defaultForm()` che
//    li tiene in memoria li porta comunque.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
// ⛔ Mai formattare una data inline: la sede è unica
//    (`feedback_locale_formatters_centralizzato`).
import { displayDate } from '../../core/utils/date'
import { lookupCodici } from '../../core/apiCore'
import { useLookup } from '../../core/composables/useLookup'
import { DRAWER_WIDTH, FIELD_LENGTH, MANAGE_ICONS } from '../../core/constants'
import {
  REGISTRO_CIFRE_MAX,
  REGISTRO_CIFRE_MIN,
  REGISTRO_FAMIGLIA_FISCALE,
  REGISTRO_POLITICA_DATA,
  REGISTRO_POLITICA_DATA_NEUTRA,
} from '../constants'
import { useRegistriNumerazioneStore } from '../stores/registriNumerazione'
import { getRegistro } from '../api/registriNumerazione'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Message from 'primevue/message'

const { t, te } = useI18n()
const notify = useNotify()
const store = useRegistriNumerazioneStore()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  // `null` = creazione. Il drawer non ha una prop `mode`: la modalità è un
  // fatto dell'id, e due sorgenti di verità divergono.
  registroId: { type: Number, default: null },
  emittenteRagioneSociale: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'saved'])

const form = ref(defaultForm())
const dettaglio = ref(null)
const salvando = ref(false)

// Vocabolario APERTO: le famiglie stanno in `vendite.famiglie_documento` e una
// nuova arriva con un seed, non con un rilascio del frontend. Da qui il lookup
// generico invece di un elenco cablato (`feedback_lookup_whitelist_first`).
// ⛔ `useLookup` e non una fetch scritta a mano: la forma dell'envelope
//    (`r.data.data.results`) e' UNA, e indovinarla con dei fallback a catena
//    significa non accorgersi il giorno che cambia — la lista uscirebbe vuota
//    invece di rompersi.
const { items: famiglieRaw, load: caricaFamiglie } = useLookup(
  () => lookupCodici('vendite.famiglie_documento'),
)
// ⚠️ Il valore da spedire e' `codice_interno`: e' quello che la FK
//    `fk_registri_fatturazione_famiglia` referenzia, non `codice`.
const famiglie = computed(() => famiglieRaw.value.map((f) => ({
  value: f.codice_interno || f.codice,
  label: f.descrizione || f.codice_interno || f.codice,
})))

const opzioniPolitica = computed(() => REGISTRO_POLITICA_DATA.map((v) => ({
  value: v,
  label: t(`amministrazione.registri_numerazione.politica_${v.toLowerCase()}`),
})))
// `contentReady` + `@after-show`: il contenuto si monta a pannello aperto, così
// il drawer non "rimbalza" mentre carica (`feedback_content_ready_after_show`).
const contentReady = ref(false)

const isEdit = computed(() => props.registroId != null)

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    famiglia_documento: REGISTRO_FAMIGLIA_FISCALE,
    utility_id: null,
    serie_default: null,
    prefisso: '',
    suffisso: '',
    lunghezza_numero: 7,
    politica_data_documento: REGISTRO_POLITICA_DATA_NEUTRA,
    limite_emissione_giorni: null,
    limite_emissione_giorno_mese: null,
  }
}

const isFattura = computed(
  () => form.value.famiglia_documento === REGISTRO_FAMIGLIA_FISCALE,
)

// ⭐ IL MOTIVO PER CUI LA FORMA NON SI TOCCA, letto e non dedotto.
const formaBloccata = computed(() => Boolean(dettaglio.value?.forma_blocco_reason))
const motivoForma = computed(() =>
  dettaglio.value ? motivoBloccoRiga(t, te, dettaglio.value, 'forma_blocco') : '',
)

// ⭐ L'ANTEPRIMA, e si compone QUI. Non è una regola: è la concatenazione di
//    ciò che l'operatore ha appena scritto, quindi chiederla al backend
//    significherebbe un giro di rete per una `padStart`. È l'unica forma in cui
//    si capisce cosa si sta cambiando senza doverlo dedurre.
const anteprima = computed(() => {
  const cifre = Math.max(
    REGISTRO_CIFRE_MIN,
    Math.min(Number(form.value.lunghezza_numero) || REGISTRO_CIFRE_MIN, REGISTRO_CIFRE_MAX),
  )
  return `${form.value.prefisso || ''}${'1'.padStart(cifre, '0')}${form.value.suffisso || ''}`
})

async function carica() {
  dettaglio.value = null
  if (!isEdit.value) {
    form.value = defaultForm()
    return
  }
  const res = await getRegistro(props.registroId)
  const dati = res.data.data
  dettaglio.value = dati
  form.value = {
    codice: dati.codice ?? '',
    descrizione: dati.descrizione ?? '',
    famiglia_documento: dati.famiglia_documento,
    utility_id: dati.utility_id,
    serie_default: dati.serie_default,
    prefisso: dati.prefisso ?? '',
    suffisso: dati.suffisso ?? '',
    lunghezza_numero: dati.lunghezza_numero ?? 7,
    politica_data_documento:
      dati.politica_data_documento ?? REGISTRO_POLITICA_DATA_NEUTRA,
    limite_emissione_giorni: dati.limite_emissione_giorni,
    limite_emissione_giorno_mese: dati.limite_emissione_giorno_mese,
  }
}

watch(() => props.visible, async (aperto) => {
  if (!aperto) {
    contentReady.value = false
    return
  }
  await Promise.all([caricaFamiglie(), carica()])
})

// Scopo: il payload da spedire — ⛔ i campi che il verbo non ammette NON ci
//        entrano, invece di essere spediti e lasciati rifiutare.
function payload() {
  const p = {
    codice: form.value.codice,
    descrizione: form.value.descrizione,
  }
  // ⛔ I TRE campi fiscali — i due limiti E la politica data — si spediscono
  //    SOLO su FATTURA: il `CHECK` li rifiuta sulle altre quattro famiglie.
  //    La politica era il caso peggiore dei tre: stava nel `defaultForm()`
  //    senza nessun campo a video, quindi partiva sempre col suo valore
  //    cablato — un dato spedito che l'operatore non poteva né vedere né
  //    scegliere. Ora ha il suo Select, e fuori da FATTURA non parte.
  if (isFattura.value) {
    p.politica_data_documento = form.value.politica_data_documento
    p.limite_emissione_giorni = form.value.limite_emissione_giorni
    p.limite_emissione_giorno_mese = form.value.limite_emissione_giorno_mese
  }
  // La forma si spedisce solo quando è davvero modificabile: in creazione
  // sempre, in modifica solo se la check non l'ha bloccata.
  if (!isEdit.value || !formaBloccata.value) {
    p.prefisso = form.value.prefisso
    p.suffisso = form.value.suffisso
    p.lunghezza_numero = form.value.lunghezza_numero
  }
  if (!isEdit.value) {
    p.famiglia_documento = form.value.famiglia_documento
    p.utility_id = form.value.utility_id
    p.serie_default = form.value.serie_default
  }
  return p
}

async function salva() {
  salvando.value = true
  try {
    const dati = isEdit.value
      ? await store.aggiorna(props.registroId, payload())
      : await store.crea(payload())
    notify.success(t('amministrazione.registri_numerazione.salvato'))
    emit('saved', dati)
    chiudi()
  } catch {
    // Errore gestito dall'interceptor axios globale: i due `23505` arrivano
    // già parlanti dal backend, e uno dei due accende il campo `prefisso`.
  } finally {
    salvando.value = false
  }
}

function chiudi() {
  emit('update:visible', false)
}

const titolo = computed(() => {
  const base = isEdit.value
    ? t('amministrazione.registri_numerazione.drawer_title_edit')
    : t('amministrazione.registri_numerazione.drawer_title_new')
  return props.emittenteRagioneSociale ? `${base} — ${props.emittenteRagioneSociale}` : base
})
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="contentReady = true"
  >
    <template #header>
      <DrawerTitle :icon="MANAGE_ICONS.EDIT" :title="titolo" />
    </template>

    <div v-if="contentReady" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_codice') }} *</label>
          <InputText
            v-model="form.codice"
            :maxlength="FIELD_LENGTH.REGISTRO_CODICE_MAX"
            :disabled="isReadonly"
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_descrizione') }} *</label>
          <InputText
            v-model="form.descrizione"
            :maxlength="FIELD_LENGTH.REGISTRO_DESCRIZIONE_MAX"
            :disabled="isReadonly"
            class="w-full"
          />
        </div>

        <!-- ⛔ La famiglia si sceglie SOLO in creazione: cambiarla sposterebbe
             il registro di slot (famiglia/emittente/utility), che è una
             creazione, non una modifica. -->
        <div class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_famiglia_descrizione') }}</label>
          <Select
            v-if="!isEdit"
            v-model="form.famiglia_documento"
            :options="famiglie"
            option-label="label"
            option-value="value"
            :disabled="isReadonly"
            class="w-full"
          />
          <span v-else>{{ dettaglio?.famiglia_descrizione || form.famiglia_documento }}</span>
        </div>

        <!-- ⚠️ `serie_default` SI VEDE E NON SI TOCCA (decisione di Tid,
             2026-09-01). Il guard sulla forma non la copre — entra nella chiave
             del contatore, e il mirror CSV la riscrive a ogni migrate — quindi
             un campo editabile su di lei sarebbe l'unico senza presidio. Si
             mostra perché spiega da dove viene la serie dei numeri. -->
        <div v-if="isEdit" class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_serie_default') }}</label>
          <span>{{ form.serie_default || '—' }}</span>
          <small class="app-field-hint">
            {{ t('amministrazione.registri_numerazione.serie_hint') }}
          </small>
        </div>
      </div>

      <!-- ── La forma del numero ───────────────────────────────────────── -->
      <h4 class="mt-3">{{ t('amministrazione.registri_numerazione.sezione_forma') }}</h4>

      <Message v-if="formaBloccata" severity="warn" :closable="false" class="mb-3">
        {{ motivoForma }}
      </Message>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_prefisso') }}</label>
          <!-- ⛔ `maxlength` NON è un vezzo: la colonna è `varchar(4)`, e un
               carattere in più non produce un 400 parlante ma un `DataError`,
               che non passa da `map_integrity_error`. -->
          <InputText
            v-model="form.prefisso"
            :maxlength="FIELD_LENGTH.REGISTRO_PREFISSO_MAX"
            :disabled="isReadonly || formaBloccata"
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_suffisso') }}</label>
          <InputText
            v-model="form.suffisso"
            :maxlength="FIELD_LENGTH.REGISTRO_SUFFISSO_MAX"
            :disabled="isReadonly || formaBloccata"
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.registri_numerazione.col_lunghezza_numero') }}</label>
          <InputNumber
            v-model="form.lunghezza_numero"
            :min="REGISTRO_CIFRE_MIN"
            :max="REGISTRO_CIFRE_MAX"
            :disabled="isReadonly || formaBloccata"
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.registri_numerazione.anteprima') }}</label>
          <strong>{{ anteprima }}</strong>
          <small class="app-field-hint">
            {{ t('amministrazione.registri_numerazione.anteprima_hint') }}
          </small>
        </div>
      </div>

      <!-- ── I campi che il CHECK ammette solo su FATTURA ───────────────── -->
      <template v-if="isFattura">
        <h4 class="mt-3">{{ t('amministrazione.registri_numerazione.sezione_limiti') }}</h4>
        <div class="form-grid-2col">
          <!-- ⭐ La politica data è il terzo campo condizionato del §FE-4, e
               fino alla revisione critica non aveva un campo: viaggiava nel
               payload col valore di `defaultForm()`. -->
          <div class="form-field">
            <label>{{ t('amministrazione.registri_numerazione.politica_data') }}</label>
            <Select
              v-model="form.politica_data_documento"
              :options="opzioniPolitica"
              option-label="label"
              option-value="value"
              :disabled="isReadonly"
              class="w-full"
            />
          </div>
          <div class="form-field">
            <label>{{ t('amministrazione.registri_numerazione.limite_giorni') }}</label>
            <InputNumber
              v-model="form.limite_emissione_giorni"
              :disabled="isReadonly"
              class="w-full"
            />
          </div>
          <div class="form-field">
            <label>{{ t('amministrazione.registri_numerazione.limite_giorno_mese') }}</label>
            <InputNumber
              v-model="form.limite_emissione_giorno_mese"
              :disabled="isReadonly"
              class="w-full"
            />
          </div>
        </div>
      </template>

      <!-- ── I contatori, in SOLA LETTURA ───────────────────────────────── -->
      <!-- ⛔ Non esiste nessun endpoint che li scriva, e non ne deve nascere uno
           "per l'amministratore": cambiare `last_numero` a mano significa
           riassegnare un numero già uscito, cioè due documenti con lo stesso
           numero sullo stesso sezionale.
           ⚠️ Tabella HTML e non `DataTable`: sono poche righe di sola lettura
           dentro un drawer, e importare `primevue/datatable` qui farebbe salire
           il contatore della regola zero per una cosa che non è una lista. -->
      <template v-if="isEdit && dettaglio?.progressivi?.length">
        <h4 class="mt-3">{{ t('amministrazione.registri_numerazione.sezione_contatori') }}</h4>
        <table class="app-mini-table">
          <thead>
            <tr>
              <th>{{ t('amministrazione.registri_numerazione.col_anno') }}</th>
              <th>{{ t('vendite.registri_numerazione.col_serie_default') }}</th>
              <th>{{ t('amministrazione.registri_numerazione.col_ultimo_numero') }}</th>
              <th>{{ t('amministrazione.registri_numerazione.col_ultima_data') }}</th>
            </tr>
          </thead>
          <tbody>
            <!-- La chiave del contatore e' (registro, anno, serie): `mese` non
                 esiste piu' sul database, per quanto la doc auto-gen la elenchi. -->
            <tr v-for="p in dettaglio.progressivi" :key="`${p.anno}-${p.serie}`">
              <td>{{ p.anno }}</td>
              <td>{{ p.serie || '—' }}</td>
              <td>{{ p.last_numero }}</td>
              <td>{{ displayDate(p.ultima_data) }}</td>
            </tr>
          </tbody>
        </table>
      </template>

      <div class="app-form-footer">
        <Button :label="t('common.cancel')" :icon="MANAGE_ICONS.CANCEL" text @click="chiudi" />
        <Button
          v-if="!isReadonly"
          :label="t('common.save')"
          :loading="salvando"
          @click="salva"
        />
      </div>
    </div>
  </Drawer>
</template>

<style scoped>
/* Tabella di sola lettura dei contatori: quattro colonne, poche righe.
   ⛔ Non è una lista e non deve sembrarlo — niente paginator, niente azioni. */
.app-mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.app-mini-table th,
.app-mini-table td {
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid var(--app-border-color, var(--p-content-border-color));
  text-align: left;
}
.app-mini-table th {
  font-weight: 600;
}
</style>
