// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le due azioni di riga «Archivia» / «Ripristina» delle schede code,
//        in una sede sola. Toglie una riga dall'ELENCO senza toccarne lo
//        stato: i conteggi del pannello «Esiti fatturazione» e il badge in
//        topbar restano fermi (brief-db-archiviazione-righe-code, 2026-09-04).
// Note: Estratto PRIMA di scrivere la seconda copia (regola del 2). Le due
//       code sono gemelle per costruzione — stessa bandiera, stesso trigger,
//       stesso codice errore — e due copie di questo blocco divergerebbero al
//       primo che tocca una sola delle due schede, che e' esattamente cio' che
//       il presidio pgTAP di simmetria esiste per impedire a database.
// ------------------------------------------------------------
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { rigaCodaViva } from '../../core/composables/useQueueCountsPolling'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { AZIONE_CODE_MANAGE } from './useCodaFiltri'

// ⛔ Il permesso dei due verbi NON e' l'ownership di annulla/requeue, ed e' una
// decisione: quei due sono owner-scoped (un operatore agisce sui PROPRI job)
// mentre l'archiviazione ha effetto GLOBALE — chi archivia toglie la riga
// dall'elenco anche all'amministratore. Effetto globale, permesso globale
// (decisione di Tid, brief §7.2).
// ⚠️ Il codename arriva da `useCodaFiltri`, che e' la sede: scritto due volte
// sarebbe un cancello che smette di essere lo stesso al primo rename.
// ⚠️ Passato a `RowActionsMenu` come `action`: il permesso NASCONDE la voce.
// Un'azione grigia «non hai il permesso» sarebbe una promessa che chi guarda
// non puo' mantenere.

