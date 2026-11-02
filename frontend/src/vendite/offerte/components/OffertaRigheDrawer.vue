<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Sub-drawer delle righe di un'offerta commerciale — involucro del BB
//        `RigheEccezioniDrawer` (lista configurabile `vendite.offerta_righe`,
//        106, coi verbi del DB, e form inline di OVERRIDE/AGGIUNTA), gemello
//        di `ContrattoRigheDrawer`.
//
// ⭐ DAL 2026-10-05 (brief-db-righe-esclusione-solo-non-si-vende §8.1, regola
//    del 2 con ok Tid). Fino a quel giorno questo file era
//    `OffertaEccezioniDrawer`: una `DataTable` in memoria sulla tabella cruda
//    delle eccezioni, il tipo scelto in una tendina, l'ESCLUSIONE creata dal
//    form (vuota, poi in sola lettura) e il toggle «attivo». Ora le righe sono
//    quelle che il DB calcola — il listino con l'overlay delle eccezioni, piu'
//    le aggiunte — coi verbi della riga: «Escludi» nasce sulla riga del
//    listino, spento col motivo quando il guard lo rifiuterebbe (R-BE-7).
//    ⛔ Niente toggle «attivo» (decisione di Tid, 2026-10-05): la lista legge
//    le sole eccezioni attive, e un'eccezione spenta sarebbe sparita senza
//    modo di riaccenderla. Un'eccezione c'e' o si toglie (Ripristina/Rimuovi),
//    come sul contratto.
//
// Qui resta cio' che e' dell'OFFERTA: lo store della sua lista, le sue
// scritture e API dei componenti, l'intestazione, e il blocco dalla capability
// del DB (`can_edit_eccezioni`).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DrawerContextHeader from '../../../core/components/DrawerContextHeader.vue'
import RigheEccezioniDrawer from '../../_shared/righe/RigheEccezioniDrawer.vue'
import { TAB_ENTITIES } from '../../../core/constants'
import { displayDate } from '../../../core/utils/date'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import {
  previewEccezioneComponenti,
  listEccezioneComponenti,
  updateEccezioneComponente,
  deleteEccezioneComponente,
  exportRigheLista,
  listRigaErogazioni,
} from '../api/offerteApi'
import { useOfferteStore } from '../stores/offerte'
import { useOffertaRigheStore } from '../stores/offertaRighe'

const { t } = useI18n()
const store = useOfferteStore()

const props = defineProps({
  visible: Boolean,
  offertaId: { type: Number, required: true },
  // L'emittente dell'offerta (PK di `anagrafiche.emittenti_fiscali`): il
  // lasciapassare del cancello di perimetro della lista.
  emittenteFiscaleId: { type: Number, default: null },
  offertaCodice: { type: String, default: '' },
  offertaStatoCodice: { type: String, default: '' },
  // Le righe si scrivono: la capability `can_edit_eccezioni` del DB
  // (`script.fn_available_actions_offerta`), dal dettaglio dell'offerta.
  // Assente = falso: senza il si' del DB i verbi non si propongono.
  righeModificabili: { type: Boolean, default: false },
  offertaStatoDescrizione: { type: String, default: '' },
  offertaCliente: { type: String, default: '' },
  offertaValiditaDal: { type: String, default: null },
  offertaValiditaAl: { type: String, default: null },
})
const emit = defineEmits(['update:visible', 'changed'])

// Righe modificabili lo dice il DB (capability), non lo stato letto qui: la
// regola «solo in BOZZA» vive in `fn_available_actions_offerta` e nel guard
// `E_RIGA_DOC_NON_BOZZA`. Stringe la catena dei permessi. Stessa forma di
// `ContrattoRigheDrawer`.
const bloccato = computed(() => !props.righeModificabili)

// Lo store della lista: una istanza per drawer, nata nello scope di questo
// componente (si dispone con lui).
const righeStore = useOffertaRigheStore()

// Le scritture delle righe (le eccezioni), nella forma che il BB chiede.
const scritture = {
  crea: (id, payload) => store.addEccezione(id, payload),
  aggiorna: (id, rigaId, payload) => store.aggiornaEccezione(id, rigaId, payload),
  elimina: (id, rigaId) => store.eliminaEccezione(id, rigaId),
}
const apiComponenti = {
  anteprima: previewEccezioneComponenti,
  elenco: listEccezioneComponenti,
  aggiorna: updateEccezioneComponente,
  elimina: deleteEccezioneComponente,
}
</script>

<template>
  <RigheEccezioniDrawer
    :visible="props.visible"
    :documento-id="props.offertaId"
    :emittente-fiscale-id="props.emittenteFiscaleId"
    lista-codice="vendite.offerta_righe"
    documento="OFFERTA_COMMERCIALE"
    :righe-store="righeStore"
    :scritture="scritture"
    :esporta-righe="exportRigheLista"
    :api-componenti="apiComponenti"
    :erogazioni-articolo="listRigaErogazioni"
    :tab-entity="TAB_ENTITIES.OFFERTA_COMMERCIALE"
    i18n-documento="vendite.offerte"
    :bloccato="bloccato"
    @update:visible="(v) => emit('update:visible', v)"
    @changed="emit('changed')"
  >
    <template #intestazione>
      <DrawerContextHeader
        :tag-value="props.offertaCodice"
        :items="[
          { label: t('vendite.offerte.col_cliente'), value: props.offertaCliente },
          { label: t('vendite.offerte.col_validita_dal'), value: props.offertaValiditaDal ? displayDate(props.offertaValiditaDal) : null },
          { label: t('vendite.offerte.col_validita_al'), value: props.offertaValiditaAl ? displayDate(props.offertaValiditaAl) : null, fallback: '∞' },
        ]">
        <template #status>
          <Tag
            :value="props.offertaStatoDescrizione"
            :severity="statoOffertaSeverity(props.offertaStatoCodice)"
          />
        </template>
      </DrawerContextHeader>
    </template>
  </RigheEccezioniDrawer>
</template>
