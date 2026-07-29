# Contratto context ↔ template — Fattura

## Scopo

Descrivere il **contratto** fra il context builder `FATTURA`
(`apps/vendite/services/fattura_document_context_builder.py`) e il template
documentale `Fattura` (`documenti.template_documenti`), cioè quali chiavi il
template può leggere e da dove arrivano.

> A differenza di [template_contratto_iniziale](template_contratto_iniziale.md)
> e [template_offerta_iniziale](template_offerta_iniziale.md), che pubblicano
> l'HTML iniziale da copiare, qui il template esiste già ed è pubblicato: il
> documento serve a evitare che il contratto si rompa **di nuovo**.

## Contesto

**Questo contratto si è rotto tre volte, e nessuna delle tre ha prodotto un
errore.** È la ragione per cui esiste questa pagina.

| # | Difetto | Sintomo | Chiuso |
|---|---|---|---|
| 1 | Il template leggeva `quantita`/`sconto_perc`/`importo_riga`, il repository esponeva `qta`/`sconto_percentuale`/`imponibile_riga` | tre colonne su otto a `-` su **ogni** fattura | 2026-07-28 |
| 2 | `imponibile_riga` non era scritto da nessuno | totali a **0,00 €** su ogni fattura emessa | 2026-07-28 |
| 3 | `{{ valore or "-" }}` su campi numerici: `Decimal('0.000000')` è **falsy** | un importo o una quantità pari a **zero** stampata come `-` | 2026-07-29 |

Il meccanismo comune: il template legge il context con `.get()`, che
**disinnesca `StrictUndefined`**. Una chiave sbagliata non è un errore di
render — è un trattino. Il PDF si genera, la coda di stampa passa a `FATTO`, e
nulla segnala il problema.

**Il presidio** è lo smoke
`backend/scripts/tests/smoke-fatturazione-render-stampa.py`: rende il template
**pubblicato** con un context **reale** e pretende che ogni valore presente nel
context arrivi nella cella corrispondente. Contiene anche un'auto-verifica a
mutazione controllata (caso 8): rimuove una chiave dal context e pretende che il
controllo se ne accorga — un presidio che non può fallire non presidia nulla.

## Input

Il context è prodotto da `FatturaDocumentContextBuilder.build_context(fattura_id)`
e ha quattro rami più `_meta`.

### `righe` — il ramo che si è rotto

⚠️ **Fonte: `vendite.vw_fattura_righe_esposte`, NON la tabella
`vendite.fatture_righe`.** È la rappresentazione unica del documento (regola
R17): la stessa vista deve essere letta da PDF, XML SDI e portale, altrimenti
due uscite dello stesso documento mostrano dettagli diversi — totali uguali,
quindi nulla di irregolare, ma una divergenza che nessuno ha deciso.

| Chiave | Tipo | Origine | Note |
|---|---|---|---|
| `id` | int \| None | `vw.fatture_righe_id` | **None** sulle righe `KIT_PADRE`: non esistono in tabella |
| `tipo_riga` | str | `vw.tipo_riga` | `NORMALE` · `KIT_PADRE` · `KIT_COMPONENTE` |
| `livello` | int | `vw.livello` | `0` padre e righe semplici, `1` componenti |
| `riga_nr` | int | `vw.riga_nr` | |
| `articolo_id`, `articolo_codice`, `articolo_descrizione` | | JOIN `catalogo.articoli` | |
| `descrizione` | str | `vw.descrizione` | |
| `uom_id`, `uom_codice` | | JOIN `catalogo.unita_misura` | |
| **`quantita`** | Decimal | `vw.qta` | ⚠️ alias: la colonna DB si chiama `qta` |
| `prezzo_unitario` | Decimal \| None | `vw.prezzo_unitario` | **None** sui `KIT_COMPONENTE` |
| `sconto_percentuale` | Decimal \| None | `vw.sconto_percentuale` | |
| `iva_id`, `iva_codice`, `iva_descrizione`, `iva_aliquota` | | JOIN `config.iva` | |
| `iva_natura` | str \| None | `vw.iva_natura` | per le righe non imponibili |
| **`importo_riga`** | Decimal \| None | `vw.imponibile` | ⚠️ doppio alias: colonna `imponibile_riga`, vista `imponibile`. **None** sui `KIT_COMPONENTE` |

