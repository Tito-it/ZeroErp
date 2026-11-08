// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I vocabolari CHIUSI del dominio magazzino che il frontend deve
//        conoscere, e la configurazione delle DUE FAMIGLIE del documento
//        interno (inventario e rettifica), in un punto solo.
// Note: ⛔ QUI STANNO SOLO I VOCABOLARI CHE **NON** HANNO UN CATALOGO. Sono
//       `CHECK` del database o vocabolari di una funzione: non esiste una
//       tabella da interrogare, quindi il frontend una copia la tiene per
//       forza — e allora la tiene in UN posto, dove si vede. Gli stati del
//       documento interno NON hanno una tabella di stato (D-L2-h del brief
//       del motore: «matrice nel guard, non tabella»), quindi stanno qui e
//       sono lo specchio dichiarato di `chk_mag_inventari_stato` — lo stesso
//       specchio che il backend pinna con `valori_check`
//       (`STATI_DOCUMENTO_INTERNO` in `magazzino_service.py`).
//       ⚠️ Ogni etichetta si risolve **fail-visible** (`labelOrCode`, in
//       `etichette.js`): un valore che il backend aggiunge e i locales non
//       conoscono si vede come CODICE, non come cella vuota.
//       ⚠️ Nessun import di pinia o di store: questo modulo lo carica anche il
//       ROUTER (per `FAMIGLIA` nel `meta` delle rotte), che non deve tirarsi
//       dietro uno store per leggere una costante. Gli store delle famiglie
//       stanno in `stores/documentiInterni.js`, che LEGGE da qui.
// ------------------------------------------------------------

import { TAB_ENTITIES } from '../core/constants'

// Gli stati del documento interno — `CHECK chk_mag_inventari_stato` /
// `chk_mag_rettifiche_stato` (una famiglia, la stessa matrice:
// `DRAFT → CONFIRM | CANCEL; CONFIRM → POSTED | CANCEL | DRAFT`).
// ⚠️ La MATRICE non sta qui: vive nel guard di transizione del database, e
//    quando servira' a video (le azioni di stato del drawer) arrivera' dalla
//    capability (R-1 del brief 2-bis), mai riscritta nel frontend.
export const STATO_DOCUMENTO = Object.freeze({
  DRAFT: 'DRAFT',
  CONFIRM: 'CONFIRM',
  POSTED: 'POSTED',
  CANCEL: 'CANCEL',
})
export const STATI_DOCUMENTO_INTERNO = Object.freeze(Object.values(STATO_DOCUMENTO))

// Gli esiti del PIANO di un inventario (`magazzino.fn_inventario_piano.esito`):
// che cosa il posting scrivera' per ogni posizione. Vocabolario della funzione,
// senza tabella. `NON_CONTATA` e' il caso di Tid (D-L2-n): a registro c'e'
// merce che il conteggio non ha nominato. `NON_POSTABILE` ferma TUTTO.
export const ESITO_PIANO = Object.freeze({
  INV_INIZIALE: 'INV_INIZIALE',
  RETT_POS: 'RETT_POS',
  RETT_NEG: 'RETT_NEG',
  INVARIATA: 'INVARIATA',
  NON_CONTATA: 'NON_CONTATA',
  NON_POSTABILE: 'NON_POSTABILE',
})
export const ESITI_PIANO = Object.freeze(Object.values(ESITO_PIANO))

// Le sorgenti di un movimento (`config.sorgenti.codice_interno`): il tipo del
// DOCUMENTO che ha mosso la merce — la sua chiave e' `sorgente_id`, la riga
// `sorgente_riga` (giro M.1 di brief-db-sorgente-documento-e-riga, 2026-11-08;
// fino ad allora il registro portava il tipo della RIGA, `INVENTARIO_RIGA` …).
// Sono i documenti che scrivono sul registro, di questo dominio e della
// vendita: il filtro li propone tutti, e la riga di un documento POSTED apre il
// registro sul proprio. ⚠️ Una sorgente fuori da qui si vede in colonna col
// suo codice.
export const SORGENTE_MOVIMENTO = Object.freeze({
  INVENTARIO: 'INVENTARIO',
  RETTIFICA: 'RETTIFICA',
  TRASFERIMENTO: 'TRASFERIMENTO',
  DDT_VENDITA: 'DDT_VENDITA',
  RESO_VENDITA: 'RESO_VENDITA',
  EVENTO_ASSET: 'EVENTO_ASSET',
})
export const SORGENTI_MOVIMENTO = Object.freeze(Object.values(SORGENTE_MOVIMENTO))

// ⭐ LE DUE FAMIGLIE DEL DOCUMENTO INTERNO (Q-1, decisa da Tid il 2026-09-18:
//    UNA implementazione, due configurazioni — il DB le ha gia' fatte una
//    famiglia, e il backend le monta da `FamigliaDocumentoInterno`). Le
//    differenze fra inventario e rettifica sono TUTTE qui: lista, vista, i18n,
//    il nome della quantita' di riga, il motivo, il piano. Drawer, dialog di
//    apertura, form di riga e search table sono UNO per famiglia e leggono da
//    qui — un `if (famiglia === 'inventari')` in un componente e' una
//    differenza scappata dalla sede.
// ⚠️ `campoQta` e' il nome FISICO della colonna (`qta_contata` / `qta_delta`),
//    come nel `types.py` del backend: e' cio' che la lista a catalogo chiede
//    alla riga e cio' che il payload porta — due chiavi, non una `qta`.
export const FAMIGLIA = Object.freeze({
  INVENTARI: 'inventari',
  RETTIFICHE: 'rettifiche',
})

