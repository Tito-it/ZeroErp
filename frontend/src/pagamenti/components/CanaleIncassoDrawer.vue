<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il drawer di configurazione di un CANALE DI INCASSO — da dove i soldi
//        arrivano, e su quale conto dell'azienda atterrano.
//
// 🔴 NON e' un pannello di configurazione qualunque. Il **conto** che un canale
//    porta e' il punto da cui il database ricava DI CHI SONO i soldi arrivati
//    prima della fattura: con due partite IVA attive, un canale agganciato al
//    conto sbagliato non da' errore — sposta il denaro nel perimetro di un
//    altro emittente, e non se ne accorge nessuno.
//
// ⭐ Per questo l'elenco dei conti e' FILTRATO dal backend (BE-8): solo quelli
//    con `uso = 'INCASSO'` del soggetto, censiti a livello di RUOLO. E ogni
//    riga porta la **utility** del conto (BE-11), perche' un elenco di IBAN
//    senza utility fa scegliere il conto del gas al posto di quello
//    dell'energia — e chi sbaglia se ne accorge dopo aver compilato il resto.
//
// ⛔ LA TRAPPOLA DEI DUE `soggetto_ruolo_id`, e sono cose diverse:
//      · quello che si sceglie in cima serve SOLO a filtrare i conti — e'
//        l'emittente, NON viaggia nel payload e sul canale non esiste;
//      · `soggetto_ruolo_id` sul canale e' il soggetto **PSP**, e lo pretende
//        solo `tipo = PSP` (`trgfn_enti_incasso_guard_psp`).
//    Confonderli significherebbe scrivere l'emittente nella colonna del PSP.
//
// ⚠️ La FILIALE e' obbligatoria su BANCA e **vietata** altrove
//    (`chk_enti_incasso_bank_branch_tipo`): un valore rimasto in memoria dopo un
//    cambio di tipo non e' un campo di troppo, e' un rifiuto del database.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AutoComplete from 'primevue/autocomplete'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'

import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import SoggettoRuoloLookup from '../../core/components/SoggettoRuoloLookup.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import {
  useEmittenteFiscaleField,
  formatEmittenteOptionLabel,
} from '../../core/composables/useEmittenteFiscaleField'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { useServerAutocomplete } from '../../core/composables/useServerAutocomplete'
import { DRAWER_WIDTH, TIPO_RUOLO } from '../../core/constants'
import { lookupBankBranches } from '../../anagrafiche/api/anagrafiche'
import {
  aggiornaEnteIncasso,
  creaEnteIncasso,
  getEnteIncasso,
  listContiIncasso,
} from '../api/pagamenti'
import { useEtichettePagamenti } from '../etichette'
import { TIPO_CANALE_CON_FILIALE, TIPO_CANALE_PSP } from '../vocabolari'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // `null` = nuovo canale.
  canaleId: { type: [Number, null], default: null },
})
const emit = defineEmits(['update:visible', 'salvato'])

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const {
  isAdminMode, currentEmittente, opzioneSessione, emittentiOptions,
  emittentiError, loadOptions,
} = useEmittenteFiscaleField()

const isEdit = computed(() => props.canaleId != null)

// ── il perimetro dell'emittente: decide QUALI conti si vedono ──────
// ⛔ NON E' PIU' UNA SCELTA, NEMMENO PER L'ADMIN (decisione di Tid,
//    2026-09-02). Prima il super admin aveva qui una combo editabile: poteva
//    configurare il canale di una partita IVA mentre la sessione ne stava
//    guardando un'altra — due verita' sullo stesso perimetro, e la seconda
//    invisibile a chi guarda la topbar. L'emittente di lavoro si sceglie una
//    volta per sessione: qui si MOSTRA, come si e' sempre fatto con
//    l'operatore.
const soggettoRuoloEmittente = ref(null)

