<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CONFERMA DELL'ANNULLO DI UN DOCUMENTO CON LEGAMI — bolla, ordine,
//        preventivo, contratto (brief-db-annullo-documento-con-legami R-1),
//        commessa (brief-db-annullo-a-valle-riapre-a-monte D-2) e offerta
//        (brief-modello-documento-vendita §13, O-4).
//        Annullare un documento che ha consumato qualcosa di altri documenti
//        (la merce di un ordine o di un reso, le righe di un preventivo, righe
//        di commessa da emettere) o che nasce da un'offerta riapre quelle
//        cose. Per decisione di Tid non succede in silenzio.
// ⭐ Il giro e' quello di `useForzaturaConfermata` (il chiamante lo possiede):
//    1° tentativo senza dichiarazione -> il DB rifiuta (E_DOC_ANNULLO_CON_LEGAMI,
//    `confirm_and_retry`) -> qui si elencano i legami -> la conferma DICHIARA
//    quanti legami si sono visti (`legami_confermati`). Se nel frattempo sono
//    cambiati il DB chiede di nuovo: arriva una `domanda` NUOVA (identita'
//    diversa) e l'elenco si rilegge.
// ⭐ Regola del 2: e' nato per la bolla (`DdtAnnulloLegamiDialog`, D-8 di
//    brief-db-ddt-righe-evase-dall-ordine) e alla seconda finestra e' diventato
//    questo componente; la copia della bolla si e' ritirata.
// ⛔ Il numero dichiarato e' quello LETTO qui (`GET …/legami/`), mai un valore
//    preso dal messaggio o tenuto da prima: dichiarare cio' che non si e' visto
//    svuoterebbe la conferma. Conta i LEGAMI (`count(*)` del lettore del DB),
//    non le righe del documento: una riga di ri-consegna ne porta due.
// ⭐ Se fra la domanda del DB e la lettura i legami sono spariti (un'altra
//    sessione li ha ritirati), qui si legge ZERO: non c'e' niente da
//    dichiarare, e la conferma ripete SENZA dichiarazione — il documento senza
//    legami il DB lo annulla al primo colpo. Se nel frattempo i legami sono
//    tornati, il DB chiede di nuovo e l'elenco si rilegge.
// ⚠️ Il nome del documento dall'altra parte lo da' il lineage (decisione di
//    Tid): se non lo vede, la riga mostra il solo tipo, senza link.
// ⭐ LA COMMESSA e' a valle di tutto cio' che la riempie: un legame per riga
//    NON_EMESSA, e i legami sono di due nature. CONSUMO si RIAPRE (il
//    preventivo, l'ordine, il contratto, la bolla o il consumo tornano da
//    mandare in commessa, il reso da accreditare); ANNULLO SI ANNULLA (gli
//    oneri: niente a monte). La finestra li dice in due elenchi, come ha
//    chiesto Tid (§6.1 del brief). Le righe di commessa non hanno un numero
//    che l'operatore conosca, quindi si contano per documento d'origine
//    invece di elencarle una a una; il NUMERO DICHIARATO resta quello del
//    lettore (`legami`), non quello delle voci a video.
// ⭐ L'OFFERTA: il legame e' la revisione precedente, superata, che torna
//    emessa quando si annulla l'ultima revisione viva. E' una PROVENIENZA come
//    l'offerta d'origine di un ordine, ma cio' che succede e' un altro: non
//    «torna trasformabile», «torna emessa». La revisione precedente non e' un
//    nodo del lineage: la riga mostra il solo tipo, senza link.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'

