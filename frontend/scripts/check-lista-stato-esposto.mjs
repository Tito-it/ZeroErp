// Scopo: verifica che ogni store che usa DIRETTAMENTE il BB
//        `useListaEmptyStateFetch` ne esponga lo stato INTERO (`...lista`),
//        invece di elencarne i ref a mano.
//
// Perche' esiste (2026-09-26, regola del 2): i ref del BB crescono —
// `ricercaFull`, poi `ricercaMinCaratteri`, poi `ricercaCambiaLaRichiesta` —
// e a ogni giro andavano ricopiati nella destrutturazione e nel `return` di
// ogni store scritto a mano. Chi se ne dimenticava non dava errore: con
// `ricercaCambiaLaRichiesta` assente `useSearchTable` risponde `true` e la
// lista torna a ricaricare a ogni tasto. Cinque store erano allineati, cinque
// no. Questo script rende rumorosa la sesta copia.
//
// La forma richiesta:
//   const lista = useListaEmptyStateFetch({ ... })
//   const { fetchList } = lista          // solo cio' che lo store usa dentro
//   return { ...lista, filters, ... }
//
// ⚠️ Esclusi i BB di `core/composables` (`useListaStoreCore` riceve i ref uno
//    per uno PER MESTIERE: ne rinomina e ne avvolge alcuni) e gli spec.
//
// Uso:
//   cd frontend && node scripts/check-lista-stato-esposto.mjs
// Exit 0 = tutto verde. Exit 1 = almeno uno store fuori forma.

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const RADICE = new URL('../src/', import.meta.url).pathname

// Scopo: tutti i .js sotto `dir`, ricorsivo.
function fileJs(dir) {
  return readdirSync(dir).flatMap((nome) => {
    const p = join(dir, nome)
    if (statSync(p).isDirectory()) return fileJs(p)
    return p.endsWith('.js') ? [p] : []
  })
}

const fuoriForma = []
let esaminati = 0
for (const p of fileJs(RADICE)) {
  const rel = relative(RADICE, p)
  if (rel.startsWith('core/composables/') || rel.endsWith('.spec.js')) continue
  // Commenti tolti: lo store spiega `...lista` in un commento, e un
  // controllo sul testo grezzo si farebbe ingannare proprio da quello.
  const src = readFileSync(p, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
  if (!src.includes('useListaEmptyStateFetch(')) continue
  esaminati += 1
  const motivi = []
  if (!/const lista = useListaEmptyStateFetch\(/.test(src)) motivi.push('lo stato non e\' in `const lista = useListaEmptyStateFetch(...)`')
  if (!/\.\.\.lista\b/.test(src)) motivi.push('il `return` non spalma `...lista`')
  if (motivi.length) fuoriForma.push(`${rel}: ${motivi.join('; ')}`)
}

if (fuoriForma.length) {
  console.log('[KO] store che elencano a mano lo stato di useListaEmptyStateFetch:')
  for (const riga of fuoriForma) console.log(`  - ${riga}`)
  process.exit(1)
}
console.log(`[ok] ${esaminati} store espongono lo stato intero di useListaEmptyStateFetch`)