// Il SOGGETTO-RUOLO dell'emittente di sessione — che e' la chiave con cui si
// chiedono i conti, non la PK.
// ⛔ Due famiglie di id nella stessa riga, e scambiarle non solleva niente:
//    filtra su numeri che non corrispondono e l'elenco dei conti esce vuoto
//    (`feedback_emittente_pk_vs_soggetto_ruolo`). `auth` conosce la PK della
//    sessione; il soggetto-ruolo lo porta il lookup, che qui e' gia' caricato.
// ⚠️ Per l'operatore la risposta e' nel profilo e non costa niente; per il
//    super admin va risolta dall'elenco, e finche' non e' arrivato resta
//    `null` — cioe' i conti non si chiedono con una chiave sbagliata.
const soggettoRuoloSessione = computed(
  () => currentEmittente.value?.soggettoRuoloId
    ?? opzioneSessione.value?.soggetto_ruolo_id
    ?? null,
)

// L'etichetta di CIO' CHE E' IN GIOCO, cioe' di `soggettoRuoloEmittente`.
// ⛔ NON dell'emittente di sessione, ed e' un difetto che ho scritto e corretto
//    nella stessa passata: in MODIFICA quel ref porta l'emittente DEL CANALE
//    (derivato dal conto), che non e' detto sia quello della sessione. Con
//    l'etichetta presa dalla sessione la riga avrebbe mostrato un nome e
//    filtrato i conti di un altro — due verita' nello stesso campo, e quella
//    sbagliata e' la sola che si legge.
// ⚠️ Una sorgente sola per il valore e per il nome: se il nome non si trova si
//    lascia vuoto, non si ripiega su un altro emittente.
const emittenteMostratoLabel = computed(() => {
  const sr = soggettoRuoloEmittente.value
  if (sr == null) return ''
  if (currentEmittente.value?.soggettoRuoloId === sr) {
    return currentEmittente.value.ragioneSociale
  }
  // ⚠️ Si cerca PER soggetto-ruolo, quindi le righe che non ce l'hanno non
  //    possono corrispondere: il filtro preventivo che stava qui e' caduto
  //    con la combo che lo motivava — scartava voci «non proponibili» in un
  //    elenco che non si propone piu' a nessuno.
  const trovato = (emittentiOptions.value || [])
    .find((e) => e.soggetto_ruolo_id === sr)
  return trovato ? formatEmittenteOptionLabel(trovato) : ''
})

// ⛔ Tre casi, non due: conti presenti · nessun conto di incasso · non letti.
//    L'ultimo NON si spaccia per il secondo — «questo emittente non ha conti»
//    e' un'affermazione, e su una fetch fallita e' falsa. I tre stati li tiene
//    il BB; qui resta il MOTIVO del vuoto, che viaggia con la risposta
//    (`nessun_conto_di_incasso`) e che la schermata non deve indovinare.
const {
  dati: risposta,
  caricati: contiCaricati,
  errore: erroreConti,
  loading: caricamentoConti,
  carica: caricaConti,
  azzera: azzeraConti,
} = useLetturaTreStati((id) => listContiIncasso(id))
const conti = computed(() => risposta.value?.results || [])
const nessunConto = computed(() => risposta.value?.nessun_conto_di_incasso === true)

const form = ref(defaultForm())
const filialeObj = ref(null)
const soggettoPspObj = ref(null)
// Modifiche non salvate (BB useDrawerFormPreserve): il guscio AppDrawer colora
// l'azione e chiede conferma su ogni uscita.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    tipo: null,
    attivo: true,
    soggetto_ruolo_conto_bancario_id: null,
    centro_riscossione_id: null,
    bank_branch_id: null,
    soggetto_ruolo_id: null,
    formato_flusso: '',
  }
}

const vuoleFiliale = computed(() => form.value.tipo === TIPO_CANALE_CON_FILIALE)
const vuolePsp = computed(() => form.value.tipo === TIPO_CANALE_PSP)