import AppDialog from '../../../core/components/AppDialog.vue'
import DocumentoDrawerHost from '../../../core/components/DocumentoDrawerHost.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useDocumentoDrawer } from '../../../core/composables/useDocumentoDrawer'
import { formatNumber } from '../../../core/utils/format'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { NATURA_LEGAME } from '../../constants'
import { lineageDocumentoLabel } from '../lineage/lineageLabels'
import { getLegami } from './legamiApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Il path lista del dominio (es. '/vendite/ordini') e l'id del documento.
  basePath: { type: String, required: true },
  docId: { type: Number, required: true },
  // Il nome dell'azione che ha aperto la finestra («Annulla ordine»): titolo e
  // pulsante dicono la stessa parola del pulsante premuto.
  header: { type: String, required: true },
  // La domanda in sospeso di `useForzaturaConfermata` (`{ messaggio }`): una
  // domanda nuova = rileggere.
  domanda: { type: [Object, null], default: null },
  // Il salvataggio in volo e' del chiamante (la conferma ripete la sua chiamata).
  loading: { type: Boolean, default: false },
  // ⭐ Readonly PURO del chiamante (permessi area / split / forzato), MAI il
  // lock-di-stato del documento. L'annullo con legami arriva per costruzione
  // su un documento uscito dalla bozza, cioe' proprio quando il drawer fornisce
  // READONLY_KEY=true: ereditandolo, FormFooter nascondeva la conferma e la
  // finestra offriva solo «Annulla» — su preventivo, ordine, bolla e contratto
  // l'annullo con legami non si poteva confermare (collaudo di Tid, 2026-10-13).
  // OBBLIGATORIA di proposito: dimenticarla rifarebbe il difetto senza errori.
  readonly: { type: Boolean, required: true },
})
const emit = defineEmits(['conferma', 'cancel'])

const { t, te } = useI18n()
const { execute, loading: caricamento } = useApiHandler()

const dati = ref(null)

// ⚠️ La risposta vale solo per la domanda che l'ha chiesta: se nel frattempo ne
//    e' arrivata una nuova (o la finestra si e' chiusa), quella vecchia si
//    scarta — altrimenti si dichiarerebbe un conteggio letto per un'altra domanda.
watch(() => props.domanda, async (domanda) => {
  dati.value = null
  if (!domanda) return
  const letti = await execute(() => getLegami(props.basePath, props.docId))
  if (props.domanda === domanda) dati.value = letti
}, { immediate: true })

const righe = computed(() => dati.value?.righe ?? [])

// La forma della commessa: la decide il documento della risposta, non la
// forma delle righe (riga_nr nullo vale anche per i legami di testata).
const daCommessa = computed(() => dati.value?.documento === SORGENTE_CODES.COMMESSA)
// Idem per l'offerta: la sua PROVENIENZA e' la revisione precedente.
const daOfferta = computed(() => dati.value?.documento === SORGENTE_CODES.OFFERTA_COMMERCIALE)

// Scopo: le voci della finestra. Documento qualunque: una voce per legame,
//        com'e' sempre stato. Commessa: le righe che si riaprono contate per
//        documento d'origine (o per origine, quando non e' un documento del
//        lineage: i consumi), gli oneri da parte.
// ⚠️ La chiave e' l'IDENTITA' del documento (tipo + id), non `apribile`: quella
//    chiede anche il nome, e due documenti che il lineage non nomina
//    finirebbero in una voce sola, contando come uno.
const voci = computed(() => {
  if (!daCommessa.value) return righe.value.map((legame) => ({ legame, n: 1 }))
  const gruppi = new Map()
  for (const l of righe.value) {
    if (l.natura === NATURA_LEGAME.ANNULLO) continue
    const documento = l.origine_tipo_codice_interno != null && l.origine_id != null
    const chiave = documento ? `${l.origine}:${l.origine_id}` : String(l.origine)
    const voce = gruppi.get(chiave)
    if (voce) voce.n += 1
    else gruppi.set(chiave, { legame: l, n: 1 })
  }
  return [...gruppi.values()]
})

// Gli oneri della commessa: si annullano con lei, e la finestra li conta.
const oneriAnnullati = computed(() => (
  daCommessa.value ? righe.value.filter((l) => l.natura === NATURA_LEGAME.ANNULLO).length : 0
))

// I legami sono spariti dopo la domanda: si annulla senza dichiarare niente.
const senzaLegami = computed(() => dati.value != null && !dati.value.legami)

// Scopo: il documento dall'altra parte, a parole: tipo e codice.
// ⭐ Un vocabolario solo: dal lotto 2b della grammatica unica l'`origine` e' il
//    codice di `config.sorgenti`, come il tipo del lineage, e si nomina con la
//    stessa etichetta anche quando non e' un documento da aprire (i consumi).
//    ONERE non e' una sorgente: senza chiave esce il codice (fail-visible), ma
//    nella commessa gli oneri si contano a parte e non arrivano qui.
function documentoLabel(l) {
  const tipo = lineageDocumentoLabel(t, te, l.origine_tipo_codice_interno ?? l.origine, null)
  return l.origine_codice ? `${tipo} ${l.origine_codice}` : tipo
}

