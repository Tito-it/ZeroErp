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
import DocumentoDrawerHost from './vendite/_shared/documenti/DocumentoDrawerHost.vue'
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

  <ConfirmDialog />
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
  gap: var(--app-gap-sm, 0.5rem);
  width: 100%;
}

.app-toast-azioni-testo {
  font-weight: 500;
}

/* `wrap`: i bersagli possono essere fino a cinque, e su schermi stretti
   andrebbero fuori dal riquadro. */
.app-toast-azioni-pulsanti {
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-gap-sm, 0.5rem);
}
</style>
