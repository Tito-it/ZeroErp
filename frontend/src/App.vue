<script setup>
// ⭐ QUI VIVONO LE TRE COSE GLOBALI: le notifiche, la conferma, e — dal
// 2026-08-24 — l'OSPITE DEL BERSAGLIO.
//
// Il bersaglio e' l'entita' su cui un errore e' successo (envelope
// `error.targets`): il toast lo trasforma in un gesto — «Apri la fattura 820» —
// e quel gesto deve poter aprire un drawer da QUALUNQUE schermata, comprese
// quelle che un `DocumentoDrawerHost` proprio non lo montano. Per questo
// l'ospite sta qui, uno solo, accanto al toast che lo comanda.
// Brief: docs/it/dev/work-in-progress/brief-db-bersaglio-errore.md §7-bis.
import Toast from 'primevue/toast'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import DocumentoDrawerHost from './core/components/DocumentoDrawerHost.vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_CHROME } from './core/constants'
import { TASTO, nomeTasto } from './core/utils/scorciatoie'
import { useUiStore } from './stores/ui'

// Scopo: ESC sulla radice della ConfirmDialog — ferma la risalita e chiude la
//        sola conferma (`instance.close()` = la via di PrimeVue: `onHide`).
//        Dentro una conferma non ci sono tendine: nessun controllo da fare.
// ⭐ E il tasto DETTO in testa (2026-10-11, Tid), come in `AppDialog`:
//    l'etichetta «Esc» in alto a destra, senza X. La ConfirmDialog non inoltra
//    lo slot `#header` al suo Dialog: l'etichetta e' il `::before` delle azioni
//    di testa (`data-tasto`, main.css `.app-dialog-tasto-css`), che un figlio
//    non lo possono ricevere da un `pt`. Assente su `ui.isCompatto`.
const { t, te } = useI18n()
const ui = useUiStore()
const confirmDialogPt = computed(() => ({
  root: ({ instance }) => ({
    onKeydown: (event) => {
      if (event.code !== 'Escape') return
      event.stopPropagation()
      if (DIALOG_CHROME.closeOnEscape) instance.close()
    },
  }),
  headerActions:
    DIALOG_CHROME.closeOnEscape && !ui.isCompatto
      ? { class: 'app-dialog-tasto-css', 'data-tasto': nomeTasto(t, te, TASTO.ESC) }
      : {},
}))
import {
  bersaglioDrawerVisible,
  bersaglioDrawerTipo,
  bersaglioDrawerId,
  onBersaglioDrawerVisible,
} from './core/bersaglioGesto'

// Scopo: esegue il gesto e chiude il toast. ⚠️ In quest'ordine e in una
//        funzione, non due istruzioni inline nel template: se `esegui` sollevasse
//        il toast resterebbe aperto davanti alla cosa che stava aprendo, e nel
//        template l'errore sarebbe invisibile.
function eseguiAzione(azione, chiudi) {
  try {
    azione.esegui()
  } finally {
    chiudi()
  }
}
</script>

<template>
  <Toast />

  <!--
    ⭐ IL TOAST CHE PORTA UN GESTO. Gruppo dedicato: il toast normale resta
    esattamente com'era, e solo gli errori con un bersaglio passano di qui.
    ⚠️ Persistente per costruzione (`life: 0` da `useNotify.errorConAzioni`): un
    pulsante che sparisce dopo cinque secondi non e' un gesto.
    ⚠️ `closeCallback` sui pulsanti: dopo aver agito il toast se ne va, o
    resterebbe aperto davanti alla cosa che ha appena aperto.
  -->
  <Toast group="azioni">
    <template #message="{ message, closeCallback }">
      <div class="app-toast-azioni">
        <span class="app-toast-azioni-testo">{{ message.summary }}</span>
        <!--
          ⭐ LA SOLUZIONE (2026-09-09): cosa fare adesso, dal catalogo del
          database (`error.hint`). Sta FRA il testo e i pulsanti perche' quello
          e' l'ordine del ragionamento — cosa e' successo → cosa fare → il
          pulsante che lo fa. ⚠️ Qui va scritta a mano: il gruppo `azioni` ha un
          template suo, quindi il `detail` che PrimeVue renderebbe da se' nel
          toast normale qui non lo rende nessuno.
        -->
        <span v-if="message.detail" class="app-toast-azioni-soluzione">{{ message.detail }}</span>
        <div class="app-toast-azioni-pulsanti">
          <Button
            v-for="(azione, i) in message.azioni"
            :key="i"
            :label="azione.label"
            :icon="azione.icon"
            size="small"
            severity="secondary"
            @click="eseguiAzione(azione, closeCallback)"
          />
        </div>
      </div>
    </template>
  </Toast>

  <!-- La ConfirmDialog globale (unica: `useConfirmAction` e' l'unico che la
       apre). ⚠️ `closable` sta QUI e non nel composable: PrimeVue 4 non la
       inoltra da `confirm.require` al Dialog, ma la ConfirmDialog eredita gli
       attributi (`inheritAttrs`) e li passa al Dialog radice — e' l'unico
       pezzo di chrome che vive sul tag. Il valore e' quello di DIALOG_CHROME:
       niente X, come su ogni AppDialog (decisione Tid, 2026-09-18).
       ⭐ ESC si gestisce sulla RADICE (`pt.root`), come in AppDialog: chiude
       solo la conferma e non arriva a `document`, dove il Drawer sotto si
       chiuderebbe insieme (rilievo di Tid, stesso giorno). `instance` e' il
       Dialog di PrimeVue che la ConfirmDialog renderizza. -->
  <ConfirmDialog :closable="DIALOG_CHROME.closable" :pt="confirmDialogPt" />
  <router-view />

  <!-- L'ospite del bersaglio: uno per tutta l'applicazione. -->
  <DocumentoDrawerHost
    :visible="bersaglioDrawerVisible"
    :tipo-codice="bersaglioDrawerTipo"
    :doc-id="bersaglioDrawerId"
    @update:visible="onBersaglioDrawerVisible"
  />
</template>

<style scoped>
/* Il testo sopra, i pulsanti sotto: la frase puo' essere lunga (i nostri
   messaggi citano numeri di documento e la via d'uscita) e affiancarla ai
   pulsanti la comprimerebbe proprio dove serve leggerla. */
.app-toast-azioni {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
  width: 100%;
}

.app-toast-azioni-testo {
  font-weight: 500;
}

/* La soluzione arretra rispetto al messaggio: sono due frasi con due ruoli, e
   la gerarchia dice quale si legge per prima. Stessa cosa che il tema Aura fa
   da se' su `summary`/`detail` nel toast normale — qui va ripetuta perche'
   questo gruppo ha un template suo.
   ⛔ Il peso e la dimensione, MAI `opacity`: la regola sta in
   frontend-standards §«Glifo vs controllo» — l'opacita' si somma ai veli dei
   contenitori e smorza anche cio' che resta da leggere. E nemmeno un colore
   scritto qui: il toast d'errore porta il proprio, e sovrascriverlo per un
   figlio vorrebbe dire indovinare il contrasto su due temi. */
.app-toast-azioni-soluzione {
  font-size: var(--app-font-size-sm);
}

/* `wrap`: i bersagli possono essere fino a cinque, e su schermi stretti
   andrebbero fuori dal riquadro. */
.app-toast-azioni-pulsanti {
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-space-sm);
}
</style>
