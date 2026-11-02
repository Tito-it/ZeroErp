<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
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

import { CAMPI_SALDO, LIVELLO, useSaldi } from '../composables/useSaldi'
import { formatCurrency } from '../../core/utils/format'

import { STATUS_ICONS } from '../../core/constants'
const props = defineProps({
  // `LIVELLO.DOCUMENTO` | `LIVELLO.RATA` | (un giorno) `LIVELLO.CLIENTE`.
  livello: {
    type: String,
    required: true,
    validator: (v) => Object.values(LIVELLO).includes(v),
  },
  riferimentoId: { type: [Number, null], default: null },
  // ⭐ «Prima di se'» (D19-b): la riga contabile da NON contare, per chi la sta
  //    correggendo. Rata e — dal 2026-09-18, P-6 — documento la sanno
  //    applicare; dove un livello non la sa fare il pannello lo DICE invece di
  //    fingere: un «in lavorazione» che include la riga che si sta cambiando
  //    non e' sbagliato, e' un numero che va letto sapendolo.
  escludiRigaId: { type: [Number, null], default: null },
  // ⭐ Quali numeri accendere. Il default e' quello del documento (Q-6): chi ne
  //    vuole altri lo dichiara — ⛔ non li rinomina.
  // ⚠️ Il `validator` non e' pignoleria: un nome sbagliato qui non da' errore,
  //    da' una RIGA IN MENO — cioe' un numero che sparisce da un pannello di
  //    saldi senza che niente lo dica.
  // ⛔ I due nomi per esteso, NON `CAMPI_SALDO[0], [1]`: indicizzare per
  //    posizione legherebbe il default all'ORDINE di una lista che il commento
  //    accanto dichiara intoccabile — e un riordino cambierebbe in silenzio
  //    quali numeri si accendono. La lista presidia i nomi (il `validator`), non
  //    li sostituisce.
  mostra: {
    type: Array,
    default: () => ['residuo', 'in_lavorazione'],
    validator: (v) => v.every((c) => CAMPI_SALDO.includes(c)),
  },
})

const { t } = useI18n()
// ⚠️ Il livello si legge UNA VOLTA (vedi `useSaldi`): il lettore si sceglie al
//    montaggio e non cambia. Chi deve cambiarlo rimonta il componente con
//    `:key="livello"`.
const livelloMontato = props.livello
const {
  saldo, caricato, errore, loading, leggi, azzera,
  livelloSupportato, esclusioneSupportata, senzaMovimenti,
} = useSaldi(livelloMontato)

// L'esclusione e' stata CHIESTA e il livello non la sa fare: si dichiara.
// ⭐ Dal 2026-09-18 nessun livello vivo ci finisce piu' (P-6: anche il
//    documento esclude). ⛔ Il ramo resta, come `incassatoNonDisponibile`: e' la
//    risposta a un caso che il modello ammette — il CLIENTE, che nascera'
//    sommando documenti — non a uno che oggi capita.
const esclusioneNonApplicata = computed(
  () => props.escludiRigaId != null && !esclusioneSupportata,
)

// ⛔ E se il prop cambia SENZA `:key`, il pannello si spegne invece di mostrare
//    i numeri del livello vecchio. Fino a oggi quel caso era solo scritto in un
//    commento del composable: un contratto che nessuno presidia e' una regola
//    che qualcuno infrangera' — e qui l'infrazione non darebbe un errore, darebbe
//    il saldo di un'ALTRA cosa sotto l'etichetta giusta.
const livelloDivergente = computed(() => props.livello !== livelloMontato)

const acceso = (campo) => props.mostra.includes(campo)

// ⭐ «Solo quando c'e'»: ne' `null` (il livello non lo sa) ne' zero (non c'e'
//    niente in mezzo). Un «in lavorazione: 0,00» accanto al residuo non spiega
//    niente e ruba spazio al numero che conta.
const inLavorazioneVisibile = computed(() => {
  if (!acceso('in_lavorazione') || !saldo.value) return false
  const v = saldo.value.in_lavorazione
  return v != null && Number(v) !== 0
})

