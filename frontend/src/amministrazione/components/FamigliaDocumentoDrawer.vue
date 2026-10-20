<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer autonomo di UNA famiglia di documento — creazione e modifica.
//        Brief: brief-be-fe-crud-registri-di-numerazione §11.10 (FE-F6).
//
// ⭐ COSA SI STA DAVVERO CONFIGURANDO: una famiglia dice DOVE vive un documento
//    (colonna del numero, colonna del cliente, colonna della serie) e con quale
//    FORMA nascono i suoi registri.
//
// ⭐ LA FAMIGLIA E' QUELLA DI UNA SORGENTE (dal 2026-10-20,
//    brief-db-grammatica-unica-documenti 2c, G-5): in creazione si SCEGLIE la
//    sorgente (`config.sorgenti`), il suo `codice_interno` diventa quello della
//    famiglia e la tabella dei documenti e' la sua `target_table`. Schema e
//    tabella non si scrivono piu': si leggono. Non è una tabella di decodifica:
//    è la regola che il registro applica, e i registri di quella famiglia se la
//    portano dentro dal giorno in cui nascono.
//
// ⛔ LA SOLA-LETTURA DELLA STRUTTURA È PER RIGA, NON CATEGORICA. La decide
//    `struttura_blocco_reason`, che arriva da `script.fn_check_famiglia_
//    documento_struttura_modificabile` — la STESSA funzione che il guard DB
//    chiama per rifiutare. Una famiglia senza registri si corregge; una che ne
//    ha no, e il motivo si LEGGE: un campo grigio e muto è la stessa promessa
//    mancata del cestino spento senza spiegazione.
//
// ⛔ `codice_interno` NON si modifica MAI, ed è un presidio diverso dagli altri:
//    lo tiene il lock automatico `script.trgfn_lock_columns` (D3, Tid
//    2026-09-01), lo stesso delle altre diciotto tabelle. È il bersaglio della
//    FK dei registri: cambiarlo li staccherebbe tutti.
//
// ⚠️ `presidia_data_documento` SI VEDE E NON SI TOCCA. Una famiglia creata da
//    qui nasce **non fiscale** (✅ D5, §11.11): il `CHECK` dei registri cabla
//    `'FATTURA'` e un `CHECK` non può leggere un'altra tabella. Mostrarlo
//    editabile prometterebbe un comportamento che il resto del modello non dà.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { DRAWER_WIDTH, FIELD_LENGTH, MANAGE_ICONS } from '../../core/constants'
// ⭐ Le cifre sono LE STESSE dei registri, e non e' un caso: `lunghezza_default`
//    e' il valore con cui nasce `registri_fatturazione.lunghezza_numero`. Due
//    intervalli diversi lascerebbero scrivere qui un default che il registro
//    poi rifiuta — un limite inventato al posto di quello vero.
import { REGISTRO_CIFRE_MAX, REGISTRO_CIFRE_MIN } from '../constants'
import { useFamiglieDocumentoStore } from '../stores/famiglieDocumento'
import { getFamiglia, listSorgentiFamiglie } from '../api/famiglieDocumento'
import { useLookup } from '../../core/composables/useLookup'
import AppDrawer from '../../core/components/AppDrawer.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Message from 'primevue/message'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'

const { t, te } = useI18n()
const notify = useNotify()
const store = useFamiglieDocumentoStore()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  // `null` = creazione. Nessuna prop `mode`: la modalità è un fatto dell'id, e
  // due sorgenti di verità divergono (`feedback_drawer_autonomi`).
  famigliaId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

const form = ref(defaultForm())
const dettaglio = ref(null)
const salvando = ref(false)

const isEdit = computed(() => props.famigliaId != null)

function defaultForm() {
  return {
    codice_interno: '',
    codice: '',
    descrizione: '',
    colonna_numero: '',
    colonna_billing_account: '',
    colonna_serie: '',
    prefisso_default: '',
    // Il default del database, ripetuto qui perché il form deve partire da un
    // numero: 7 cifre è la forma con cui nasce un registro se nessuno dice
    // altro.
    lunghezza_default: 7,
  }
}

// ⭐ IL MOTIVO PER CUI LA STRUTTURA NON SI TOCCA, letto e non dedotto.
const strutturaBloccata = computed(
  () => Boolean(dettaglio.value?.struttura_blocco_reason),
)
const motivoStruttura = computed(() =>
  dettaglio.value ? motivoBloccoRiga(t, te, dettaglio.value, 'struttura_blocco') : '',
)