// ⚠️ Il salvataggio si abilita sui campi che il CONTRATTO dichiara
//    obbligatori, e non su tutto cio' che il database potrebbe rifiutare: i
//    guard parlano da soli, e un pulsante spento senza spiegazione no.
const canSave = computed(
  () =>
    !isReadonly.value &&
    form.value.codice.trim() !== '' &&
    form.value.descrizione.trim() !== '' &&
    form.value.tipo != null &&
    form.value.soggetto_ruolo_conto_bancario_id != null,
)

const { opzioniTipoCanale } = useEtichettePagamenti()
const opzioniTipo = opzioniTipoCanale()

// ⭐ IBAN, utility e «predefinito» sulla stessa riga: sono le tre cose con cui
//    si riconosce il conto giusto fra due che si somigliano.
// ⚠️ `conto_utility_descrizione` e' NULL in DUE casi legittimi (conto generico
//    del ruolo, oppure istanza senza PDP): a video NULL non e' un buco, e'
//    «nessuna utility» — e va detto a parole.
function etichettaConto(c) {
  const parti = [c.iban || t('pagamenti.canali.conto_senza_iban')]
  parti.push(c.conto_utility_descrizione || t('pagamenti.canali.conto_senza_utility'))
  if (c.predefinito) parti.push(t('pagamenti.canali.conto_predefinito'))
  return parti.join(' · ')
}

const filialeAc = useServerAutocomplete((query) => lookupBankBranches(query), {
  minLength: 2,
})

function etichettaFiliale(f) {
  if (!f) return ''
  if (typeof f === 'string') return f
  // ⚠️ Fail-visible: su un canale gia' configurato il dettaglio potrebbe non
  //    portare il nome (filiale disattivata, o cancellata dall'anagrafica). Si
  //    mostra l'id, che dice «c'e' un valore e non so leggerlo» — mai il vuoto,
  //    che direbbe «non c'e' filiale» su un canale BANCA dove e' obbligatoria.
  if (!f.filiale_nome) return f.id != null ? `#${f.id}` : ''
  return f.bank_code ? `${f.filiale_nome} (${f.bank_code})` : f.filiale_nome
}

// Scopo: carica i conti agganciabili dell'emittente scelto.
// ⚠️ `precedente` non e' un dettaglio: distingue il PRIMO caricamento (apertura
//    del drawer, dove l'emittente si deriva dal canale) da un cambio VOLUTO. Il
//    conto si azzera solo nel secondo caso — azzerarlo anche nel primo
//    cancellerebbe in silenzio il conto di un canale gia' configurato, ogni
//    volta che quel conto non e' piu' fra gli agganciabili.
// Scopo: il conto scelto e' fra quelli che l'elenco propone?
// ⚠️ Una sede sola: la risposta serve a DUE cose che devono restare d'accordo —
//    azzerare la scelta al cambio di emittente, e dire a video che il conto
//    configurato non e' piu' proponibile. Due copie della stessa domanda
//    finirebbero per rispondere in modo diverso.
function contoNellElenco() {
  return conti.value.some(
    (c) => c.soggetto_ruolo_conto_bancario_id === form.value.soggetto_ruolo_conto_bancario_id,
  )
}

watch(soggettoRuoloEmittente, async (id, precedente) => {
  azzeraConti()
  if (id == null) return
  await caricaConti(id)
  // ⚠️ Cambiato emittente, il conto scelto prima NON e' piu' proponibile: e'
  //    di un altro perimetro. Si azzera, tranne quando e' ancora nell'elenco.
  if (precedente == null) return
  if (!contoNellElenco()) form.value.soggetto_ruolo_conto_bancario_id = null
})

// ⛔ Il conto configurato che NON e' piu' fra gli agganciabili (scaduto,
//    bloccato, o passato a un altro uso). Il Select lo mostrerebbe vuoto, cioe'
//    direbbe «questo canale non ha conto» di un canale che ne ha uno — e il
//    conto e' il perimetro dei soldi. Si dice, e non si tocca da soli.
const contoFuoriElenco = computed(
  () =>
    form.value.soggetto_ruolo_conto_bancario_id != null &&
    contiCaricati.value &&
    !erroreConti.value &&
    !contoNellElenco(),
)

