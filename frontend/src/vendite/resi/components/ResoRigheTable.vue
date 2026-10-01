<script setup>
// Scopo: righe reso master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2):
//        la lista, la macchina del form e le azioni vivono nel BB; qui restano
//        le celle speciali (quota accreditata, stato della ri-consegna), le
//        azioni di dominio e il form di riga.
//        ⭐ Le colonne vengono dal catalogo (`vendite.reso_righe`, lista 100)
//        dal 2026-09-28 (brief-db-liste-righe-documento).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import { useActionPermission } from '../../../core/composables/useActionPermission'
import { MANAGE_ICONS } from '../../../core/constants'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import { formatNumber } from '../../../core/utils/format'
import { statoRiconsegnaSeverity } from '../../../core/utils/severity'
import { AZIONE_ACCREDITA_RESO } from '../constants'
import { useResiStore } from '../stores/resi'
import { useResoRigheStore } from '../stores/resoRighe'
import { exportRigheLista } from '../api/resiApi'
import AccreditoAnnullaDialog from './dialogs/AccreditoAnnullaDialog.vue'
import ResoRigaForm from './ResoRigaForm.vue'

const { t, te } = useI18n()
const store = useResiStore()
// La lista delle righe: uno store per istanza del drawer.
const righe = useResoRigheStore()