// Le sorgenti fra cui si sceglie in creazione. Si caricano solo lì: in modifica
// la sorgente è il `codice_interno`, che non si cambia.
// ⚠️ `reload` e non `load`: il drawer resta montato fra un'apertura e l'altra,
//    e i motivi che spengono una voce cambiano a ogni creazione, spegnimento o
//    riaccensione. Con la cache, la sorgente appena usata resterebbe sceglibile.
const { items: sorgentiRaw, reload: caricaSorgenti } = useLookup(listSorgentiFamiglie)

// Scopo: il motivo per cui una sorgente non si può scegliere, o `null`.
// ⛔ È un'INFORMAZIONE, non il rifiuto: a rifiutare restano l'indice unico su
//    `codice_interno` e il guard dei riferimenti. Spegnere la voce col motivo
//    accanto evita il giro «scegli, salva, leggi l'errore».
// ⚠️ Prima la tabella presa da un'ALTRA famiglia: in quel caso anche la propria
//    famiglia spenta non si può riaccendere, e il motivo giusto è quello.
function motivoSorgenteNonSceglibile(s) {
  if (s.tabella_numerata_da) {
    return t('amministrazione.famiglie_documento.sorgente_tabella_numerata', {
      famiglia: s.tabella_numerata_da,
    })
  }
  if (s.famiglia_esistente) {
    return t('amministrazione.famiglie_documento.sorgente_ha_famiglia')
  }
  return null
}

const sorgenti = computed(() => sorgentiRaw.value.map((s) => {
  const motivo = motivoSorgenteNonSceglibile(s)
  return {
    value: s.codice_interno,
    label: `${s.etichetta} (${s.codice_interno})`,
    motivo,
    disabled: motivo != null,
    tabella: s.tabella_documento,
  }
}))

// La tabella dei documenti: in modifica la dà la vista, in creazione la
// sorgente scelta. Si legge e non si scrive (G-5).
const tabellaCompleta = computed(() => {
  if (isEdit.value) return dettaglio.value?.tabella_documento || '—'
  return sorgenti.value.find((s) => s.value === form.value.codice_interno)?.tabella || '—'
})

async function carica() {
  if (!isEdit.value) {
    form.value = defaultForm()
    dettaglio.value = null
    await caricaSorgenti()
    return
  }
  const res = await getFamiglia(props.famigliaId)
  const dati = res.data.data
  dettaglio.value = dati
  form.value = {
    codice_interno: dati.codice_interno ?? '',
    codice: dati.codice ?? '',
    descrizione: dati.descrizione ?? '',
    colonna_numero: dati.colonna_numero ?? '',
    colonna_billing_account: dati.colonna_billing_account ?? '',
    colonna_serie: dati.colonna_serie ?? '',
    prefisso_default: dati.prefisso_default ?? '',
    lunghezza_default: dati.lunghezza_default ?? 7,
  }
}

watch(() => props.visible, async (aperto) => {
  if (!aperto) {
    return
  }
  await carica()
  fissa()
})

// Scopo: il payload da spedire — ⛔ i campi che il verbo non ammette NON ci
//        entrano, invece di essere spediti e lasciati rifiutare.
function payload() {
  const p = {
    descrizione: form.value.descrizione,
    prefisso_default: form.value.prefisso_default,
    lunghezza_default: form.value.lunghezza_default,
  }
  // ⛔ `codice_interno` solo in creazione: dopo lo tiene il lock automatico, e
  //    spedirlo uguale a sé stesso sveglierebbe comunque quel presidio.
  if (!isEdit.value) p.codice_interno = form.value.codice_interno
  // ⭐ Il `codice` dell'operatore si cambia in MODIFICA (Tid, 2026-09-24): alla
  //    nascita lo copia il database dal `codice_interno`, e la madre di
  //    creazione non ha il parametro.
  if (isEdit.value) p.codice = form.value.codice
  // Le tre colonne strutturali si spediscono solo quando sono davvero
  // modificabili: in creazione sempre, in modifica solo se la check non le ha
  // bloccate. La tabella non c'è: la dice la sorgente.
  if (!isEdit.value || !strutturaBloccata.value) {
    p.colonna_numero = form.value.colonna_numero
    p.colonna_billing_account = form.value.colonna_billing_account
    // ⚠️ Vuota = NULL = «questa famiglia non gestisce le serie»: è il backend a
    //    normalizzarla, e la differenza non è cosmetica — una stringa vuota
    //    risulterebbe una colonna DICHIARATA, che il guard cercherebbe sul
    //    documento senza trovarla.
    p.colonna_serie = form.value.colonna_serie
  }
  return p
}