export const FAMIGLIE = Object.freeze({
  [FAMIGLIA.INVENTARI]: Object.freeze({
    codice: FAMIGLIA.INVENTARI,
    singolare: 'inventario',
    // Il segmento delle rotte API (`/magazzino/inventari/…`) e della pagina.
    rotta: 'magazzino-inventari',
    listaCodice: 'magazzino.inventari',
    listaRigheCodice: 'magazzino.inventario_righe',
    // La radice i18n della famiglia (titoli, «Nuovo», ricerca…).
    i18n: 'magazzino.inventari',
    campoQta: 'qta_contata',
    // La regola della quantita', specchio del `CHECK` di riga
    // (`chk_mag_inventario_righe_qta_contata_non_neg`): una posizione contata
    // VUOTA e' un dato, il negativo no. `qtaMin` e' il `min` dell'InputNumber.
    qtaZeroAmmessa: true,
    qtaMin: 0,
    // Solo la riga di rettifica porta il `motivo`.
    conMotivo: false,
    // Solo l'inventario ha `descrizione` in testata.
    conDescrizione: true,
    // Solo l'inventario ha il piano (`fn_inventario_piano`).
    haPiano: true,
    // La chiave cross-tab della famiglia (producer: i verbi dello store;
    // consumer: `useTabFreshness` della lista). Dall'enum, mai un literal.
    tabEntity: TAB_ENTITIES.INVENTARIO,
    // Il parametro del registro dei movimenti per il deep-link dal POSTED.
    filtroMovimenti: 'inventario_id',
    // La sorgente dei movimenti che il posting scrive: il tipo del documento.
    sorgente: SORGENTE_MOVIMENTO.INVENTARIO,
  }),
  [FAMIGLIA.RETTIFICHE]: Object.freeze({
    codice: FAMIGLIA.RETTIFICHE,
    singolare: 'rettifica',
    rotta: 'magazzino-rettifiche',
    listaCodice: 'magazzino.rettifiche',
    listaRigheCodice: 'magazzino.rettifica_righe',
    i18n: 'magazzino.rettifiche',
    campoQta: 'qta_delta',
    // `chk_mag_rettifiche_qta_non_zero`: il delta e' firmato (negativo scarica)
    // e lo zero non e' una correzione.
    qtaZeroAmmessa: false,
    qtaMin: null,
    conMotivo: true,
    conDescrizione: false,
    haPiano: false,
    tabEntity: TAB_ENTITIES.RETTIFICA,
    filtroMovimenti: 'rettifica_id',
    sorgente: SORGENTE_MOVIMENTO.RETTIFICA,
  }),
})

// Le schede della vista «Disponibilita'»: per magazzino (la vista
// `vw_disponibilita`) e per articolo (la somma sui magazzini visibili).
// ⚠️ Contratto fra file che non si vedono (`?tab=`): scritte come literal, un
//    refuso non fallisce e la scheda di default si apre in silenzio.
export const TAB_DISPONIBILITA = Object.freeze({
  MAGAZZINI: 'magazzini',
  ARTICOLI: 'articoli',
})

// Le anagrafiche di magazzino (piano anagrafiche-fuori-dal-pannello-config):
// il `rel` del lookup generico dei magazzini — lo montano i picker del
// documento interno e lo invalida lo store dei magazzini a ogni scrittura — e
// la chiave di cache del lookup delle ubicazioni DI UN magazzino (endpoint
// dedicato, filtrato sul padre: una chiave per magazzino, o il primo montato
// vincerebbe in silenzio sugli altri).
export const LOOKUP_REL_MAGAZZINI = 'magazzino.magazzini'

// La causale di magazzino (`magazzino.causali.codice_interno`) che fa di una
// bolla un TRASFERIMENTO fra depositi: la bolla vuole anche il magazzino di
// arrivo. E' la stessa regola del DB (`vendite.trgfn_ddt_guard_magazzino`,
// `script.fn_check_ddt_merce`); la causale di trasporto la porta nel lookup
// (`causale_magazzino`, Lotto 3 D-L3-g).
export const CAUSALE_MAGAZZINO_TRASFERIMENTO = 'TRASF_OUT'
export function chiaveLookupUbicazioni(magazzinoId) {
  return `magazzino.ubicazioni.${magazzinoId}`
}

// L'azione di processo che autorizza il VERBO IRREVERSIBILE (R-3 del brief
// 2-bis, a catalogo dal 2026-09-23): una sola per la famiglia, perche' il
// verbo e' lo stesso su inventari e rettifiche.
// ⚠️ Qui serve solo a NASCONDERE il pulsante a chi non ce l'ha: il cancello
//    vero e' il backend (`post_permission` su `.../registra/`), e resta
//    fail-closed finche' un profilo non porta l'azione.
export const AZIONE_REGISTRA_MAGAZZINO = 'registra_magazzino'

// L'azione dei BLOCCHI manuali (Lotto 3 D-L3-j): aprire e liberare. Come sopra,
// qui serve a NASCONDERE il gesto a chi non ce l'ha; il cancello vero e' il
// backend (`post_permission`) e, dietro, il verbo DB.
export const AZIONE_BLOCCA_MERCE = 'blocca_merce'
