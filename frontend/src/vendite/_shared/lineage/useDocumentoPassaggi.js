// Scopo: Fetch unica dei "passaggi" (genealogia/lineage) di un documento
// vendite, condivisa dai due consumatori della stessa risposta (regola del 2,
// 2026-07-25): la barra `DocumentoCollegamentiBar` (chip tipizzati dei
// collegamenti diretti) e il contenuto `LineagePassaggiContenuto` (grafo
// completo, in dialog o inline nei drawer commessa).
//
// PERCHE' una sorgente sola: i chip dicono "2 DDT · 1 Reso" e la dialog mostra
// gli stessi documenti. Se i due numeri venissero da query diverse potrebbero
// divergere (una fresca, una stantia) — e un contatore che smentisce il
// dettaglio è peggio di nessun contatore. Qui la stessa risposta alimenta
// entrambi per costruzione.
//
// Il QUANDO leggere sta in `useLetturaDocumento` (2026-10-13): con `versione`
// (il dettaglio del drawer ospite) i passaggi si rileggono a ogni rilettura del
// drawer — nessun drawer deve piu' ricordarsi di chiamare `reload`.
//
// Config: `basePath` (path lista del dominio, es. '/vendite/ordini'), `docId`
// (ref/getter della pk di dominio; null in CREATE → nessuna fetch) e
// `versione` (facoltativa: senza, si legge al solo cambio di documento).
import { toValue } from 'vue'
import { getPassaggi } from './lineageApi'
import { useLetturaDocumento } from '../../../core/composables/useLetturaDocumento'

export function useDocumentoPassaggi(basePath, docId, versione) {
  const { dati, caricati, loading, rileggi } = useLetturaDocumento(
    (id) => getPassaggi(toValue(basePath), id),
    { docId, versione },
  )
  return { data: dati, loaded: caricati, loading, reload: rileggi }
}