async function salva() {
  salvando.value = true
  try {
    const dati = isEdit.value
      ? await store.aggiorna(props.famigliaId, payload())
      : await store.crea(payload())
    // ⭐ La creazione ha fatto DUE cose: la famiglia e i registri che la madre
    //    ha provveduto su ogni emittente. Dirne una sola lascerebbe scoprire
    //    l'altra per caso, aprendo il tab di un emittente.
    const creati = dati?.registri_creati
    notify.success(
      !isEdit.value && creati
        ? t('amministrazione.famiglie_documento.salvata_con_registri', { registri: creati })
        : t('amministrazione.famiglie_documento.salvata'),
    )
    emit('saved', dati)
    chiudi()
  } catch {
    // Errore gestito dall'interceptor axios globale: la tabella già numerata
    // arriva parlante dal guard del database (E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_
    // NUMERATA) e nomina la famiglia che la numera.
  } finally {
    salvando.value = false
  }
}

function chiudi() {
  emit('update:visible', false)
}

// Modifiche non salvate (2026-10-03, D-1 di
// work-done/analisi-fe-chrome-drawer.md): fino a quel giorno X, ESC,
// clic fuori e Annulla chiudevano con un `emit` diretto, e una famiglia
// compilata e non salvata si perdeva senza domanda. Anche la creazione conta:
// la fotografia e' il form vuoto. Dopo il Salva si chiude con `chiudi`
// diretto: non c'e' niente da perdere.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, {
  visibile: () => props.visible,
})

