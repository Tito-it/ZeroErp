# Collaudo in-app · La casella di ricerca segue il catalogo

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il piano: il *perché* sta nei due brief
> chiusi, [brief-be-ricerca-full-liste-residue.md](brief-be-ricerca-full-liste-residue.md)
> (§7-bis, §13.4, §13.5) e
> [brief-db-ricerca-full-colonne-da-accendere.md](brief-db-ricerca-full-colonne-da-accendere.md).
> Qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** Il pezzo condiviso (`store.ricercaFull` + `FiltriLista`)
> è provato da `FiltriLista.spec.js` (test 13) e `ricercaFull.spec.js`, ma
> **nessun test monta una pagina vera** con la configurazione del backend: che
> la casella compaia o sparisca secondo il catalogo, e che la ricerca trovi,
> l'ha visto solo chi l'ha scritto. Un difetto qui non dà errori: una casella
> che manca, o una casella che non filtra niente.
>
> **Stato**: ✅ **chiuso il 2026-10-06** — tutti i passi spuntati da Tid (scritto il 2026-09-24).
> **Ambiente**: sviluppo (`dbdev`). **Utente**: un operatore con lettura su
> magazzino e pagamenti, e un amministratore per il passo 3.

---

## 1. Le nove liste che prima non avevano la casella

Per ognuna: la casella c'è; un termine di **tre** caratteri preso da una riga a
video la trova; con due caratteri la lista **non** cambia.

| ✓   | Dove                                                                                            | Lista                           |
| --- | ----------------------------------------------------------------------------------------------- | ------------------------------- |
| X   | Magazzino → drawer di un inventario, tab righe                                                  | `magazzino.inventario_righe`    |
| X   | Magazzino → drawer di una rettifica, tab righe                                                  | `magazzino.rettifica_righe`     |
| X   | Magazzino → inventario → dialog del piano                                                       | `magazzino.inventario_piano`    |
| X   | Magazzino → Movimenti                                                                           | `magazzino.movimenti`           |
| X   | Pagamenti → Distinte                                                                            | `pagamenti.distinte`            |
| X   | Pagamenti → drawer di una distinta, righe (anche l'**export**: il file porta la stessa ricerca) | `pagamenti.distinta_righe`      |
| X   | Pagamenti → Coda del riconciliatore                                                             | `pagamenti.righe`               |
| X   | Pagamenti → Rate fuori capienza                                                                 | `pagamenti.rate_fuori_capienza` |
| X   | Pagamenti → Eccedenze                                                                           | `pagamenti.eccedenze`           |

**Se la casella manca**: la configurazione ha `ricerca_full: false` per
quell'operatore (`GET /ui/liste/<codice>/config`). Controllare le colonne
`ricercabile_full` della lista e i permessi di colonna, prima del codice.

## 2. Una lista su compatto

X Sotto i 1024px (o su un tablet) la casella resta **fuori** dal drawer dei
filtri, in toolbar (slot `#sempre`).

## 3. L'amministratore spegne tutte le colonne

X Da amministrazione liste, su una delle nove: `ricercabile_full = f` su
**tutte** le colonne. Riaprire la lista: la casella **non c'è**.

X Con la lista aperta su un `?search=…` (deep-link): spente le colonne, il
termine si svuota e la lista torna intera. **Se resta vuota**:
`useListaConfigurabilePage.onConfigLoaded` non ha svuotato `searchText`.

X Riaccendere le colonne: la casella torna.

## 4. Nessun lampeggio

X Aprendo una lista che cerca, la casella c'è **da subito**, senza sparire e
ricomparire mentre arriva la configurazione (`null` la lascia a video).
