<!--
  SPDX-License-Identifier: GPL-3.0-or-later
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
import {
  useEmittenteFiscaleField,
  formatEmittenteOptionLabel,
} from '../../core/composables/useEmittenteFiscaleField'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { useServerAutocomplete } from '../../core/composables/useServerAutocomplete'
import { DRAWER_WIDTH } from '../../core/constants'
import { lookupBankBranches } from '../../anagrafiche/api/anagrafiche'
import {
  aggiornaEnteIncasso,
  creaEnteIncasso,
  getEnteIncasso,
  listContiIncasso,
} from '../api/pagamenti'
import { useEtichettePagamenti } from '../etichette'
import { RUOLO_PSP, TIPO_CANALE_CON_FILIALE, TIPO_CANALE_PSP } from '../vocabolari'

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
  isAdminMode, currentEmittente, emittentiOptions, emittentiError, loadOptions,
} = useEmittenteFiscaleField()

const isEdit = computed(() => props.canaleId != null)

// ── il filtro dell'emittente: sceglie QUALI conti si vedono ────────
// ⚠️ Per l'operatore non e' una scelta: e' il suo perimetro. Per l'admin
//    globale lo e', ed e' l'unico modo che ha di configurare il canale di una
//    delle due partite IVA senza vedere i conti dell'altra.
const soggettoRuoloEmittente = ref(null)

// ⚠️ Le opzioni senza `soggetto_ruolo_id` si scartano: senza quel valore la
//    tendina dei conti non si puo' nemmeno chiedere, e proporle darebbe una
//    voce che non fa niente.
const opzioniEmittente = computed(() =>
  (emittentiOptions.value || []).filter((e) => e.soggetto_ruolo_id != null),
)

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

  if (isAdminMode.value) {
    // L'admin globale sceglie: l'elenco degli emittenti gli serve davvero.
    await loadOptions().catch(() => { /* il toast lo alza l'interceptor */ })
    soggettoRuoloEmittente.value = null
  } else {
    // ⭐ L'operatore non sceglie: il suo emittente e' un permesso, e il campo
    //    esiste solo per dirgli su quale perimetro sta configurando.
    soggettoRuoloEmittente.value = currentEmittente.value?.soggettoRuoloId ?? null
  }

  if (!props.canaleId) return
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
    :title="t(isEdit ? 'pagamenti.canali.titolo_modifica' : 'pagamenti.canali.titolo_nuovo')"
    :width="DRAWER_WIDTH.STANDARD"
    :loading="loading || caricamentoConti"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
    @cancel="emit('update:visible', false)"
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
        <Select
          v-if="isAdminMode"
          v-model="soggettoRuoloEmittente"
          :options="opzioniEmittente"
          option-value="soggetto_ruolo_id"
          :option-label="formatEmittenteOptionLabel"
          :placeholder="t('pagamenti.canali.campo_emittente_placeholder')"
          :disabled="isReadonly"
          filter
        />
        <!-- ⛔ Un elenco emittenti non letto NON e' «nessun emittente»: senza
             questa riga la tendina resterebbe vuota, quella dei conti
             disabilitata, e non ci sarebbe niente a video che spieghi perche'
             il form non si puo' compilare. -->
        <Message v-if="isAdminMode && emittentiError" severity="warn" :closable="false" size="small">
          {{ t('pagamenti.canali.emittenti_non_letti') }}
        </Message>
        <!-- ⚠️ L'operatore non sceglie: si mostra il suo perimetro, e si dice
             che e' un permesso — un campo bloccato senza motivo si legge come
             un difetto. -->
        <template v-else>
          <span>{{ currentEmittente?.ragioneSociale || '—' }}</span>
          <small class="app-text-muted">
            {{ t('pagamenti.canali.emittente_dal_permesso') }}
          </small>
        </template>
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
          :tipo-ruolo="RUOLO_PSP"
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