defineProps({
  resoId: { type: Number, required: true },
  // L'emittente del reso (PK): lasciapassare del cancello di perimetro della
  // lista, per chi vede piu' emittenti. Arriva col dettaglio.
  emittenteFiscaleId: { type: Number, default: null },
  // DDT di origine del reso: serve al form riga per proporre le righe DDT
  // con residuo rendibile.
  ddtOrigineId: { type: [Number, null], default: null },
  isModificabile: { type: Boolean, default: true },
  // Readonly PURO del drawer (permessi), non il lock-di-stato: le azioni di
  // dominio sulle righe vivono proprio sul documento non piu' modificabile.
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['changed', 'form-aperto'])

// Il drawer parent chiama loadRighe sul ref: ri-espone quello del BB.
const tableRef = ref(null)
defineExpose({ loadRighe: () => tableRef.value?.loadRighe() })

// ── Annullo dell'accredito (B2-bis) — QUI e' la sede principale ─────────────
// ⭐ Perche' nel drawer e non nella coda: dopo il verbo la riga ESCE dalla coda
// accrediti (l'accredito e' registrato al verbo, non alla fattura — §20.3),
// quindi il caso per cui l'annullo esiste — «ho cliccato la riga sbagliata» —
// da li' non si raggiunge piu'. Il reso invece la riga ce l'ha sempre.
// ⚠️ L'azione vive su un reso CONFERMATO, dove le righe non sono piu'
// modificabili: e' il motivo per cui il BB ha ora un punto d'innesto per le
// azioni di dominio (`extraRowActions`) indipendente da `isModificabile`.
// ⚠️ Si offre sul FATTO (`gia_accreditato > 0`, che il backend legge dalla fn
// unica del DB) e non sulla REGOLA: «tutte le rettifiche ancora NON_EMESSA» e'
// una precondizione della madre, e ricalcolarla qui sarebbe una seconda copia
// destinata a divergere.
// ⛔ MA FINO AL 2026-08-26 IL BOTTONE RESTAVA ACCESO ANCHE QUANDO LA MADRE
//    AVREBBE RIFIUTATO, e l'operatore scopriva il vincolo dopo aver aperto la
//    dialog e scritto il motivo OBBLIGATORIO (rilievo in-app di Tid su
//    RESO0000017, le cui tre rettifiche erano gia' EMESSA sulla nota di
//    credito). Fra «ricalcolare la regola qui» e «non dirla affatto» c'e' la
//    terza strada, che e' quella di casa: la regola la EMETTE il database.
//    `annullo_blocco_codice` arriva da `vw_resi_righe_dettaglio` e nasce da
//    `script.fn_check_accredito_annullabile`, che e' la sede UNICA — la stessa
//    che la madre chiama per rifiutare. Zero copie, e il pulsante spento sa
//    dire perche'.
//    Regola: `frontend-standards` «permesso ⇒ nascondi, stato ⇒ disabilita col
//    motivo», gia' applicata al §43 su «Annulla RESO» (livello documento) e
//    arrivata qui solo ora (livello riga).
// ⚠️ `NESSUN_ACCREDITO` non raggiunge la UI: senza accredito l'azione non e'
//    proprio offerta (`visible` implicito). Vive nella check perche' la MADRE
//    deve poterlo sollevare su una chiamata diretta all'API.
const { isAllowed: canAccreditare } = useActionPermission(AZIONE_ACCREDITA_RESO)
const annulloVisible = ref(false)
const annulloRiga = ref(null)

// Decodifica fail-visible del motivo di blocco (gemella di `bloccoLabel` nella
// coda): un codice nuovo mostra il codice grezzo, mai la chiave i18n letterale.
function annulloBloccoLabel(codice) {
  return labelOrCode(t, te, `vendite.resi.annullo_blocco.${String(codice).toLowerCase()}`, codice)
}

function azioniRiga(riga) {
  if (!canAccreditare.value || !(Number(riga.gia_accreditato) > 0)) return []
  const blocco = riga.annullo_blocco_codice || null
  return [{
    key: 'annulla-accredito',
    label: t('vendite.resi.annullo_azione'),
    icon: MANAGE_ICONS.UNDO,
    severity: 'danger',
    disabled: blocco != null,
    // ⚠️ Il campo del BB e' `tooltip`, NON `motivo`: `RowActionsMenu` ne ricava
    //    da solo la riga del popup (`actionMotivo`). Un `motivo:` sull'azione
    //    non lo legge nessuno — difetto reale trovato in `ResiCodaTable` il
    //    2026-08-26 e corretto insieme a questo.
    tooltip: blocco ? annulloBloccoLabel(blocco) : undefined,
    command: () => {
      annulloRiga.value = riga
      annulloVisible.value = true
    },
  }]
}
</script>

<template>
  <RigheMasterDetailTable
    ref="tableRef"
    codice="vendite.reso_righe"
    :store="righe"
    :parent-id="resoId"
    :emittente-fiscale-id="emittenteFiscaleId"
    :export-fn="exportRigheLista"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    :extra-row-actions="azioniRiga"
    title-key="vendite.resi.section_righe"
    new-tooltip-key="vendite.resi.aggiungi_riga"
    confirm-delete-key="vendite.resi.conferma_elimina_riga"
    deleted-message-key="vendite.resi.riga_eliminata"
    new-label-key="vendite.resi.nuova_riga"
    edit-label-key="vendite.resi.modifica_riga"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <!-- Quota gia' accreditata: si mostra solo dove c'e' (una riga per
         ri-consegna non ha accrediti), ed e' il dato da cui dipende l'azione
         di annullo — mostrarlo rende visibile PERCHE' l'azione c'e'. -->
    <template #cell-gia_accreditato="{ data }">
      <span v-if="Number(data.gia_accreditato) > 0">{{ formatNumber(data.gia_accreditato) }}</span>
      <span v-else>—</span>
    </template>
    <!-- Copertura ri-consegna: solo per righe con riapre_residuo (derivata). -->
    <template #cell-stato_riconsegna="{ data }">
      <Tag v-if="data.stato_riconsegna"
        :value="t(`vendite.resi.riconsegna_stato.${data.stato_riconsegna}`)"
        :severity="statoRiconsegnaSeverity(data.stato_riconsegna)" />
    </template>

    <template #form="{ riga, onSaved, onCancel }">
      <ResoRigaForm
        :reso-id="resoId"
        :ddt-origine-id="ddtOrigineId"
        :riga="riga"
        @saved="onSaved"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>

  <!-- Stesso dialog della coda accrediti: una sola copia del testo che
       distingue «annulla l'accredito» da «resetta il lotto». -->
  <AccreditoAnnullaDialog
    :readonly="readonly"
    v-model:visible="annulloVisible"
    :riga="annulloRiga"
    @annullato="tableRef?.loadRighe(); emit('changed')"
  />
</template>
