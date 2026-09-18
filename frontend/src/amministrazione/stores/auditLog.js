// Pinia store per il log di audit globale (sola lettura, `storico.audit_log`).
//
// Nato con la conversione della pagina a `<ListaConfigurabile>` (2026-08-02):
// prima i filtri e la paginazione vivevano dentro `AuditLogView.vue`, ma lo
// scaffolding `useListaConfigurabilePage` vuole uno store che possieda
// `items`/`totalRecords`/`loading`/`filters`/`fetchList`.
//
// ⭐ Dal 2026-09-18 e' `createListaStore` e basta: era l'unico store del
//    frontend con il ciclo di fetch scritto INTERAMENTE a mano — `items`,
//    `loading`, un `fetchSeq` anti-race suo, `hasSearched` dichiarato apposta
//    per `useSearchTable` — piu' la copia del `buildParams`. Tutto cio' che
//    faceva lo fa il BB, compresa la guardia di versione che qui era un
//    contatore locale.
// ⚠️ `search` esiste solo perche' `useSearchTable` ci scrive dentro: il BE
//    audit NON ha ricerca testuale (`AuditLogView` non mostra la casella, e nel
//    seed tutte le colonne hanno `ricercabile_full=f`). Il BB la manderebbe
//    solo da tre caratteri, e da quella pagina non ci arriva mai.

import { createListaStore } from '../../core/stores/createListaStore'
import { getAuditLog } from '../api/amministrazione'
import { defaultFiltroDataDaString } from '../../core/utils/date'

export const useAuditLogStore = createListaStore('amm-audit-log', {
  fetchPage: getAuditLog,
  // Parte piena: e' un registro, non una ricerca.
  startsEmpty: false,
  filterDefaults: {
    tabella: null,
    // Floor temporale standard delle liste: oggi-60gg riportato al 1° del mese
    // (`feedback_filtro_data_liste`). Sostituisce il "ultimo mese" calcolato a
    // mano che stava nel .vue — stessa intenzione, ma dalla fonte unica.
    data_da: defaultFiltroDataDaString(),
    data_a: null,
  },
  // Allineato all'`ordinamento_default` del preset `audit_log_default`
  // (seed `lista_preset`, riga 32): il piu' recente in cima. Il ripiego del
  // verso segue: e' una lista di eventi, si legge dal piu' recente.
  orderBy: 'timestamp',
  orderDir: 'desc',
  orderDirDefault: 'desc',
})
