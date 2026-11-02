// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le etichette dei vocabolari chiusi del dominio incassi, in un posto
//        solo — e le liste di opzioni che ne derivano.
// Note: ⭐ Estratto il 2026-08-28 alla rilettura critica: la stessa riga
//       (`labelOrCode(t, te, \`prefisso_${minuscolo}\`, valore)`) era scritta in
//       OTTO componenti, e tre di quei prefissi comparivano DUE volte ciascuno
//       (verso del credito, tipo di canale, destinazione). Non e' rumore: due
//       copie divergono alla prima chiave rinominata, e la copia rimasta
//       indietro mostra un CODICE dove l'altra mostra una parola — cioe' il
//       difetto si vede solo su una delle due schermate.
//
//       ⛔ E' una FABBRICA, non un oggetto condiviso: ogni chiamante ottiene le
//       proprie funzioni legate al proprio `useI18n()`. Esportare un oggetto
//       gia' costruito legherebbe tutti al `t` del primo montato, e al cambio
//       lingua il secondo consumatore resterebbe indietro **in silenzio**
//       (memoria feedback_estrarre_non_condividere_stato).
//
//       ⚠️ Ogni etichetta e' **fail-visible**: un valore che il backend aggiunge
//       e i locales non conoscono si vede come CODICE, mai come cella vuota.
// ------------------------------------------------------------

import { useI18n } from 'vue-i18n'

import { NATURA_DOC } from '../core/constants'
import { displayDate } from '../core/utils/date'
import { formatCurrency } from '../core/utils/format'
import { labelOrCode } from '../core/utils/i18nLabel'
import {
  CHI_E_IN_CREDITO,
  DESTINAZIONI,
  MOTIVI_FUORI_CAPIENZA,
  ORIGINI_DISTINTA,
  ROTTA_PER_CODA,
  STATI_SISTEMAZIONE,
  TIPI_CANALE,
} from './vocabolari'

