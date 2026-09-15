## 📘 Documentazione Concettuale – Tabella `magazzino.causali`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove il verso viene fatto rispettare
> • [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'altro catalogo che guida la primitiva
>
Approfondimento funzioni:
> • [magazzino.trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.1) · analisi carico e scarico (§4, M-1)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il catalogo delle causali di movimento.** La causale dice tre cose di un movimento: il
**verso** (`segno`: `+1` entrata, `−1` uscita), se è una **rettifica** (`is_rettifica`), se
ammette lo **stock negativo** (`consente_stock_negativo`). È uno dei due cataloghi che
guidano la primitiva di scrittura; l'altro è l'articolo (lotto, seriale, gestito a magazzino).

Sedici righe, caricate dal seed (`causali.csv`), uguali su ogni installazione:

| Codice | Verso | Che cosa registra |
|---|---:|---|
| `CARICO_ACQ` | +1 | carico da bolla del fornitore |
| `SCARICO_VEN` | −1 | scarico per bolla di vendita |
| `CARICO_RESO_VEN` | +1 | carico da reso del cliente |
| `SCARICO_RESO_ACQ` | −1 | scarico per reso al fornitore |
| `TRASF_OUT` / `TRASF_IN` | −1 / +1 | le due righe di un trasferimento |
| `RETT_POS` / `RETT_NEG` | +1 / −1 | rettifica di giacenza |
| `INV_INIZIALE` | +1 | inventario iniziale (il primo carico): non è una rettifica |
| `ODL_USCITA_MAT` / `ODL_ENTRATA_MAT` | −1 / +1 | materiali per e da un ordine di lavoro |
| `ODL_VERSAMENTO_PF` | +1 | versamento del prodotto finito da un ordine di lavoro |
| `ASSET_INSTALL` / `ASSET_RIENTRO` | −1 / +1 | installazione e rientro di un asset |
| `STORNO_POS` / `STORNO_NEG` | +1 / −1 | lo storno di un movimento (specchio di un'uscita / di un'entrata) |

---

### Il verso è un meccanismo, non una dichiarazione

Fino al 14-09 questa pagina segnalava che «`segno` non entra in nessun calcolo»: la quantità
del movimento doveva arrivare già firmata e nulla lo garantiva. Dal 15-09 il guard
[trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso) rifiuta
un movimento (e un atteso) la cui quantità non ha il segno della causale. La scelta è stata la
prima delle due strade allora descritte — **verificare**, non derivare: la quantità resta un
dato scritto, e chi sbaglia il verso viene fermato.

Lo `0` non esiste più: il CHECK ammette solo `−1` e `+1`, e la colonna non ha default — chi
crea una causale dice il verso.

---

### Lo storno ha causali sue

Sotto il guard del verso, il movimento contrario non può portare la causale dell'originale
(`SCARICO_VEN` è −1, lo specchio è +1). Due causali generiche, `STORNO_POS` e `STORNO_NEG`:
*che cosa* è stornato lo dice il legame `movimenti.storno_di_movimento_id`, non la causale.

---

### Che cosa non c'è più (2026-09-15)

* `impatto_valorizzazione` — la valorizzazione è **una** (media ponderata, ri-somma dei
  costi scritti), non una regola per causale; i trasferimenti valorizzano.
* `richiede_lotto`, `richiede_seriale`, `richiede_magazzino_dest` — lotto e seriale li
  pretende l'**articolo**; la destinazione non è una colonna del movimento.
* `abilita_billing`, `richiede_odl`, `contabilizza_cdc` — dichiarate, seminate, lette da
  nessuno.
* `ambito_causale_id` e la tabella `magazzino.ambito_causale` — un quarto asse chiamato
  «ambito» che nessuna funzione leggeva. Se un giorno servirà «questa causale accetta solo
  questa sorgente», la forma è un `sorgente_tipo_id` sulla causale, letto dalla primitiva.

`is_installazione_asset` resta: è la sola marca che lega la causale al ciclo di vita
dell'asset; il suo consumatore nasce col Lotto 2.

---

### Vocabolario, uguale per tutti

La tabella è **fuori dal perimetro RLS**: le causali sono parte del contratto del software e
valgono identiche per ogni emittente. `codice_interno` è la chiave su cui il codice confronta
ed è immutabile; una causale con movimenti non si spegne. Presidio:
`db/pgtap/magazzino/test-causali-e-sorgenti-seed-v1.sql`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