// `archivia`/`ripristina`: le due chiamate API della coda (POST per id).
// `ricarica`: che cosa rinfrescare dopo (la scheda ricarica lista + worker).
// `etichettaRiga`: come si nomina la riga nella conferma (le due code hanno
//   identificatori diversi: tipo di lavoro di qua, fattura di la').
// `onArchiviato(idsFalliti)`: invocata dopo un'archiviazione ANDATA IN PORTA
// (anche parziale), con gli id che NON sono passati. Le schede ci riducono la
// selezione a quelli: le riuscite escono dall'elenco, e un contatore che
// continuasse a contarle mentirebbe.
// ⭐ L'ICONA del verbo e' `MANAGE_ICONS.ARCHIVIA`, non un letterale nei due
// chiamanti: la porta la voce di riga E il pulsante di massa, e la stessa
// azione con due icone diverse e' il genere di divergenza che nessun test vede.
export function useCodaArchiviazione({
  archivia, ripristina, ricarica, etichettaRiga, onArchiviato = null,
}) {
  const { t } = useI18n()
  const notify = useNotify()
  const { execute, loading } = useApiHandler()
  const { confirmAction } = useConfirmAction()
  const isReadonly = useInjectReadonly()

  // Scopo: esegue una delle due chiamate su N righe e riferisce l'esito.
  // ⛔ L'esito e' a TRE stati e il 200 non basta: una riga che il database ha
  //    rifiutato — perche' e' tornata al lavoro sotto le mani — non affonda le
  //    altre, ma va DETTA. Tacere il parziale e' il difetto che il verbo di
  //    massa introduce se lo si tratta come uno singolo.
  // ⚠️ `res !== null` e non `if (res)`: `execute` restituisce `null` solo
  //    sull'errore, e una risposta legittima puo' essere falsy.
  // Ritorna gli id che NON sono passati, oppure `null` se la chiamata stessa e'
  // fallita (rete, 4xx): li' non si sa niente delle righe e la selezione resta
  // intatta — buttarla via su un errore di trasporto farebbe perdere il lavoro
  // di chi ha spuntato.
  async function _esegui(chiamata, ids, { chiaveOk, chiaveParziale }) {
    const res = await execute(() => chiamata(ids))
    if (res === null) return null
    const d = res ?? {}
    const falliti = d.falliti ?? []
    if (falliti.length === 0) {
      notify.success(t(chiaveOk, d.riuscite, { n: d.riuscite }))
    } else if (d.riuscite > 0) {
      // Parziale: si dice quante sono passate, quante no, e il PERCHE' della
      // prima — la frase viene dal catalogo del database, non riscritta qui.
      notify.warn(t(chiaveParziale, {
        ok: d.riuscite, ko: falliti.length, motivo: falliti[0].message,
      }))
    } else {
      notify.error(falliti[0].message || t('common.error'))
    }
    ricarica()
    return falliti.map((f) => f.id)
  }

  // Scopo: mette via N righe. La conferma c'e' perche' l'effetto e' PER TUTTI —
  //        le righe spariscono anche a chi non le ha archiviate — e questa e'
  //        l'unica occasione in cui dirlo. Il gesto resta reversibile, e la
  //        frase lo dice: e' il motivo per cui non e' una conferma `danger`.
  // ⚠️ Due frasi diverse per una riga e per molte: «Mettere via la fattura X?»
  //    e «Mettere via 14 righe?» non sono la stessa domanda, e un plurale
  //    finto («1 righe») e' il segno che nessuno ha guardato.
  function archiviaRighe(righe) {
    const ids = righe.map((r) => r.id)
    if (ids.length === 0) return
    confirmAction({
      header: t('strumenti.code.archivia_header'),
      message: ids.length === 1
        ? t('strumenti.code.archivia_conferma', { riga: etichettaRiga(righe[0]) })
        : t('strumenti.code.archivia_conferma_multi', { n: ids.length }),
      onAccept: async () => {
        const idsFalliti = await _esegui(archivia, ids, {
          chiaveOk: 'strumenti.code.archivia_esito',
          chiaveParziale: 'strumenti.code.archivia_esito_parziale',
        })
        // ⛔ Si tolgono dalla selezione le sole RIUSCITE: quelle fallite
        //    restano spuntate, ed e' quello che serve — sono esattamente le
        //    righe su cui l'operatore deve tornare. Azzerare tutto gliele
        //    farebbe cercare a mano nell'elenco.
        if (idsFalliti !== null) onArchiviato?.(idsFalliti)
      },
    })
  }

  // Scopo: rimette N righe nell'elenco. Nessuna conferma: annulla un gesto,
  //        non ne compie uno nuovo.
  function ripristinaRighe(righe) {
    return _esegui(ripristina, righe.map((r) => r.id), {
      chiaveOk: 'strumenti.code.ripristina_esito',
      chiaveParziale: 'strumenti.code.ripristina_esito_parziale',
    })
  }

  // Scopo: le due voci di kebab per una riga, da concatenare a quelle proprie
  //        della scheda. Si escludono a vicenda: una riga archiviata offre
  //        «Ripristina», una non archiviata «Archivia».
  //
  // ⛔ IL PREDICATO E' `rigaCodaViva`, il BB che gia' esiste, e NON un terzo
  //    elenco di stati. «Viva» ha UNA definizione — PENDING o IN_CORSO — ed e'
  //    la stessa che conta il badge in topbar e che il trigger applica a
  //    database: due letture della stessa coda che non concordano sono gia'
  //    state un difetto.
  // ⭐ E si DISABILITA col motivo, non si nasconde: cio' che dipende dallo
  //    STATO puo' cambiare da solo mentre l'operatore guarda: un'azione che
  //    sparisce non spiega niente, una grigia col motivo dice quando tornera'.
  //    (Il permesso invece nasconde: `action`, sopra.)
  function azioniArchiviazione(row) {
    const viva = rigaCodaViva(row.stato)
    return [
      {
        key: 'archivia',
        label: t('strumenti.code.azione_archivia'),
        icon: MANAGE_ICONS.ARCHIVIA,
        action: AZIONE_CODE_MANAGE,
        visible: row.archiviato !== true,
        disabled: viva || isReadonly.value,
        tooltip: viva
          ? t('strumenti.code.archivia_bloccato_hint')
          : t('strumenti.code.azione_archivia_hint'),
        command: () => archiviaRighe([row]),
      },
      {
        key: 'ripristina',
        label: t('strumenti.code.azione_ripristina'),
        icon: MANAGE_ICONS.TOGLI,
        action: AZIONE_CODE_MANAGE,
        visible: row.archiviato === true,
        disabled: isReadonly.value,
        tooltip: t('strumenti.code.azione_ripristina_hint'),
        command: () => ripristinaRighe([row]),
      },
    ]
  }

  return { azioniArchiviazione, archiviaRighe, loading }
}
