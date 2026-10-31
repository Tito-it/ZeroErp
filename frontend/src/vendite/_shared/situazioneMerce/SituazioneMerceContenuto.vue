<script setup>
// Scopo: Il DETTAGLIO della situazione merce — «riga per riga», il secondo
// tempo del §5.2 (riassunto in testata, dettaglio a richiesta).
//
// Quattro sezioni piu' il riepilogo:
//   1. righe d'ordine  (il riassunto per riga ordinata)
//   2. spedizioni      (le partite di merce, grana riga di DDT)
//   3. da accreditare  (la coda, con l'etichetta DOVUTA/FACOLTATIVA)
//   4. da ri-consegnare(la coda, col residuo aperto)
//   5. riepilogo       (il CONTO, una volta sola, in fondo)
//
// ⭐ IL CONTO SI SCRIVE UNA VOLTA SOLA, E STA IN FONDO (rev 2026-08-19, rilievo
// in-app di Tid). Prima ogni tabella aveva la colonna «da fare», e sull'ordine
// le tabelle sono DUE che descrivono la STESSA merce a due livelli: la riga
// d'ordine diceva «1 da accreditare» e la sua spedizione pure — *«sembra quasi
// ci siano 2 pezzi da restituire»*. Non era un errore di calcolo (il totale era
// sempre uno solo): era il conto ripetuto accanto a due righe diverse. Adesso le
// tabelle raccontano i FATTI (quanto ordinato, uscito, tornato, fatturato) e il
// COMPITO si legge nel riepilogo, dove e' uno.
//
// ⭐ E LE DUE SEZIONI CI SONO SEMPRE, sull'ordine come sul DDT: il pannello e'
// lo stesso da qualunque documento lo si apra. Dal DDT la sezione righe d'ordine
// dice come sta la riga NEL COMPLESSO (le altre spedizioni comprese) — che e'
// il contesto che prima costringeva a cambiare schermata.
//
// ⚠️ E `differenza` NULL non e' zero. Il motivo per cui il conto non si applica
// (riga mai spedita, causale non fatturabile, conto non calcolabile) resta sulla
// RIGA, come Tag sotto la descrizione: quelle righe non portano un saldo, quindi
// non possono ri-creare la doppia lettura, e senza il motivo «non calcolabile»
// (FE-1) sparirebbe dentro un vuoto che somiglia a «tutto a posto».
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
// DataTable grezza: le quattro tabelle sono SEZIONI di un payload solo
// (`props.sezioni`), tutte limitate al documento da cui si apre — il dettaglio
// del master, non liste con endpoint e popolazione propri.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import { statoMerceSeverity } from '../../../core/utils/severity'
import { displayDate } from '../../../core/utils/date'
import { CONTESTO_MERCE, ETICHETTA_ACCREDITO_MERCE, STATO_MERCE } from './situazioneMerceCostanti'
import {
  compitiSituazioneMerce,
  formatQtaMerce as qta,
  sintesiSituazioneMerce,
} from './situazioneMerceSintesi'
import { STATUS_ICONS } from '../../../core/constants'

const props = defineProps({
  sezioni: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  loaded: { type: Boolean, default: false },
})

const emit = defineEmits(['apri-coda-accrediti'])

const { t, te } = useI18n()

const s = computed(() => sintesiSituazioneMerce(props.sezioni))
const righeOrdine = computed(() => props.sezioni.righe_ordine ?? [])
const partite = computed(() => props.sezioni.partite ?? [])
const accrediti = computed(() => props.sezioni.accrediti ?? [])
const riconsegne = computed(() => props.sezioni.riconsegne ?? [])
const eDdt = computed(() => props.sezioni.contesto === CONTESTO_MERCE.DDT)

// I compiti del riepilogo: la STESSA lista dei chip in testata
// (`compitiSituazioneMerce`), non una seconda aritmetica. Il chip della barra e
// la voce del riepilogo dicono lo stesso numero per costruzione.
const compiti = computed(() => compitiSituazioneMerce(s.value, t))

// Gli stati che PORTANO un saldo: il loro numero vive nel riepilogo, e non si
// ripete sulla riga. `PAREGGIATA` non ha niente da dire — una riga a posto non
// merita un'etichetta.
const _STATI_SENZA_MOTIVO = [
  STATO_MERCE.PAREGGIATA,
  STATO_MERCE.DA_FATTURARE,
  STATO_MERCE.DA_ACCREDITARE,
]

