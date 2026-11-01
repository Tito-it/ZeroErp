## 📘 Documentazione Concettuale – Tabella `magazzino.causali`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove il verso viene fatto rispettare
> * [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi) — le attese, con lo stesso verso
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'altro catalogo che guida la primitiva
>
> Approfondimento funzioni:
>
> * [magazzino.trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso) — il guard del verso
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva che legge la causale

---

### 🎯 Scopo Principale

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

Il guard [trgfn_movimenti_guard_verso](/dbzero/magazzino/funzioni/trgfn_movimenti_guard_verso)
rifiuta un movimento (e un atteso) la cui quantità non ha il segno della causale. La scelta è
**verificare**, non derivare: la quantità resta un dato scritto, e chi sbaglia il verso viene
fermato.

Lo `0` non esiste: il CHECK ammette solo `−1` e `+1`, e la colonna non ha default — chi
crea una causale dice il verso.

---

### Lo storno ha causali sue

Sotto il guard del verso, il movimento contrario non può portare la causale dell'originale
(`SCARICO_VEN` è −1, lo specchio è +1). Due causali generiche, `STORNO_POS` e `STORNO_NEG`:
*che cosa* è stornato lo dice il legame `movimenti.storno_di_movimento_id`, non la causale.

---

### Come la primitiva legge la causale

La primitiva legge la causale per `codice_interno`: `segno` per il verso, `is_rettifica` per
ignorare i blocchi (una rettifica registra un fatto, un blocco è una promessa: il fatto vince,
il fisico resta), `consente_stock_negativo` per esonerare dal controllo di disponibilità.
Nessuna causale del seed consente lo stock negativo: il pgTAP costruisce il caso.

`is_installazione_asset` è la sola marca che lega la causale al ciclo di vita dell'asset; oggi
nessuna funzione la legge, e il suo consumatore nascerà con le operazioni sugli eventi asset.

⛔ **Una regola per causale, non un asse in più.** La valorizzazione è **una** (media
ponderata, ri-somma dei costi scritti) e non dipende dalla causale; lotto e seriale li
pretende l'**articolo**; la destinazione non è una colonna del movimento. Se un giorno servirà
«questa causale accetta solo questa sorgente», la forma è un `sorgente_tipo_id` sulla causale,
letto dalla primitiva.

---

### Vocabolario, uguale per tutti

La tabella è **fuori dal perimetro RLS**: le causali sono parte del contratto del software e
valgono identiche per ogni emittente. `codice_interno` è la chiave su cui il codice confronta
ed è immutabile; una causale con movimenti o attese non si spegne.

---

### Test

* `db/pgtap/magazzino/test-causali-e-sorgenti-seed-v1.sql` — le causali del seed e il
  catalogo delle sorgenti.

---

### Note di migrazione

* 2026-09-15 — `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.1; analisi carico e scarico,
  §4, M-1): `segno` diventa un meccanismo (prima nessun calcolo lo leggeva e la quantità
  doveva arrivare firmata senza garanzie); sparisce il valore `0`; escono
  `impatto_valorizzazione`, `richiede_lotto`, `richiede_seriale`, `richiede_magazzino_dest`,
  `abilita_billing`, `richiede_odl`, `contabilizza_cdc` (dichiarate, seminate, lette da
  nessuno), `ambito_causale_id` e la tabella `magazzino.ambito_causale` (un quarto asse che
  nessuna funzione leggeva).
* 2026-09-18 — la primitiva di scrittura (Lotto 2) comincia a leggere `segno`,
  `is_rettifica` e `consente_stock_negativo`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