// ⛔ Il tipo governa DUE campi in esclusiva, e il database lo pretende: fuori
//    da BANCA la filiale dev'essere NULL, fuori da PSP il soggetto anche.
//    Lasciarli valorizzati produrrebbe un rifiuto su un campo che a video non
//    si vede nemmeno piu'.
watch(() => form.value.tipo, (tipo) => {
  if (tipo !== TIPO_CANALE_CON_FILIALE) {
    form.value.bank_branch_id = null
    filialeObj.value = null
  }
  if (tipo !== TIPO_CANALE_PSP) {
    form.value.soggetto_ruolo_id = null
    soggettoPspObj.value = null
  }
})

function onFilialeSelect(evento) {
  filialeObj.value = evento.value
  form.value.bank_branch_id = evento.value?.id ?? null
}

function onPspSelect(riga) {
  soggettoPspObj.value = riga
  form.value.soggetto_ruolo_id = riga?.soggetto_ruolo_id ?? null
}

// Scopo: apre il drawer — azzera in creazione, carica in modifica.
watch(() => [props.visible, props.canaleId], async ([vis]) => {
  if (!vis) return
  form.value = defaultForm()
  filialeObj.value = null
  soggettoPspObj.value = null
  azzeraConti()

  // ⚠️ Per l'admin l'elenco si carica lo stesso, ma per un altro motivo di
  //    prima: non per farlo scegliere: per tradurre la PK della sessione nel
  //    soggetto-ruolo (e in un nome). L'operatore ha entrambi nel profilo.
  if (isAdminMode.value) {
    // ⛔ Fino al 2026-10-23 era `.catch(() => {})`, «il toast lo alza
    //    l'interceptor»: l'interceptor di `core/api.js` non mostra toast.
    // ⭐ Toast E avviso sotto il campo (`emittentiError`) non sono un doppione:
    //    il toast dice il MOTIVO (il messaggio del backend) e sparisce;
    //    l'avviso resta e dice la CONSEGUENZA, cioe' perche' i conti non si
    //    possono scegliere.
    await execute(() => loadOptions())
  }
  soggettoRuoloEmittente.value = soggettoRuoloSessione.value

  if (!props.canaleId) { fissa(); return }
  const dati = await execute(() => getEnteIncasso(props.canaleId))
  if (dati === null) return
  const c = dati.ente_incasso || {}
  form.value = {
    codice: c.codice || '',
    descrizione: c.descrizione || '',
    tipo: c.tipo || null,
    attivo: c.attivo !== false,
    soggetto_ruolo_conto_bancario_id: c.soggetto_ruolo_conto_bancario_id ?? null,
    centro_riscossione_id: c.centro_riscossione_id ?? null,
    bank_branch_id: c.bank_branch_id ?? null,
    soggetto_ruolo_id: c.soggetto_ruolo_id ?? null,
    formato_flusso: c.formato_flusso || '',
  }
  filialeObj.value = c.bank_branch_id != null
    ? { id: c.bank_branch_id, filiale_nome: c.bank_branch_nome, bank_code: c.bank_branch_bank_code }
    : null
  soggettoPspObj.value = c.soggetto_ruolo_id != null
    ? {
        soggetto_ruolo_id: c.soggetto_ruolo_id,
        ragione_sociale_completa: c.soggetto_ragione_sociale,
      }
    : null
  // ⭐ L'emittente del canale si DERIVA dal conto (`conto_soggetto_ruolo_id`):
  //    e' l'unico posto in cui e' scritto, perche' sul canale non c'e'.
  //    ⚠️ L'assegnazione fa scattare il watch, che ricarica i conti: senza,
  //    la tendina in modifica sarebbe vuota accanto a un conto valorizzato.
  if (c.conto_soggetto_ruolo_id != null) {
    soggettoRuoloEmittente.value = c.conto_soggetto_ruolo_id
  }
  fissa()
})

