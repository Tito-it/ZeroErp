<script setup>
// Scopo: Il DETTAGLIO della situazione merce — «riga per riga», il secondo
// tempo del §5.2 (riassunto in testata, dettaglio a richiesta).
//
// Quattro sezioni, che sono le quattro del payload BE:
//   1. righe d'ordine  (solo sull'ordine: il riassunto per riga ordinata)
//   2. spedizioni      (le partite di merce, grana riga di DDT)
//   3. da accreditare  (la coda, con l'etichetta DOVUTA/FACOLTATIVA)
//   4. da ri-consegnare(la coda, col residuo aperto)
//
// ⭐ IL SALDO NON SI MOSTRA MAI COME NUMERO NEGATIVO (§5.4). Al posto della
// colonna «differenza» c'e' la colonna «da fare», che dice il COMPITO: «8 da
// accreditare». Il verso lo ha gia' deciso il database nella colonna `stato`
// (BE-2): qui si sceglie la frase e il colore, non il significato.
//
// ⚠️ E `differenza` NULL non e' zero: la colonna «da fare» mostra la ragione
// per cui il conto non si applica, non un trattino generico. Riga mai spedita,
// causale non fatturabile e conto non calcolabile sono tre cose diverse, e la
// terza (FE-1) va vista.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import { statoMerceSeverity } from '../../../core/utils/severity'
import { ETICHETTA_ACCREDITO_MERCE, STATO_MERCE } from './situazioneMerceCostanti'
import { formatQtaMerce as qta, sintesiSituazioneMerce } from './situazioneMerceSintesi'

const props = defineProps({
  sezioni: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  loaded: { type: Boolean, default: false },
})

const { t, te } = useI18n()

const s = computed(() => sintesiSituazioneMerce(props.sezioni))
const righeOrdine = computed(() => props.sezioni.righe_ordine ?? [])
const partite = computed(() => props.sezioni.partite ?? [])
const accrediti = computed(() => props.sezioni.accrediti ?? [])
const riconsegne = computed(() => props.sezioni.riconsegne ?? [])

// Scopo: IL COMPITO DELLA RIGA — la traduzione unica del §5.4, in un posto solo.
//        Prende lo `stato` deciso dal DB e la quantita' del saldo, e restituisce
//        la frase che l'operatore legge. Mai il segno meno.
// ⚠️ I quattro stati «senza compito» non ricadono in un trattino comune: dicono
//        PERCHE' non c'e' un conto, e sono ragioni diverse fra loro.
function compito(riga) {
  const d = riga.differenza == null ? null : Number(riga.differenza)
  switch (riga.stato) {
    case STATO_MERCE.DA_ACCREDITARE:
      return t('vendite.situazione_merce.compito_da_accreditare', { n: qta(Math.abs(d ?? 0)) })
    case STATO_MERCE.DA_FATTURARE:
      return t('vendite.situazione_merce.compito_da_fatturare', { n: qta(d ?? 0) })
    case STATO_MERCE.PAREGGIATA:
      return t('vendite.situazione_merce.compito_pareggiata')
    case STATO_MERCE.NON_SPEDITA:
      return t('vendite.situazione_merce.compito_non_spedita')
    case STATO_MERCE.NON_IMPEGNATA:
      return t('vendite.situazione_merce.compito_non_impegnata')
    case STATO_MERCE.NON_FATTURABILE:
      return t('vendite.situazione_merce.compito_non_fatturabile')
    case STATO_MERCE.NON_MISURABILE:
      return t('vendite.situazione_merce.compito_non_misurabile')
    case STATO_MERCE.RICONSEGNA:
      return t('vendite.situazione_merce.compito_riconsegna')
    default:
      // Vocabolario esteso a DB e frontend indietro: si mostra il codice
      // grezzo (fail-visible), mai il vuoto. Stessa regola di `labelOrCode`.
      return riga.stato || '—'
  }
}

// Scopo: etichetta dell'accredito (DOVUTA | FACOLTATIVA) fail-visible: su un
//        valore nuovo a DB si vede il codice grezzo, non il path della chiave
//        i18n — la chiave dinamica nuda mostrerebbe
//        «vendite.situazione_merce.etichetta_x», che non dice niente a nessuno.
function etichettaAccredito(riga) {
  const codice = riga.etichetta || ''
  return labelOrCode(
    t, te,
    `vendite.situazione_merce.etichetta_${codice.toLowerCase()}`,
    codice || '—',
  )
}