// ⚠️ Acceso ma NON disponibile a questo livello. Si dice a parole: un trattino
//    da solo si legge come «zero», e questo numero non e' zero — non si sa.
// ⭐ Dal 2026-08-29 nessun livello vivo ci finisce piu': documento e rata
//    rispondono entrambi tutti e tre i numeri (DB-10, raccolta dal backend il
//    29/08). ⛔ Il ramo resta perche' e' la RISPOSTA a un caso che il modello
//    ammette, non a uno che oggi capita: un livello che non sa dire l'incassato
//    e' previsto — il CLIENTE, finche' somma solo documenti — e un presidio non
//    si toglie perche' oggi il suo ramo e' irraggiungibile.
const incassatoNonDisponibile = computed(
  () => acceso('incassato') && caricato.value && !errore.value
    && saldo.value?.incassato == null,
)

// ⚠️ Anche `escludiRigaId` fa rileggere: e' parte della domanda, non un
//    dettaglio della risposta.
watch(
  () => [props.riferimentoId, props.escludiRigaId],
  ([id, escludiRigaId]) => {
    if (id == null) azzera()
    else leggi(id, { escludiRigaId })
  },
  { immediate: true },
)
</script>

<template>
  <div class="saldo-panel">
    <!-- ⛔ Il livello che il frontend non sa ancora leggere si DICHIARA: e'
         previsto (il cliente) e non ancora acceso, e tacere lo farebbe
         sembrare un saldo a zero. -->
    <Message
      v-if="!livelloSupportato || livelloDivergente"
      severity="secondary"
      :closable="false"
      size="small"
    >
      {{ t('pagamenti.saldi.livello_non_pronto') }}
    </Message>

    <!-- ⚠️ Il fallimento si dice: senza, «non l'ho letto» si legge come
         «non deve niente», che e' la conclusione opposta. -->
    <Message v-else-if="errore" severity="warn" :closable="false" size="small">
      {{ t('pagamenti.saldi.non_letto') }}
    </Message>

    <div v-else-if="loading && !caricato" class="app-loading">
      <i :class="STATUS_ICONS.CARICAMENTO" />
    </div>

    <template v-else-if="caricato && saldo">
      <div class="saldo-panel__numeri">
        <div v-if="acceso('residuo')" class="saldo-panel__principale">
          <span class="saldo-panel__etichetta">{{ t('pagamenti.saldi.residuo') }}</span>
          <span class="saldo-panel__valore">{{ formatCurrency(saldo.residuo) }}</span>
        </div>

        <!-- ⭐ In piccolo, e col PERCHE' accanto: chi vede un residuo che non
             cala vuole sapere che i soldi ci sono ma non sono registrati. -->
        <div v-if="inLavorazioneVisibile" class="saldo-panel__secondario">
          <span class="saldo-panel__etichetta">{{ t('pagamenti.saldi.in_lavorazione') }}</span>
          <span>{{ formatCurrency(saldo.in_lavorazione) }}</span>
          <small class="app-text-muted">{{ t('pagamenti.saldi.in_lavorazione_aiuto') }}</small>
        </div>

        <div
          v-if="acceso('incassato') && !incassatoNonDisponibile"
          class="saldo-panel__secondario"
        >
          <span class="saldo-panel__etichetta">{{ t('pagamenti.saldi.incassato') }}</span>
          <span>{{ formatCurrency(saldo.incassato) }}</span>
        </div>
      </div>

      <small v-if="incassatoNonDisponibile" class="app-text-muted">
        {{ t('pagamenti.saldi.incassato_non_disponibile') }}
      </small>

      <!-- ⛔ QUATTRO casi, non uno. Questo e' quello che si confonde piu'
           facilmente col residuo pieno: nessuno ha ancora pagato niente. -->
      <small v-if="senzaMovimenti" class="app-text-muted">
        {{ t('pagamenti.saldi.nessun_movimento') }}
      </small>

      <!-- ⚠️ Chiesto di non contarsi addosso, e il livello non lo sa fare:
           lo si dice, perche' «in lavorazione» qui comprende la riga che
           l'operatore sta guardando. -->
      <small v-if="esclusioneNonApplicata" class="app-text-muted">
        {{ t('pagamenti.saldi.include_riga_corrente') }}
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
  color: var(--app-text-muted);
}
</style>
