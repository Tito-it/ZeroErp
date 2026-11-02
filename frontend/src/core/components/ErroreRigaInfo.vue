<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: ⭐ L'ERRORE RESTA ATTACCATO ALLA RIGA. Icona «i» rossa accanto al
// documento che ha fallito; il click apre il messaggio per intero — codice,
// testo e quando è successo.
//
// ⭐ IL PROBLEMA CHE RISOLVE (rilievo di Tid, 2026-08-21). Un fallimento in un
// giro a lotti si annunciava con un toast e poi non esisteva più da nessuna
// parte: chi tornava sul lotto dieci minuti dopo vedeva una riga marcata
// «ERRORE» e nessun modo di sapere PERCHÉ. È la forma dei gestionali a lotti da
// sempre — la testata segnala che nel dettaglio c'è un errore grave, la riga
// dice quale — e mancava solo il lato che si legge.
//
// PERCHÉ UN'ICONA E NON UNA COLONNA DI TESTO: il messaggio di un errore
// applicativo è lungo (il nostro cita numeri di documento e la via d'uscita) e
// in una cella diventerebbe illeggibile o troncato — cioè un messaggio che c'è
// e non si può usare. L'icona costa una colonna stretta e non toglie niente al
// resto della riga.
//
// ⚠️ È UN `Button`, non un `<i>` con `@click`: hit-area, focus da tastiera e
// ruolo semantico corretti (stessa regola dei chip di `DocumentoCollegamentiBar`).
//
// ⚠️ `severity="danger"` e non un colore scritto a mano: il rosso di questo
// tema arriva da lì (memoria feedback_css_centralizzazione).
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Tag from 'primevue/tag'
import { displayTimestamp } from '../utils/date'
import BersaglioAzioni from './BersaglioAzioni.vue'
import { STATUS_ICONS } from '../constants'

const props = defineProps({
  // Il messaggio dell'errore. Assente/vuoto = niente icona: la riga non ha
  // nulla da raccontare e non deve portare un segnale muto.
  messaggio: { type: String, default: null },
  // Codice applicativo (`E_*`). Mostrato com'è: è la chiave con cui si cerca
  // nel diario e con cui si parla al team DB — tradurlo lo renderebbe
  // irrintracciabile.
  codice: { type: String, default: null },
  // Quando è successo (ISO). Un errore vecchio su una riga già rilavorata si
  // riconosce solo dalla data.
  quando: { type: String, default: null },
  // Titolo del pannello; il default parla di un documento generico.
  titolo: { type: String, default: null },
  // ⭐ Livello della segnalazione (`C` critico · `W` avviso · `I` attenzione).
  // Senza, l'icona sarebbe rossa anche su un avviso — direbbe «errore» dove
  // errore non c'e', ed e' proprio la distinzione che il colore deve portare.
  // Assente o sconosciuto → si assume il caso piu' grave: una segnalazione che
  // non sa dire quanto pesa e' meglio mostrarla forte che sottovoce.
  livello: { type: String, default: null },
  // ⭐ IL BERSAGLIO dell'errore: su QUALE cosa è successo, nella forma
  // `[{type, id}]` che il backend persiste in `fatture_log.meta.bersagli` e
  // rende come `errore_bersagli` nella riga.
  //
  // ⭐ PERCHÉ QUI, ed è il caso che conta più del toast (2026-08-24). Un giro di
  // fatturazione può partire da solo — worker, batch notturno — e fallire
  // quando davanti allo schermo non c'è nessuno: chi legge quell'errore lo
  // legge ORE DOPO, da questa icona. È esattamente «l'operatore cinque minuti
  // dopo, che sta rimediando» del brief. Il toast è il caso facile.
  //
  // ⚠️ Assente o irraggiungibile → nessun pulsante, e il messaggio resta quello
  // di prima: il bersaglio è un'offerta, non una promessa. Mai un pulsante che
  // porta in un vicolo cieco.
  bersagli: { type: Array, default: () => [] },
  // ⭐ L'ENTITA' DI QUESTA RIGA — `{tipo, id}`. Dal `T-3b` (2026-08-24) il
  // bersaglio porta anche il documento **su cui** l'errore e' successo, che qui
  // e' la riga stessa: un pulsante «apri» verso di lei direbbe «vai dove sei
  // gia'». Lo filtra `BersaglioAzioni`; questo componente lo trasporta e basta.
  //
  // ⚠️ Assente = nessun filtro. E' la scelta prudente: un pulsante di troppo si
  // vede, uno nascosto per sbaglio no.
  entitaCorrente: { type: [Object, null], default: null },
})