// Scopo: severity dell'etichetta — DOVUTA arancio (obbligo), il resto grigio.
function etichettaSeverity(riga) {
  return riga.etichetta === ETICHETTA_ACCREDITO_MERCE.DOVUTA ? 'warn' : 'secondary'
}
</script>

<template>
  <div v-if="loading && !loaded" class="app-loading">
    <i class="pi pi-spin pi-spinner" />
  </div>

  <div v-else-if="!loaded" class="app-empty-state">
    {{ t('vendite.situazione_merce.non_disponibile') }}
  </div>

  <div v-else class="app-merce-contenuto">
    <!-- §5.3: cio' che non si puo' ancora chiudere si MOSTRA, dichiarando che
         l'azione non c'e'. Nascondere l'accredito farebbe sembrare a posto un
         documento su cui c'e' un dovuto al cliente; mostrarlo senza commento
         manderebbe l'operatore a cercare un pulsante che non esiste.
         ⚠️ TEMPORANEO PER COSTRUZIONE: va tolto quando arriva la nota di
         credito (cantiere 3). Il promemoria e' anche nel §10-bis di quel brief,
         cosi' chi la implementa lo trova dalla sua parte. -->
    <Message
      v-if="s.daAccreditare > 0"
      severity="info"
      :closable="false"
      size="small"
    >
      {{ t('vendite.situazione_merce.nc_non_disponibile') }}
    </Message>

    <!-- 1. RIGHE D'ORDINE — il livello che risponde a «di quello che ho
         ordinato, a che punto sono». Comprende le righe MAI SPEDITE, che il
         vecchio contatore non conteneva affatto. -->
    <template v-if="righeOrdine.length">
      <h4 class="app-drawer-section">{{ t('vendite.situazione_merce.sez_righe_ordine') }}</h4>
      <DataTable :value="righeOrdine" size="small" class="app-datatable app-datatable--inner" data-key="ordine_riga_id">
        <Column field="riga_nr" :header="t('vendite.situazione_merce.col_riga')" style="width: 60px;" />
        <Column field="articolo_codice" :header="t('vendite.situazione_merce.col_articolo')" style="width: 130px;" />
        <Column field="descrizione" :header="t('vendite.situazione_merce.col_descrizione')" />
        <Column :header="t('vendite.situazione_merce.col_ordinato')" style="width: 90px;">
          <template #body="{ data }">{{ qta(data.ordinato) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_consegnato')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.consegnato) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_tenuti')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.tenuti) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_fatturato')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.fatturato) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_da_spedire')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.da_spedire) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_da_fare')" style="width: 190px;">
          <template #body="{ data }">
            <Tag :severity="statoMerceSeverity(data.stato)" :value="compito(data)" />
            <!-- FE-3: l'anticipo accanto al compito, ma DICHIARATO come altra
                 cosa. E' merce fatturata e non ancora uscita: sommarlo al saldo
                 farebbe chiedere una nota di credito per roba da spedire. -->
            <div v-if="Number(data.fatturato_anticipato) > 0" class="app-merce-nota">
              {{ t('vendite.situazione_merce.anticipato', { n: qta(data.fatturato_anticipato) }) }}
            </div>
          </template>
        </Column>
      </DataTable>
    </template>

    <!-- 2. SPEDIZIONI (partite di merce) — la grana su cui il conto e' davvero
         tenuto. Sul DDT e' l'unica sezione di conto, ed e' quella che risponde
         a «cosa e' successo a QUESTA spedizione». -->
    <template v-if="partite.length">
      <h4 class="app-drawer-section">{{ t('vendite.situazione_merce.sez_spedizioni') }}</h4>
      <DataTable :value="partite" size="small" class="app-datatable app-datatable--inner" data-key="ddt_riga_id">
        <Column field="ddt_numero" :header="t('vendite.situazione_merce.col_ddt')" style="width: 130px;" />
        <Column field="articolo_codice" :header="t('vendite.situazione_merce.col_articolo')" style="width: 130px;" />
        <Column field="descrizione" :header="t('vendite.situazione_merce.col_descrizione')">
          <template #body="{ data }">
            {{ data.descrizione }}
            <!-- FE-2: l'avviso di S6b. Tre condizioni insieme (riga senza
                 origine, su spedizione MISTA, articolo gia' nell'ordine) —
                 il caso legittimo esiste, quindi si segnala e non si vieta. -->
            <Tag
              v-if="data.sospetto_duplicato_ordine"
              severity="warn"
              class="app-merce-badge"
              icon="pi pi-exclamation-triangle"
              :value="t('vendite.situazione_merce.sospetta')"
              v-tooltip.bottom="t('vendite.situazione_merce.sospetta_hint')"
            />
          </template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_consegnato')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.consegnato) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_reso')" style="width: 90px;">
          <template #body="{ data }">{{ qta(data.reso) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_tenuti')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.tenuti) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_fatturato')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.fatturato) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_da_fare')" style="width: 190px;">
          <template #body="{ data }">
            <Tag :severity="statoMerceSeverity(data.stato)" :value="compito(data)" />
            <!-- Merce tornata e gia' impegnata su un DDT non ancora emesso:
                 non e' dal cliente e non e' in coda, e' sul banco. Senza questa
                 voce quei pezzi sparirebbero dalla lettura (§8.3-bis). -->
            <div v-if="Number(data.in_riconsegna) > 0" class="app-merce-nota">
              {{ t('vendite.situazione_merce.in_riconsegna', { n: qta(data.in_riconsegna) }) }}
            </div>
          </template>
        </Column>
      </DataTable>
    </template>

    <!-- 3. DA ACCREDITARE — la coda, con la SUA etichetta: il pannello non puo'
         contraddirla perche' legge la stessa vista. -->
    <template v-if="accrediti.length">
      <h4 class="app-drawer-section">{{ t('vendite.situazione_merce.sez_accrediti') }}</h4>
      <DataTable :value="accrediti" size="small" class="app-datatable app-datatable--inner" data-key="resi_riga_id">
        <Column field="reso_numero" :header="t('vendite.situazione_merce.col_reso_numero')" style="width: 140px;" />
        <Column field="descrizione" :header="t('vendite.situazione_merce.col_descrizione')" />
        <Column :header="t('vendite.situazione_merce.col_qta_resa')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.quantita) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_accredito')" style="width: 110px;">
          <template #body="{ data }"><strong>{{ qta(data.accredito_dovuto) }}</strong></template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_etichetta')" style="width: 130px;">
          <template #body="{ data }">
            <Tag :severity="etichettaSeverity(data)" :value="etichettaAccredito(data)" />
          </template>
        </Column>
      </DataTable>
    </template>

    <!-- 4. DA RI-CONSEGNARE — il residuo aperto, dalla coda. -->
    <template v-if="riconsegne.length">
      <h4 class="app-drawer-section">{{ t('vendite.situazione_merce.sez_riconsegne') }}</h4>
      <DataTable :value="riconsegne" size="small" class="app-datatable app-datatable--inner" data-key="resi_riga_id">
        <Column field="reso_numero" :header="t('vendite.situazione_merce.col_reso_numero')" style="width: 140px;" />
        <Column field="descrizione" :header="t('vendite.situazione_merce.col_descrizione')" />
        <Column :header="t('vendite.situazione_merce.col_qta_resa')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.qta_resa) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_riconsegnata')" style="width: 120px;">
          <template #body="{ data }">{{ qta(data.qta_riconsegnata) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_residua')" style="width: 110px;">
          <template #body="{ data }"><strong>{{ qta(data.qta_residua) }}</strong></template>
        </Column>
      </DataTable>
    </template>

    <!-- Documento senza alcuna merce da raccontare: si dice, non si lascia
         una dialog bianca. Caso reale: un DDT ancora in bozza non ha partite
         (la merce nasce da EMESSO in poi, decisione D1). -->
    <div v-if="!righeOrdine.length && !partite.length" class="app-empty-state">
      {{ t('vendite.situazione_merce.nessuna_merce') }}
    </div>
  </div>
</template>

<style scoped>
.app-merce-contenuto {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Nota sotto il Tag del compito: e' un'informazione di contorno, deve
   arretrare rispetto al compito (frontend-standards §"Glifo vs controllo").
   Niente `opacity`: si sommerebbe al velo di .app-readonly. */
.app-merce-nota {
  margin-top: 0.2rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}

.app-merce-badge {
  margin-left: 0.4rem;
}
</style>