const titolo = computed(() => (isEdit.value
  ? t('amministrazione.famiglie_documento.drawer_title_edit')
  : t('amministrazione.famiglie_documento.drawer_title_new')))
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="titolo"
    :icon="MANAGE_ICONS.FAMIGLIA_DOCUMENTO"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="salvando"
    @update:visible="(v) => emit('update:visible', v)"
    @save="salva"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_codice_interno') }} *</label>
        <!-- ⭐ In creazione si SCEGLIE la sorgente (G-5): il suo codice è
             quello della famiglia. Le voci che non si possono scegliere
             restano visibili, spente, col motivo accanto.
             ⛔ Immutabile dopo la nascita: è il bersaglio della FK dei
             registri, e a tenerlo fermo è il lock automatico del database. -->
        <Select
          v-if="!isEdit"
          v-model="form.codice_interno"
          :options="sorgenti"
          option-label="label"
          option-value="value"
          option-disabled="disabled"
          :placeholder="t('amministrazione.famiglie_documento.sorgente_placeholder')"
          :disabled="isReadonly"
        >
          <template #option="{ option }">
            <div>
              <div>{{ option.label }}</div>
              <small v-if="option.motivo" class="app-field-hint">{{ option.motivo }}</small>
            </div>
          </template>
        </Select>
        <InputText v-else v-model="form.codice_interno" disabled />
        <small v-if="isEdit" class="app-field-hint">
          {{ t('amministrazione.famiglie_documento.codice_immutabile') }}
        </small>
        <small v-else class="app-field-hint">
          {{ t('amministrazione.famiglie_documento.sorgente_hint') }}
        </small>
      </div>
      <div v-if="isEdit" class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_codice') }} *</label>
        <!-- Il codice che la lista mostra e cerca: mutabile e unico. -->
        <InputText
          v-model="form.codice"
          :maxlength="FIELD_LENGTH.FAMIGLIA_CODICE_OPERATORE_MAX"
          :disabled="isReadonly"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_descrizione') }} *</label>
        <InputText
          v-model="form.descrizione"
          :maxlength="FIELD_LENGTH.FAMIGLIA_DESCRIZIONE_MAX"
          :disabled="isReadonly"
        />
      </div>
    </div>

    <h4>{{ t('amministrazione.famiglie_documento.sezione_dove_vive') }}</h4>
    <!-- ⭐ Il motivo si LEGGE, non si deduce dal campo grigio. -->
    <Message v-if="strutturaBloccata" severity="info" :closable="false">
      {{ motivoStruttura }}
    </Message>
    <div class="form-grid">
      <!-- ⭐ La tabella si LEGGE: è la `target_table` della sorgente (G-5). -->
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_tabella_documento') }}</label>
        <span>{{ tabellaCompleta }}</span>
        <small class="app-field-hint">
          {{ t('amministrazione.famiglie_documento.tabella_dalla_sorgente') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_colonna_numero') }} *</label>
        <InputText
          v-model="form.colonna_numero"
          :disabled="isReadonly || strutturaBloccata"
        />
      </div>
      <div class="form-field">
        <!-- Dal 2026-09-14 (P-9 di brief-db-modifiche-certe-ciclo-vendita-e-
             articolo) NON e' piu' obbligatoria: vuota = NULL = «questa
             famiglia non ha un billing account», la forma dell'ordine di
             acquisto (controparte = soggetto_ruolo). Stessa disciplina di
             `colonna_serie`: e' il backend a normalizzare il vuoto a NULL. -->
        <label>{{ t('vendite.famiglie_documento.col_colonna_billing_account') }}</label>
        <InputText
          v-model="form.colonna_billing_account"
          :disabled="isReadonly || strutturaBloccata"
        />
        <small class="app-field-hint">
          {{ t('amministrazione.famiglie_documento.billing_account_hint') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_colonna_serie') }}</label>
        <InputText
          v-model="form.colonna_serie"
          :disabled="isReadonly || strutturaBloccata"
        />
        <!-- ⚠️ Vuota non è «non compilata»: è un'informazione. E il database
             pretende che, se c'è, quella colonna distingua il numero. -->
        <small class="app-field-hint">
          {{ t('amministrazione.famiglie_documento.serie_hint') }}
        </small>
      </div>
    </div>

    <h4>{{ t('amministrazione.famiglie_documento.sezione_forma') }}</h4>
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_prefisso_default') }}</label>
        <InputText
          v-model="form.prefisso_default"
          :maxlength="FIELD_LENGTH.FAMIGLIA_PREFISSO_MAX"
          :disabled="isReadonly"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.famiglie_documento.col_lunghezza_default') }}</label>
        <InputNumber
          v-model="form.lunghezza_default"
          :min="REGISTRO_CIFRE_MIN"
          :max="REGISTRO_CIFRE_MAX"
          :disabled="isReadonly"
        />
      </div>
    </div>
    <!-- ⭐ Questi due non sono decorazione: sono la forma con cui NASCE un
         registro di questa famiglia, ed è la ragione per cui una COMMESSA
         creata a mano usciva a 7 cifre mentre quella del provisioning ne
         aveva 9. -->
    <small class="app-field-hint">
      {{ t('amministrazione.famiglie_documento.forma_hint') }}
    </small>

    <!-- Sola lettura: ciò che la famiglia È, e che da qui non si cambia. -->
    <template v-if="isEdit && dettaglio">
      <h4>{{ t('amministrazione.famiglie_documento.sezione_stato') }}</h4>
      <div class="form-grid">
        <!-- ⚠️ IL CONTEGGIO E' SU TUTTI GLI EMITTENTI, e va detto: questa
             schermata e' globale, ma chi ci arriva dal mondo dei registri —
             che vivono nel drawer di UN emittente — legge «2 registri» e
             capisce «due su questo emittente». Rilievo di Tid in collaudo,
             2026-09-02.
             ⭐ E il numero non e' decorazione: e' il predicato che rende
             immutabili le colonne di struttura, quindi spiega un divieto che
             l'operatore incontrera' due campi piu' su. -->
        <div class="form-field">
          <label>{{ t('amministrazione.famiglie_documento.registri_totali') }}</label>
          <span>{{ dettaglio.n_registri }} ({{ dettaglio.n_registri_attivi }} {{ t('amministrazione.famiglie_documento.attivi_suffisso') }})</span>
          <small class="app-field-hint">
            {{ t('amministrazione.famiglie_documento.registri_hint') }}
          </small>
        </div>
        <div class="form-field">
          <label>{{ t('vendite.famiglie_documento.col_presidia_data_documento') }}</label>
          <span>{{ dettaglio.presidia_data_documento ? t('common.yes') : t('common.no') }}</span>
          <small class="app-field-hint">
            {{ t('amministrazione.famiglie_documento.presidia_hint') }}
          </small>
        </div>
        <!-- ⭐ La domanda che decide i tre campi fiscali sul REGISTRO, e non è
             la stessa di sopra: il 2026-09-02 avevano la stessa risposta su
             tutte e cinque, ed è esattamente per questo che sono due colonne
             (§12.2). Una famiglia creata da qui nasce presidiata e NON
             fiscale: mostrarle insieme è l'unico modo di farlo vedere. -->
        <div class="form-field">
          <label>{{ t('amministrazione.famiglie_documento.ammette_regole_fiscali') }}</label>
          <span>{{ dettaglio.ammette_regole_fiscali ? t('common.yes') : t('common.no') }}</span>
          <small class="app-field-hint">
            {{ t('amministrazione.famiglie_documento.fiscali_hint') }}
          </small>
        </div>
      </div>
    </template>
  </AppDrawer>
</template>