// Scopo: IL MOTIVO PER CUI QUESTA RIGA NON HA UN CONTO — e sono ragioni diverse
//        fra loro, non un trattino comune: «non ancora spedita», «non si
//        fattura», «conto non calcolabile» e «nessun impegno» chiedono cose
//        diverse a chi guarda.
// ⚠️ Nessuno di questi stati ha un saldo, quindi mostrarli sulla riga NON
//        rimette il conto ripetuto che il ridisegno ha appena tolto.
function motivo(riga) {
  if (_STATI_SENZA_MOTIVO.includes(riga.stato)) return null
  switch (riga.stato) {
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
      return riga.stato || null
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

// Scopo: IL RITARDO DELLA RIGA, come lo dichiara la vista (brief-db-modifiche-
//        certe-ciclo-vendita-e-articolo, P-6): `giorni_ritardo` NULL = «non si
//        applica» (niente da spedire, o nessuna data) → nessuna etichetta;
//        0 = c'e' da spedire e non e' tardi; N > 0 = giorni di ritardo rispetto
//        alla PROMESSA (o, senza promessa, alla richiesta del cliente).
// ⛔ Il verso NON si ricalcola qui («oggi > data»): lo fa la vista con il
//        residuo e la soglia dell'impegno, e ricalcolarlo sarebbe una seconda
//        verita' sul residuo. Qui si sceglie solo frase e colore.
function ritardo(riga) {
  const n = riga.giorni_ritardo
  if (n == null) return null
  const giorni = Number(n)
  if (giorni > 0) {
    return { severity: 'danger', label: t('vendite.situazione_merce.ritardo_giorni', { n: giorni }) }
  }
  return { severity: 'success', label: t('vendite.situazione_merce.ritardo_in_tempo') }
}
</script>

<template>
  <div v-if="loading && !loaded" class="app-loading">
    <i :class="STATUS_ICONS.CARICAMENTO" />
  </div>

  <div v-else-if="!loaded" class="app-empty-state">
    {{ t('vendite.situazione_merce.non_disponibile') }}
  </div>

  <div v-else class="app-merce-contenuto">
    <!-- 1. RIGHE D'ORDINE — il livello che risponde a «di quello che ho
         ordinato, a che punto sono». Comprende le righe MAI SPEDITE, che il
         vecchio contatore non conteneva affatto.
         Dal DDT ci sono le righe d'ordine che QUESTA spedizione ha toccato, e
         raccontano l'ordine intero: e' il contesto, non il conto. Va detto. -->
    <template v-if="righeOrdine.length">
      <h4 class="app-drawer-section">{{ t('vendite.situazione_merce.sez_righe_ordine') }}</h4>
      <p v-if="eDdt" class="app-merce-nota">
        {{ t('vendite.situazione_merce.sez_righe_ordine_hint_ddt') }}
      </p>
      <DataTable :value="righeOrdine" size="small" class="app-datatable app-datatable--inner" data-key="ordine_riga_id">
        <Column field="riga_nr" :header="t('vendite.situazione_merce.col_riga')" style="width: 60px;" />
        <Column field="articolo_codice" :header="t('vendite.situazione_merce.col_articolo')" style="width: 130px;" />
        <Column field="descrizione" :header="t('vendite.situazione_merce.col_descrizione')">
          <template #body="{ data }">
            {{ data.descrizione }}
            <!-- FE-1: il motivo per cui il conto non si applica. Deve APPARIRE
                 diverso da «tutto regolare»: di un conto che non si puo' fare
                 non esiste un totale, e lasciare la riga muta lo farebbe
                 sembrare zero. -->
            <div v-if="motivo(data)" class="app-merce-riga-motivo">
              <Tag :severity="statoMerceSeverity(data.stato)" :value="motivo(data)" />
            </div>
          </template>
        </Column>
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
          <template #body="{ data }">
            {{ qta(data.fatturato) }}
            <!-- FE-3: l'anticipo accanto al fatturato, ma DICHIARATO come altra
                 cosa. E' merce fatturata e non ancora uscita: sommarlo al saldo
                 farebbe chiedere una nota di credito per roba da spedire. -->
            <div v-if="Number(data.fatturato_anticipato) > 0" class="app-merce-nota">
              {{ t('vendite.situazione_merce.anticipato', { n: qta(data.fatturato_anticipato) }) }}
            </div>
          </template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_da_spedire')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.da_spedire) }}</template>
        </Column>
        <!-- Le date di consegna della riga (Blocco A): la richiesta del cliente
             e la nostra promessa. Due colonne e non una, perche' la differenza
             fra le due E' la promessa — e il ritardo si misura sulla seconda. -->
        <Column :header="t('vendite.situazione_merce.col_data_consegna_richiesta_cliente')" style="width: 105px;">
          <template #body="{ data }">{{ displayDate(data.data_consegna_richiesta_cliente) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_data_consegna_confermata')" style="width: 105px;">
          <template #body="{ data }">{{ displayDate(data.data_consegna_confermata) }}</template>
        </Column>
        <!-- Il ritardo: e' IL POSTO per cui `giorni_ritardo` esiste. Vuoto
             quando il conto non si applica — «in tempo» e «niente da
             spedire» sono due cose diverse, e la vista non le confonde. -->
        <Column :header="t('vendite.situazione_merce.col_giorni_ritardo')" style="width: 100px;">
          <template #body="{ data }">
            <Tag v-if="ritardo(data)" :severity="ritardo(data).severity" :value="ritardo(data).label" />
          </template>
        </Column>
      </DataTable>
    </template>

    <!-- 2. SPEDIZIONI (partite di merce) — la grana su cui il conto e' davvero
         tenuto. Risponde a «cosa e' successo a QUESTA spedizione». -->
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
              :icon="STATUS_ICONS.ERRORE"
              :value="t('vendite.situazione_merce.sospetta')"
              v-tooltip.bottom="t('vendite.situazione_merce.sospetta_hint')"
            />
            <div v-if="motivo(data)" class="app-merce-riga-motivo">
              <Tag :severity="statoMerceSeverity(data.stato)" :value="motivo(data)" />
            </div>
          </template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_consegnato')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.consegnato) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_reso')" style="width: 90px;">
          <template #body="{ data }">
            {{ qta(data.reso) }}
            <!-- Merce tornata e gia' impegnata su un DDT non ancora emesso:
                 non e' dal cliente e non e' in coda, e' sul banco. Senza questa
                 voce quei pezzi sparirebbero dalla lettura (§8.3-bis). -->
            <div v-if="Number(data.in_riconsegna) > 0" class="app-merce-nota">
              {{ t('vendite.situazione_merce.in_riconsegna', { n: qta(data.in_riconsegna) }) }}
            </div>
          </template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_tenuti')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.tenuti) }}</template>
        </Column>
        <Column :header="t('vendite.situazione_merce.col_fatturato')" style="width: 100px;">
          <template #body="{ data }">{{ qta(data.fatturato) }}</template>
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

    <!-- 5. RIEPILOGO — IL CONTO, e in tutta la dialog c'e' solo qui. Sopra ci
         sono i fatti su due livelli; qui c'e' che cosa resta da fare, una volta.
         ⛔ Il pannello resta una LETTURA (D-NC-8): qui non c'e' il verbo, c'e'
         la strada per raggiungerlo. Un'azione qui dentro vorrebbe permessi,
         conferme, gestione errori e ricarico — quattro cose insieme. -->
    <div v-if="righeOrdine.length || partite.length" class="app-merce-riepilogo">
      <h4 class="app-drawer-section">{{ t('vendite.situazione_merce.sez_riepilogo') }}</h4>

      <!-- La frase che chiude il rilievo: le due tabelle sono DUE LETTURE DELLA
           STESSA MERCE, e il conto e' uno. Senza dirlo, due «1 da accreditare»
           su due righe diverse si leggono come due pezzi. -->
      <p class="app-merce-nota">
        {{ eDdt
          ? t('vendite.situazione_merce.riepilogo_base_ddt')
          : t('vendite.situazione_merce.riepilogo_base_ordine') }}
      </p>

      <div class="app-merce-compiti">
        <Tag
          v-if="s.tuttoRegolare"
          severity="success"
          :icon="STATUS_ICONS.SI"
          :value="t('vendite.situazione_merce.tutto_regolare')"
        />
        <Tag
          v-for="compito in compiti"
          :key="compito.key"
          :severity="compito.severity"
          :value="compito.label"
        />
      </div>

      <!-- FE-3: l'anticipo e' fuori dai compiti e resta dichiarato a parte.
           Non e' qualcosa da fare: e' merce gia' fatturata e non ancora uscita. -->
      <p v-if="s.fatturatoAnticipato > 0" class="app-merce-nota">
        {{ t('vendite.situazione_merce.anticipato', { n: qta(s.fatturatoAnticipato) }) }}
      </p>

      <!-- ⭐ 2026-08-18: la nota «l'emissione non e' ancora disponibile» e' stata
           TOLTA — il verbo esiste, e lasciarla avrebbe spostato la contraddizione
           del §21.1 invece di chiuderla. Al suo posto il collegamento alla coda
           GIA' FILTRATA su questo documento: una coda non filtrata sarebbe «un
           percorso spezzato uguale, solo con un click in piu'». -->
      <p v-if="s.daAccreditare > 0" class="app-merce-nc">
        {{ t('vendite.situazione_merce.nc_spiegazione') }}
        <Button
          link
          size="small"
          :label="t('vendite.situazione_merce.nc_apri_coda')"
          @click="emit('apri-coda-accrediti')"
        />
      </p>
    </div>

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

/* Nota sotto un valore o un titolo di sezione: e' un'informazione di contorno,
   deve arretrare rispetto al dato (frontend-standards §"Glifo vs controllo").
   Niente `opacity`: si sommerebbe al velo di .app-readonly. */
.app-merce-nota {
  margin-top: 0.2rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}

.app-merce-badge {
  margin-left: 0.4rem;
}

/* Il motivo «senza conto» sta sotto la descrizione, non in una colonna sua: una
   colonna vuota su quasi tutte le righe e' rumore, e la riga che ce l'ha si
   nota di piu' cosi'. */
.app-merce-riga-motivo {
  margin-top: 0.25rem;
}

/* Il riepilogo e' l'unico blocco che CONCLUDE: si stacca dalle tabelle con un
   filo, non con un riquadro — non e' un avviso, e' la fine della lettura. */
.app-merce-riepilogo {
  margin-top: 0.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--app-drawer-section-border);
}

.app-merce-compiti {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.app-merce-nc {
  margin-top: 0.5rem;
  font-size: var(--app-font-size-sm);
}
</style>