// Scopo: che cosa si riapre, dopo il nome del documento. Tre forme, dalla
//        natura e dalla riga: la PROVENIENZA (l'offerta torna trasformabile),
//        il consumo di una RIGA (quantita' da spedire, righe da ordinare), il
//        consumo SENZA riga (righe di commessa da emettere). Per la commessa,
//        quante righe tornano da mandare (o da accreditare, per il reso); per
//        l'offerta, la revisione precedente che torna emessa.
function cosaSiRiapre(l, n) {
  if (daCommessa.value) {
    return l.origine === SORGENTE_CODES.RESO_VENDITA
      ? t('vendite.annullo_legami.commessa_da_accreditare', { n })
      : t('vendite.annullo_legami.commessa_da_mandare', { n })
  }
  if (l.natura === NATURA_LEGAME.PROVENIENZA) {
    return t(daOfferta.value ? 'vendite.annullo_legami.revisione_precedente' : 'vendite.annullo_legami.provenienza')
  }
  if (l.riga_nr == null) return t('vendite.annullo_legami.commessa')
  if (l.qta == null) return t('vendite.annullo_legami.riga_senza_qta', { riga: l.riga_nr })
  return t('vendite.annullo_legami.riga', {
    riga: l.riga_nr,
    qta: formatNumber(l.qta, { maximumFractionDigits: 6 }),
  })
}

function apribile(l) {
  return l.origine_tipo_codice_interno != null && l.origine_id != null && l.origine_codice != null
}

// Gesto «vai a»: il drawer del documento dall'altra parte, impilato sopra.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumento,
} = useDocumentoDrawer()

function onConferma() {
  emit('conferma', senzaLegami.value ? {} : { legami_confermati: dati.value.legami })
}
</script>

<template>
  <!-- conferma-uscita: nessuna — non ci sono campi: si conferma o si rinuncia. -->
  <AppDialog
    :visible="visible"
    :header="header"
    width="md"
    :loading="loading || caricamento"
    :readonly="readonly"
    :save-disabled="!dati"
    :save-label="header"
    save-severity="danger"
    @save="onConferma"
    @cancel="emit('cancel')"
  >
    <div class="form-grid">
      <!-- La frase del DB: nomina gia' il documento e il numero di legami. -->
      <Message v-if="!senzaLegami" severity="warn" :closable="false">{{ domanda?.messaggio }}</Message>
      <!-- La frase del DB non vale piu': i legami che contava non ci sono. -->
      <Message v-else severity="info" :closable="false">
        {{ t('vendite.annullo_legami.nessun_legame') }}
      </Message>

      <div v-if="voci.length" class="form-field">
        <label>{{ t('vendite.annullo_legami.righe') }}</label>
        <ul class="app-annullo-legami-lista">
          <li v-for="({ legame: l, n }, i) in voci" :key="`${l.origine}-${l.origine_id}-${l.origine_riga_id}-${i}`">
            <Button v-if="apribile(l)" link class="app-annullo-legami-link"
              :label="documentoLabel(l)"
              v-tooltip.top="t('vendite.lineage.apri_documento')"
              @click="apriDocumento(l.origine_tipo_codice_interno, l.origine_id)" />
            <span v-else>{{ documentoLabel(l) }}</span>
            · {{ cosaSiRiapre(l, n) }}
          </li>
        </ul>
      </div>

      <div v-if="oneriAnnullati" class="form-field">
        <label>{{ t('vendite.annullo_legami.si_annulla') }}</label>
        <ul class="app-annullo-legami-lista">
          <li>{{ t('vendite.annullo_legami.oneri_annullati', { n: oneriAnnullati }) }}</li>
        </ul>
      </div>

      <small v-if="!senzaLegami" class="app-field-hint">
        {{ t(daCommessa ? 'vendite.annullo_legami.spiegazione_commessa'
          : daOfferta ? 'vendite.annullo_legami.spiegazione_offerta'
            : 'vendite.annullo_legami.spiegazione') }}
      </small>
    </div>
  </AppDialog>

  <DocumentoDrawerHost
    v-model:visible="docDrawerVisible"
    :tipo-codice="docDrawerTipo"
    :doc-id="docDrawerId" />
</template>

<style scoped>
.app-annullo-legami-lista {
  margin: 0;
  padding-left: 1.25rem;
}

/* Il link del documento resta in linea col testo della riga. */
.app-annullo-legami-link {
  padding: 0;
}
</style>