export function useEtichettePagamenti() {
  const { t, te } = useI18n()

  // Scopo: la forma unica di tutte le etichette del dominio.
  const etichetta = (prefisso, valore) =>
    labelOrCode(t, te, `${prefisso}_${String(valore).toLowerCase()}`, valore)

  // Scopo: da un vocabolario a una lista di opzioni per `<Select>`.
  const opzioni = (valori, fn) => valori.map((v) => ({ value: v, label: fn(v) }))

  const credito = (v) => etichetta('pagamenti.eccedenze.credito', v)
  const tipoCanale = (v) => etichetta('pagamenti.canali.tipo', v)
  const destinazione = (v) => etichetta('pagamenti.sistemazioni.destinazione', v)
  const statoSistemazione = (v) => etichetta('pagamenti.sistemazioni.stato', v)
  const origineDistinta = (v) => etichetta('pagamenti.distinte.origine', v)
  // Scopo: IL MOTIVO di una rata fuori capienza, letto per NATURA del documento
  //        (P-7, 2026-09-18): il vocabolario resta a DUE codici — cosi' ha
  //        deciso il DB — e la sfumatura della nota di credito la dice
  //        l'etichetta: `SOVRA_INCASSATA` su una NC e' «sovra-rimborsata»
  //        (rimborsato piu' del credito), `MOVIMENTO_CONTRARIO` e' «entrato
  //        invece di uscire» (il cliente ha pagato una nota a suo favore).
  // ⚠️ Senza natura si legge come fattura: e' il default della colonna a DB,
  //    non un dato mancante — la stessa regola di `residuoNegativo`.
  // ⛔ Non un `if` sul segno del residuo: il codice e' lo stesso, cambia cosa
  //    SIGNIFICA, e a dirlo e' la natura. Fail-visible come tutte: una chiave
  //    mancante mostra il CODICE.
  const motivoFuoriCapienza = (v, naturaCodice = null) =>
    etichetta(
      naturaCodice === NATURA_DOC.NOTA_CREDITO
        ? 'pagamenti.rate_fuori_capienza.motivo_nota_credito'
        : 'pagamenti.rate_fuori_capienza.motivo',
      v,
    )
  const coda = (v) => etichetta('pagamenti.righe.coda', v)

  // Scopo: L'ETICHETTA DI UNA RATA — «Rata 2 · 30/09/2026 · 610,00 € ·
  //        restano 400,00 €» — con i pezzi che il chiamante HA: numero e
  //        scadenza sempre, importo e residuo quando ci sono.
  // ⭐ Una sede sola (2026-09-17, rilettura del pezzo B di D19): la stessa
  //    composizione stava nella tendina delle rate, nel blocco «Destinazione»
  //    del form e nella colonna «Rata» del drawer — tre forme della stessa
  //    riga, che a video devono leggersi uguali.
  // ⚠️ Il residuo NEGATIVO si dice a parole, mai «-120,00», che si legge come
  //    un guasto. ⭐ E dal 2026-09-17 (P-5 consegnata: la nota di credito HA
  //    una rata, negativa) la frase segue la NATURA del documento, non il
  //    segno: su una fattura «120,00 di troppo» (e' entrato piu' del dovuto),
  //    su una nota di credito «20,00 da rimborsare» (e' il nostro debito, il
  //    segno e' quello giusto). ⛔ Non un `if` sul segno: il segno e' lo stesso,
  //    cambia cosa SIGNIFICA — e' `residuoNegativo`, una sede per tutti.
  const rata = ({
    numero_rata, data_scadenza, importo = null, residuo = null, natura_doc_codice_interno = null,
  } = {}) => {
    const parti = [t('pagamenti.rata.n', { n: numero_rata })]
    if (data_scadenza) parti.push(displayDate(data_scadenza))
    if (importo != null) parti.push(formatCurrency(importo))
    if (residuo != null) {
      const r = Number(residuo)
      parti.push(
        r < 0
          ? residuoNegativo(r, natura_doc_codice_interno)
          : t('pagamenti.rata.residuo', { importo: formatCurrency(r) }),
      )
    }
    return parti.join(' · ')
  }

  // Scopo: LA FRASE DI UN RESIDUO NEGATIVO, per natura: «da rimborsare» sulla
  //        nota di credito (il segno e' il verso del documento), «di troppo» su
  //        tutto il resto (e' entrato piu' del dovuto). Una sede per la
  //        tendina delle rate, il blocco «Destinazione», la colonna della
  //        distinta e il picker.
  // ⚠️ La natura assente vale «fattura»: e' il default della colonna a DB
  //    (`NATURA_DOC`), non un dato mancante.
  const residuoNegativo = (residuo, naturaCodice = null) => {
    const importo = formatCurrency(Math.abs(Number(residuo)))
    return naturaCodice === NATURA_DOC.NOTA_CREDITO
      ? t('pagamenti.rata.da_rimborsare', { importo })
      : t('pagamenti.rata.di_troppo', { importo })
  }

  return {
    etichetta,
    rata,
    residuoNegativo,
    credito,
    tipoCanale,
    destinazione,
    statoSistemazione,
    origineDistinta,
    motivoFuoriCapienza,
    coda,
    opzioniCredito: () => opzioni(CHI_E_IN_CREDITO, credito),
    opzioniTipoCanale: () => opzioni(TIPI_CANALE, tipoCanale),
    opzioniDestinazione: () => opzioni(DESTINAZIONI, destinazione),
    opzioniStatoSistemazione: () => opzioni(STATI_SISTEMAZIONE, statoSistemazione),
    opzioniOrigineDistinta: () => opzioni(ORIGINI_DISTINTA, origineDistinta),
    // ⚠️ Il FILTRO resta sui due codici letti come fattura (`opzioni` passa il
    //    solo valore, la natura resta al default): filtra per codice, e la
    //    frase per natura vive nella cella, dove la riga la natura la ha.
    opzioniMotivoFuoriCapienza: () =>
      opzioni(MOTIVI_FUORI_CAPIENZA, motivoFuoriCapienza),
    // ⭐ Le code si derivano dalle ROTTE, non da un elenco scritto a mano: cosi'
    //    «quante sono le porte» resta vero per costruzione. `TUTTE` fa parte del
    //    vocabolario dell'endpoint ma non ha una rotta, e offrirla darebbe una
    //    voce che porta in una pagina che non esiste.
    opzioniCoda: () => opzioni(Object.keys(ROTTA_PER_CODA), coda),
  }
}
