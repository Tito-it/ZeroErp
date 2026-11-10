<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CONFERMA DELLA CHIUSURA DI UN LEGAME DI DISTINTA CHE HA PREZZI
//        BUNDLE (BE19 di brief-db-revisione-catalogo, giro 3; Q19-Q22 di Tid).
//        Un prezzo bundle vale solo finche' il componente e' nel kit: chiudere
//        il legame chiude (o, in una bozza, toglie) anche i prezzi che vanno
//        oltre la fine, e da quel giorno il kit in quei listini costa meno.
//        Per decisione di Tid non succede in silenzio.
// ⭐ Il giro e' quello di `useForzaturaConfermata` (il chiamante lo possiede),
//    come l'annullo con legami (`DocumentoAnnulloLegamiDialog`): 1° tentativo
//    senza dichiarazione -> il DB rifiuta (E_BOM_CHIUSURA_CON_PREZZI,
//    `confirm_and_retry`) -> qui si elencano i prezzi -> la conferma DICHIARA
//    quanti se ne sono visti (`prezzi_confermati`). Se nel frattempo sono
//    cambiati il DB chiede di nuovo: arriva una `domanda` NUOVA e l'elenco si
//    rilegge.
// ⛔ Il numero dichiarato e' quello LETTO qui (`GET …/chiusura/`), mai un valore
//    preso dal messaggio: dichiarare cio' che non si e' visto svuoterebbe la
//    conferma. Se nel frattempo i prezzi sono spariti si legge ZERO, e la
//    conferma ripete SENZA dichiarazione: il legame senza prezzi il DB lo
//    chiude al primo colpo.
// ⚠️ Un prezzo di un listino che l'operatore non vede arriva con
//    `nel_perimetro = false` e nient'altro: si dice che c'e', non quale.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'

import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { formatCurrency } from '../../core/utils/format'
import { displayDate } from '../../core/utils/date'
import { getChiusuraArticoloComponente } from '../api/catalogo'

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null },
  // Il legame da chiudere e la fine scelta (ISO): sono quelli della chiamata
  // in sospeso, e la finestra rilegge i prezzi per QUELLA data.
  componenteId: { type: [String, null], default: null },
  validoAl: { type: [String, null], default: null },
  // Il nome dell'azione che ha aperto la finestra: titolo e pulsante dicono la
  // stessa parola del gesto («Chiudi riga», «Duplica come nuova versione»).
  header: { type: String, required: true },
  // La domanda in sospeso di `useForzaturaConfermata` (`{ messaggio }`): una
  // domanda nuova = rileggere.
  domanda: { type: [Object, null], default: null },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['conferma', 'cancel'])

const { t } = useI18n()
const { execute, loading: caricamento } = useApiHandler()

const dati = ref(null)

// ⚠️ La risposta vale solo per la domanda che l'ha chiesta: una risposta
//    arrivata dopo una domanda nuova (o a finestra chiusa) si scarta.
watch(() => props.domanda, async (domanda) => {
  dati.value = null
  if (!domanda || !props.componenteId || !props.validoAl) return
  const letti = await execute(
    () => getChiusuraArticoloComponente(props.articoloId, props.componenteId, props.validoAl),
  )
  if (props.domanda === domanda) dati.value = letti
}, { immediate: true })

const righe = computed(() => dati.value?.righe ?? [])
const senzaPrezzi = computed(() => dati.value != null && dati.value.prezzi === 0)
const nascosti = computed(() => righe.value.filter((r) => !r.nel_perimetro).length)
const visibili = computed(() => righe.value.filter((r) => r.nel_perimetro))

// Scopo: la riga di un prezzo: listino e versione (con lo stato), periodo,
//        prezzo del componente e quanto pesa su un kit.
function descrizione(r) {
  return t('catalogo.chiusura_prezzi.riga', {
    listino: r.listino_codice,
    versione: r.codice_versione,
    stato: r.stato_versione,
    dal: displayDate(r.valido_dal),
    al: r.valido_al ? displayDate(r.valido_al) : t('catalogo.chiusura_prezzi.senza_fine'),
    prezzo: formatCurrency(r.prezzo),
    kit: formatCurrency(r.importo_per_kit),
  })
}

// Scopo: che cosa succede al prezzo. ⚠️ `labelKey` LETTERALI: e' la forma che
//        `scripts/check_i18n_keys.py` sa verificare.
const ESITO_LABEL = {
  CHIUDE: 'catalogo.chiusura_prezzi.esito_chiude',
  TOGLIE: 'catalogo.chiusura_prezzi.esito_toglie',
  BLOCCA: 'catalogo.chiusura_prezzi.esito_blocca',
}
const esito = (r) => (ESITO_LABEL[r.esito] ? t(ESITO_LABEL[r.esito]) : r.esito)

function onConferma() {
  emit('conferma', senzaPrezzi.value ? {} : { prezzi_confermati: dati.value.prezzi })
}
</script>

<template>
  <!-- conferma-uscita: nessuna — non ci sono campi: si conferma o si rinuncia. -->
  <AppDialog
    :visible="visible"
    :header="header"
    width="md"
    :loading="loading || caricamento"
    :save-disabled="!dati"
    :save-label="header"
    save-severity="danger"
    @save="onConferma"
    @cancel="emit('cancel')"
  >
    <div class="form-grid">
      <!-- La frase del DB: nomina gia' componente, kit e numeri. -->
      <Message v-if="!senzaPrezzi" severity="warn" :closable="false">{{ domanda?.messaggio }}</Message>
      <!-- La frase del DB non vale piu': i prezzi che contava non ci sono. -->
      <Message v-else severity="info" :closable="false">
        {{ t('catalogo.chiusura_prezzi.nessun_prezzo') }}
      </Message>

      <div v-if="righe.length" class="form-field">
        <label>{{ t('catalogo.chiusura_prezzi.prezzi') }}</label>
        <ul class="app-chiusura-prezzi-lista">
          <li v-for="(r, i) in visibili" :key="r.riga_id ?? i">
            {{ descrizione(r) }} · <strong>{{ esito(r) }}</strong>
          </li>
          <li v-if="nascosti">{{ t('catalogo.chiusura_prezzi.fuori_perimetro', { n: nascosti }) }}</li>
        </ul>
      </div>

      <small v-if="!senzaPrezzi" class="app-field-hint">
        {{ t('catalogo.chiusura_prezzi.spiegazione') }}
      </small>
    </div>
  </AppDialog>
</template>

<style scoped>
.app-chiusura-prezzi-lista {
  margin: 0;
  padding-left: 1.25rem;
}
</style>