async function onSave() {
  const payload = {
    codice: form.value.codice.trim(),
    descrizione: form.value.descrizione.trim(),
    tipo: form.value.tipo,
    attivo: form.value.attivo,
    soggetto_ruolo_conto_bancario_id: form.value.soggetto_ruolo_conto_bancario_id,
    // ⚠️ `null` esplicito e non chiave assente: in PATCH e' cio' che TOGLIE un
    //    valore rimasto da una configurazione precedente — ed e' l'unica forma
    //    che il `CHECK` della filiale accetta quando il tipo cambia.
    centro_riscossione_id: form.value.centro_riscossione_id ?? null,
    bank_branch_id: vuoleFiliale.value ? form.value.bank_branch_id : null,
    soggetto_ruolo_id: vuolePsp.value ? form.value.soggetto_ruolo_id : null,
    formato_flusso: form.value.formato_flusso?.trim() || null,
  }

  const esito = await execute(
    () => (isEdit.value
      ? aggiornaEnteIncasso(props.canaleId, payload)
      : creaEnteIncasso(payload)),
    {
      successMessage: t(isEdit.value
        ? 'pagamenti.canali.aggiornato'
        : 'pagamenti.canali.creato'),
    },
  )
  if (esito === null) return
  emit('salvato')
  emit('update:visible', false)
}
</script>