**I nomi sono di CONTRATTO, non di colonna.** `quantita` e `importo_riga` sono
gli stessi che espongono `ordini_repository`, `ddt_repository` e
`preventivi_repository`: i template restano uniformi fra tipi documento. Il
context fattura era l'unico a esporre i nomi di colonna grezzi — era il
difetto 1.

**Ordinamento**: per `ordinamento`, **non** per `riga_nr`. È la colonna che
tiene ogni componente subito sotto il proprio padre.

### `fattura`, `cliente`, `riepilogo_iva`, `scadenze`

Prodotti da `_shape_fattura` / `_shape_cliente` e dai repository di riepilogo e
scadenze. I totali stanno in `fattura.totali` (`imponibile`, `imposta`, alias
`iva`, `sconto`, `bollo`, `arrotondamento`, `documento`, `a_pagare`,
`valuta_codice`, `tasso_cambio`).

## Output

HTML renderizzato da Jinja2 con `StrictUndefined`, poi PDF via WeasyPrint
(`apps/documenti/services/render_service.render_pdf`).

## Regole

1. **Mai `{{ valore or "-" }}` su un campo numerico.** `Decimal('0.000000')`,
   `0` e `Decimal(0)` sono **falsy**: un importo o una quantità pari a zero
   verrebbero stampati come assenti. Zero è un valore — il requisito D1 ammette
   esplicitamente righe con `qta = 0` e importo `0`. Usare il test esplicito:

   ```jinja
   {% if r.get("importo_riga") is not none %}{{ r.get("importo_riga") }}{% else %}-{% endif %}
   ```

   Sui campi **testuali** `or` va bene: una descrizione vuota è davvero assente.

2. **Ogni chiave letta dal template deve esistere in questa pagina.** Se serve
   un campo nuovo, si aggiunge prima al context builder e qui, poi al template —
   mai il contrario: `.get()` non protesta.

3. **Il dettaglio kit si rende da `tipo_riga` e `livello`**, mai interpretando
   `segment_key`. Un `KIT_PADRE` porta il totale del kit; i `KIT_COMPONENTE`
   sono righe **descrittive**, con quantità e UoM ma senza prezzo né importo —
   il loro valore è già dentro il totale del padre, e stamparlo lo conterebbe
   due volte.

4. **Le colonne monetarie dei componenti restano vuote, non a `-`**: un
   trattino si legge come «componente a costo zero».

5. **Una versione `PUBBLICATA` è immutabile** (trigger
   `trgfn_template_documenti_versioni_protect_pubblicata`). Per modificarla:
   `clone_versione` → `update_versione` → `pubblica_versione`
   (`TemplateVersioniAdminService`). La funzione DB chiude e obsoleta da sola la
   versione precedente.

6. **Dopo ogni nuova versione, rieseguire lo smoke.** È l'unico controllo che
   guarda dentro al documento prodotto.

## Dipendenze DB

- `vendite.vw_fattura_righe_esposte` — righe esposte (rappresentazione unica)
- `vendite.fatture`, `vendite.fatture_riepiloghi_iva`, `vendite.fatture_scadenze`
- `catalogo.articoli`, `catalogo.unita_misura`, `config.iva`, `config.iva_natura`
- `documenti.template_documenti` / `template_documenti_versioni`

⚠️ `vendite.fatture` è **RLS**: senza contesto operatore il builder solleva
`E_NOT_FOUND` su una fattura che esiste. Vale per gli smoke e per ogni lettura
fuori dal ciclo di richiesta web.

## Note di migrazione

- **v1** (2026-07-13) — chiavi righe disallineate e `sconto_perc` inesistente.
- **v2** (2026-07-28) — allineata al contratto; aggiunto il dettaglio kit
  (`tipo_riga`/`livello`, CSS `.row-componente`); `sconto_perc` →
  `sconto_percentuale`.
- **v3** (2026-07-29) — rimosso `or "-"` da quantità, prezzo, importo di riga e
  dai quattro totali di testata: lo zero non è più stampato come assente.

Storia completa: `docs/it/dev/work-done/brief-fix-importi-riga-fattura-zero.md`
e `docs/it/dev/work-done/brief-be-fe-importi-riga-fattura.md`.