const { t } = useI18n()
const popover = ref(null)

// ⭐ L'ICONA COMPARE SE C'E' QUALCOSA DA RACCONTARE — una frase OPPURE un
// codice. ⚠️ Fino al 2026-09-06 guardava il solo `messaggio`, e su una riga con
// il codice ma senza frase non compariva niente: la riga si leggeva SANA mentre
// un tentativo era fallito. È esattamente il difetto per cui esiste il cantiere
// dell'esito di gruppo, ricreato un piano più su.
// ⛔ E il modello lo AMMETTE, non è un caso di scuola: il CHECK
// `chk_lotti_gruppi_errore_parlante` pretende «almeno uno dei due» — codice o
// frase — quindi una riga in errore con la sola causa è una riga legittima.
// Che oggi chi scrive li valorizzi entrambi non cambia la regola: un guard non
// si restringe perché il ramo oggi è irraggiungibile.
// ⚠️ Resta il caso in cui NON compare, ed è quello giusto: nessuno dei due. Lì
// la riga non ha davvero niente da dire, e un'icona sarebbe un segnale muto.
const haErrore = computed(
  () => Boolean(String(props.messaggio ?? '').trim())
    || Boolean(String(props.codice ?? '').trim()),
)

// La scala dei livelli del diario (`fatture_log.status`) tradotta nelle
// severity PrimeVue: stesso vocabolario di `SelectButtonGravita` e dei Tag.
const SEVERITY_PER_LIVELLO = { C: 'danger', W: 'warn', I: 'info' }
const severita = computed(() => SEVERITY_PER_LIVELLO[props.livello] || 'danger')

// L'icona segue il livello: triangolo per critico e avviso (c'e' qualcosa che
// non va), «i» per l'attenzione (c'e' qualcosa da sapere).
const icona = computed(
  () => (props.livello === 'I' ? STATUS_ICONS.INFO : STATUS_ICONS.ERRORE),
)

function toggle(event) {
  popover.value?.toggle(event)
}

// Dopo aver agito il popover si chiude: resterebbe aperto davanti alla cosa
// che ha appena aperto. ⭐ Lo dice il componente dei pulsanti con `@eseguita`,
// cosi' la regola sta in un posto solo per tutte le superfici.
function chiudiPopover() {
  popover.value?.hide()
}
</script>

<template>
  <Button
    v-if="haErrore"
    type="button"
    text
    rounded
    size="small"
    :severity="severita"
    :icon="icona"
    :aria-label="t('common.errore_riga_vedi')"
    v-tooltip.top="t('common.errore_riga_vedi')"
    class="app-errore-riga-btn"
    @click="toggle"
  />

  <Popover v-if="haErrore" ref="popover" :style="{ width: '460px' }">
    <h4>{{ titolo || t('common.errore_riga_titolo') }}</h4>
    <div class="app-errore-riga-meta">
      <Tag v-if="codice" :value="codice" :severity="severita" />
      <span v-if="quando" class="app-errore-riga-quando">{{ displayTimestamp(quando) }}</span>
    </div>
    <!-- `white-space: pre-line`: i messaggi del database vanno a capo da soli
         (DETAIL e HINT su righe proprie), e schiacciarli in un paragrafo unico
         toglierebbe proprio la separazione fra «cos'è successo» e «cosa fare». -->
    <!-- ⚠️ Il paragrafo si rende solo se la frase c'è: con il solo codice, il
         Tag qui sopra è già tutto ciò che si sa, e un paragrafo vuoto
         lascerebbe un buco che sembra un caricamento mancato. -->
    <p v-if="messaggio" class="app-errore-riga-testo">{{ messaggio }}</p>

    <!-- Il GESTO, quando c'è dove andare. Sotto il messaggio e non accanto al
         titolo: prima si legge cosa è successo, poi si decide di muoversi. -->
    <BersaglioAzioni
      class="app-errore-riga-azioni"
      :bersagli="bersagli"
      :entita-corrente="entitaCorrente"
      @eseguita="chiudiPopover"
    />
  </Popover>
</template>

<style scoped>
.app-errore-riga-btn {
  width: 2rem;
  height: 2rem;
}
.app-errore-riga-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.app-errore-riga-quando {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
.app-errore-riga-testo {
  margin: 0;
  white-space: pre-line;
  line-height: 1.45;
}
/* La disposizione dei pulsanti la porta `BersaglioAzioni`: qui resta solo lo
   stacco dal messaggio. */
.app-errore-riga-azioni {
  margin-top: 0.75rem;
}
</style>
