<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer autonomo di UNA famiglia di documento — creazione e modifica.
//        Brief: brief-be-fe-crud-registri-di-numerazione §11.10 (FE-F6).
//
// ⭐ COSA SI STA DAVVERO CONFIGURANDO: una famiglia dice DOVE vive un documento
//    (tabella, colonna del numero, colonna del cliente, colonna della serie) e
//    con quale FORMA nascono i suoi registri. Non è una tabella di decodifica:
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
import { getFamiglia } from '../api/famiglieDocumento'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'

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

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
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
    schema_tabella: '',
    nome_tabella: '',
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

// La tabella, composta: è ciò che l'operatore riconosce, e in lista arriva già
// concatenata dalla vista.
const tabellaCompleta = computed(() => {
  const s = (form.value.schema_tabella || '').trim()
  const n = (form.value.nome_tabella || '').trim()
  return s && n ? `${s}.${n}` : '—'
})

async function carica() {
  if (!isEdit.value) {
    form.value = defaultForm()
    dettaglio.value = null
    return
  }
  const res = await getFamiglia(props.famigliaId)
  const dati = res.data.data
  dettaglio.value = dati
  form.value = {
    codice_interno: dati.codice_interno ?? '',
    codice: dati.codice ?? '',
    descrizione: dati.descrizione ?? '',
    schema_tabella: dati.schema_tabella ?? '',
    nome_tabella: dati.nome_tabella ?? '',
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
  // Le quattro colonne strutturali si spediscono solo quando sono davvero
  // modificabili: in creazione sempre, in modifica solo se la check non le ha
  // bloccate.
  if (!isEdit.value || !strutturaBloccata.value) {
    p.schema_tabella = form.value.schema_tabella
    p.nome_tabella = form.value.nome_tabella
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
    // Errore gestito dall'interceptor axios globale: il duplicato di tabella
    // arriva già parlante dal backend e nomina la famiglia che la occupa.
  } finally {
    salvando.value = false
  }
}

function chiudi() {
  emit('update:visible', false)
}

const titolo = computed(() => (isEdit.value
  ? t('amministrazione.famiglie_documento.drawer_title_edit')
  : t('amministrazione.famiglie_documento.drawer_title_new')))
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :icon="MANAGE_ICONS.FAMIGLIA_DOCUMENTO" :title="titolo" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('vendite.famiglie_documento.col_codice_interno') }} *</label>
          <!-- ⛔ Immutabile dopo la nascita: è il bersaglio della FK dei
               registri, e a tenerlo fermo è il lock automatico del database. -->
          <InputText
            v-model="form.codice_interno"
            :maxlength="FIELD_LENGTH.FAMIGLIA_CODICE_MAX"
            :disabled="isReadonly || isEdit"
          />
          <small v-if="isEdit" class="app-field-hint">
            {{ t('amministrazione.famiglie_documento.codice_immutabile') }}
          </small>
          <small v-else class="app-field-hint">
            {{ t('amministrazione.famiglie_documento.codice_nasce_dal_interno') }}
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
        <div class="form-field">
          <label>{{ t('amministrazione.famiglie_documento.schema_tabella') }} *</label>
          <InputText
            v-model="form.schema_tabella"
            :disabled="isReadonly || strutturaBloccata"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.famiglie_documento.nome_tabella') }} *</label>
          <InputText
            v-model="form.nome_tabella"
            :disabled="isReadonly || strutturaBloccata"
          />
          <small class="app-field-hint">{{ tabellaCompleta }}</small>
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