<template>
  <AppDrawer
    :visible="visible"
    :title="t('pagamenti.canali.titolo_singolare')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :width="DRAWER_WIDTH.STANDARD"
    :loading="loading || caricamentoConti"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
  >
    <div class="form-grid">
      <!-- ══ Che canale e' ══ -->
      <div class="app-drawer-section">
        <h4>{{ t('pagamenti.canali.sezione_identita') }}</h4>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('pagamenti.canali.col_codice') }}</label>
          <InputText
            v-model="form.codice"
            class="app-codice-input"
            :disabled="isReadonly"
            :invalid="campiErrati.includes('codice')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.canali.col_tipo') }}</label>
          <Select
            v-model="form.tipo"
            :options="opzioniTipo"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.canali.col_tipo')"
            :disabled="isReadonly"
            :invalid="campiErrati.includes('tipo')"
          />
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.canali.col_descrizione') }}</label>
        <InputText
          v-model="form.descrizione"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>

      <div class="form-field">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <Checkbox v-model="form.attivo" binary :disabled="isReadonly" input-id="canale-attivo" />
          <label for="canale-attivo">{{ t('pagamenti.canali.col_attivo') }}</label>
        </div>
      </div>

      <!-- ══ Dove atterra il denaro ══ -->
      <div class="app-drawer-section">
        <h4>{{ t('pagamenti.canali.sezione_conto') }}</h4>
      </div>

      <!-- ⭐ Perche' questa sezione conta piu' delle altre. Senza, «scegli un
           conto» sembra una formalita' anagrafica. -->
      <Message severity="secondary" :closable="false" size="small">
        {{ t('pagamenti.canali.perche_il_conto') }}
      </Message>

      <div class="form-field">
        <label>{{ t('pagamenti.canali.campo_emittente') }}</label>
        <!-- ⚠️ Nessuno sceglie qui: si mostra il perimetro e si dice DA DOVE
             viene — un campo bloccato senza motivo si legge come un difetto. -->
        <span>{{ emittenteMostratoLabel || '—' }}</span>
        <!-- ⚠️ Tre didascalie, perche' sono tre provenienze diverse e una sola
             frase ne mentirebbe due: in modifica l'emittente lo DERIVA il conto
             del canale, in creazione e' la sessione (admin) o il permesso
             (operatore). -->
        <small class="app-text-muted">
          {{ isEdit
            ? t('pagamenti.canali.emittente_dal_conto')
            : (isAdminMode
              ? t('pagamenti.canali.emittente_dalla_sessione')
              : t('pagamenti.canali.emittente_dal_permesso')) }}
        </small>
        <!-- ⛔ Un elenco emittenti non letto NON e' «nessun emittente»: senza
             questa riga il nome resterebbe vuoto, la tendina dei conti
             disabilitata, e non ci sarebbe niente a video che spieghi perche'
             il form non si puo' compilare. -->
        <Message v-if="isAdminMode && emittentiError" severity="warn" :closable="false" size="small">
          {{ t('pagamenti.canali.emittenti_non_letti') }}
        </Message>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.canali.campo_conto') }}</label>
        <Select
          v-model="form.soggetto_ruolo_conto_bancario_id"
          :options="conti"
          :option-label="etichettaConto"
          option-value="soggetto_ruolo_conto_bancario_id"
          :placeholder="t('pagamenti.canali.campo_conto_placeholder')"
          :disabled="isReadonly || !conti.length"
          :invalid="campiErrati.includes('soggetto_ruolo_conto_bancario_id')"
        />
        <!-- ⛔ Un elenco vuoto si DICHIARA, e col suo motivo: e' la condizione
             voluta da D5 — si fallisce alla configurazione, dove se ne accorge
             chi puo' rimediare. Un menu vuoto e muto sembra un guasto. -->
        <Message v-if="erroreConti" severity="warn" :closable="false" size="small">
          {{ t('pagamenti.canali.conti_non_letti') }}
        </Message>
        <Message
          v-else-if="contiCaricati && nessunConto"
          severity="info"
          :closable="false"
          size="small"
        >
          {{ t('pagamenti.canali.nessun_conto_di_incasso') }}
        </Message>
        <Message v-else-if="contoFuoriElenco" severity="warn" :closable="false" size="small">
          {{ t('pagamenti.canali.conto_fuori_elenco') }}
        </Message>
      </div>

      <!-- ══ Riferimenti ══ -->
      <div class="app-drawer-section">
        <h4>{{ t('pagamenti.canali.sezione_riferimenti') }}</h4>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.canali.col_centro') }}</label>
        <LookupSelect
          v-model="form.centro_riscossione_id"
          rel="pagamenti.centri_riscossione"
          :placeholder="t('pagamenti.canali.campo_centro_placeholder')"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('centro_riscossione_id')"
          show-clear
        />
      </div>

      <!-- ⚠️ La filiale compare SOLO su BANCA, ed e' obbligatoria li'. Altrove
           il database la vuole NULL: mostrarla sarebbe offrire un campo che
           fara' fallire il salvataggio. -->
      <div v-if="vuoleFiliale" class="form-field">
        <label>{{ t('pagamenti.canali.campo_filiale') }}</label>
        <AutoComplete
          :model-value="filialeObj"
          :suggestions="filialeAc.suggestions.value"
          :loading="filialeAc.loading.value"
          :option-label="etichettaFiliale"
          :placeholder="t('pagamenti.canali.campo_filiale_placeholder')"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('bank_branch_id')"
          force-selection
          dropdown
          @complete="filialeAc.onSearch"
          @item-select="onFilialeSelect"
        />
        <small class="app-text-muted">{{ t('pagamenti.canali.filiale_obbligatoria') }}</small>
      </div>

      <!-- ⚠️ Il soggetto PSP e' l'ALTRO `soggetto_ruolo_id`: non c'entra con
           l'emittente scelto sopra. Compare solo su PSP, dove il guard del
           database lo pretende. -->
      <div v-if="vuolePsp" class="form-field">
        <label>{{ t('pagamenti.canali.campo_psp') }}</label>
        <SoggettoRuoloLookup
          :model-value="soggettoPspObj"
          :tipo-ruolo="TIPO_RUOLO.PSP"
          :placeholder="t('pagamenti.canali.campo_psp_placeholder')"
          :disabled="isReadonly"
          @update:model-value="onPspSelect"
        />
        <small class="app-text-muted">{{ t('pagamenti.canali.psp_obbligatorio') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.canali.col_formato_flusso') }}</label>
        <InputText v-model="form.formato_flusso" :disabled="isReadonly" />
        <small class="app-text-muted">{{ t('pagamenti.canali.formato_flusso_aiuto') }}</small>
      </div>
    </div>
  </AppDrawer>
</template>
