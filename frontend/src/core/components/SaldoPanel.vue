<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL PANNELLO DEI SALDI — «questo documento e' a posto?», e la stessa
//        domanda a qualunque altro livello.
//
// ⛔ NON e' «il pannello della fattura»: e' il pannello della BASE (§2.7,
//    decisione di Tid del 2026-08-24), e la fattura e' il suo primo
//    consumatore. Ogni schermata sceglie QUALI numeri accendere con `mostra`;
//    ⛔ nessuna li rinomina e nessuna li ricalcola.
//
// ⭐ SUL DOCUMENTO SE NE ACCENDONO DUE, non tre (Q-6): il **residuo** in grande,
//    perche' e' la domanda che uno si fa, e **in lavorazione** in piccolo e solo
//    quando c'e'. ⛔ L'«incassato» resta fuori da quella schermata: risponde a
//    una domanda di tesoreria, non a «questa fattura e' a posto?».
//
// ⚠️ E i casi sono QUATTRO, non uno: non letto · non leggibile · letto e
//    **senza nessun movimento** · letto coi numeri. Il terzo e il quarto a video
//    si somigliano — un residuo pari al totale — ma dicono cose diverse:
//    «nessuno ha ancora pagato niente» e «ha pagato, e manca ancora tutto» non
//    sono la stessa frase. Li separa `has_movimenti`, che lo dice il database.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'

import { useSaldi } from '../composables/useSaldi'
import { formatCurrency } from '../utils/format'

const props = defineProps({
  // `LIVELLO.DOCUMENTO` | `LIVELLO.RATA` | (un giorno) `LIVELLO.CLIENTE`.
  livello: { type: String, required: true },
  riferimentoId: { type: [Number, null], default: null },
  // ⭐ Quali numeri accendere. Il default e' quello del documento (Q-6): chi ne
  //    vuole altri lo dichiara — ⛔ non li rinomina.
  mostra: { type: Array, default: () => ['residuo', 'in_lavorazione'] },
})

const { t } = useI18n()
const { saldo, caricato, errore, loading, leggi, azzera, livelloSupportato, senzaMovimenti } =
  useSaldi(props.livello)

// ⚠️ `placeholder: '—'` e non stringa vuota: qui `null` significa «questo conto
//    non si applica», e una cella VUOTA si legge come un dato perso mentre il
//    trattino si legge come una risposta.
// 📮 E' la SECONDA occorrenza di questa coppia (l'altra e' `pagamenti/formato.js`):
//    la sede naturale sarebbe un `placeholder` di default in `formatCurrency`.
//    Dichiarato, non fatto di mia iniziativa — cambia il ripiego di tutto il
//    progetto.
const euro = (v) => formatCurrency(v, { placeholder: '—' })

const acceso = (campo) => props.mostra.includes(campo)

// ⭐ «Solo quando c'e'»: ne' `null` (il livello non lo sa) ne' zero (non c'e'
//    niente in mezzo). Un «in lavorazione: 0,00» accanto al residuo non spiega
//    niente e ruba spazio al numero che conta.
const inLavorazioneVisibile = computed(() => {
  if (!acceso('in_lavorazione') || !saldo.value) return false
  const v = saldo.value.in_lavorazione
  return v != null && Number(v) !== 0
})

// ⚠️ Acceso ma NON disponibile a questo livello (`incassato` sul documento: il
//    database da' due numeri e non tre). Si dice a parole: un trattino da solo
//    si legge come «zero», e questo numero non e' zero — non si sa.
const incassatoNonDisponibile = computed(
  () => acceso('incassato') && caricato.value && !errore.value
    && saldo.value?.incassato == null,
)

watch(
  () => props.riferimentoId,
  (id) => { if (id == null) azzera(); else leggi(id) },
  { immediate: true },
)
</script>

<template>
  <div class="saldo-panel">
    <!-- ⛔ Il livello che il frontend non sa ancora leggere si DICHIARA: e'
         previsto (il cliente) e non ancora acceso, e tacere lo farebbe
         sembrare un saldo a zero. -->
    <Message v-if="!livelloSupportato" severity="secondary" :closable="false" size="small">
      {{ t('core.saldi.livello_non_pronto') }}
    </Message>

    <!-- ⚠️ Il fallimento si dice: senza, «non l'ho letto» si legge come
         «non deve niente», che e' la conclusione opposta. -->
    <Message v-else-if="errore" severity="warn" :closable="false" size="small">
      {{ t('core.saldi.non_letto') }}
    </Message>

    <div v-else-if="loading && !caricato" class="app-loading">
      <i class="pi pi-spin pi-spinner" />
    </div>

    <template v-else-if="caricato && saldo">
      <div class="saldo-panel__numeri">
        <div v-if="acceso('residuo')" class="saldo-panel__principale">
          <span class="saldo-panel__etichetta">{{ t('core.saldi.residuo') }}</span>
          <span class="saldo-panel__valore">{{ euro(saldo.residuo) }}</span>
        </div>

        <!-- ⭐ In piccolo, e col PERCHE' accanto: chi vede un residuo che non
             cala vuole sapere che i soldi ci sono ma non sono registrati. -->
        <div v-if="inLavorazioneVisibile" class="saldo-panel__secondario">
          <span class="saldo-panel__etichetta">{{ t('core.saldi.in_lavorazione') }}</span>
          <span>{{ euro(saldo.in_lavorazione) }}</span>
          <small class="app-text-muted">{{ t('core.saldi.in_lavorazione_aiuto') }}</small>
        </div>

        <div
          v-if="acceso('incassato') && !incassatoNonDisponibile"
          class="saldo-panel__secondario"
        >
          <span class="saldo-panel__etichetta">{{ t('core.saldi.incassato') }}</span>
          <span>{{ euro(saldo.incassato) }}</span>
        </div>
      </div>

      <small v-if="incassatoNonDisponibile" class="app-text-muted">
        {{ t('core.saldi.incassato_non_disponibile') }}
      </small>

      <!-- ⛔ QUATTRO casi, non uno. Questo e' quello che si confonde piu'
           facilmente col residuo pieno: nessuno ha ancora pagato niente. -->
      <small v-if="senzaMovimenti" class="app-text-muted">
        {{ t('core.saldi.nessun_movimento') }}
      </small>
    </template>
  </div>
</template>

<style scoped>
/* Stili PROPRI e non classi prese in prestito: `app-dash-stat-n` esiste ed e'
 * grande al punto giusto, ma nasce per le card della lente Competenza —
 * prendere il nome di un'altra idea e' il modo in cui due cose diverse
 * finiscono per sembrare la stessa. I colori restano i token del tema. */
.saldo-panel {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.saldo-panel__numeri {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.25rem 1.5rem;
}

.saldo-panel__principale {
  display: flex;
  flex-direction: column;
}

.saldo-panel__valore {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--app-text-color);
  /* Cifre a larghezza fissa: due importi incolonnati si confrontano a colpo
   * d'occhio solo se le cifre non ballano. */
  font-variant-numeric: tabular-nums;
}

.saldo-panel__secondario {
  display: flex;
  flex-direction: column;
  font-variant-numeric: tabular-nums;
}

.saldo-panel__etichetta {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
</style>
