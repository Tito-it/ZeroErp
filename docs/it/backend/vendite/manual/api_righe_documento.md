# API Righe documento — la lista configurabile (BB condiviso)

## Scopo

Le righe di un documento di vendita come **lista configurabile**: una pagina
con ricerca e ordinamento, e il suo export. Endpoint identici sui documenti,
generati dal factory condiviso `build_lista_figlia_views`
(`apps/ui/api/lista_figlia_views.py`, lo stesso della distinta del catalogo) sopra il mixin repository
`RigheListaMixin` / `RigheListaCompletaMixin` (`apps/core/db/righe_lista_mixin.py`, in core dal
2026-10-04: lo usa anche la distinta del catalogo) e `RigheDocumentoRepositoryMixin`
(`apps/vendite/db/_righe_repo_mixin.py`). «Leggi prima la testata» e' il BB
`pagina_dopo_testata` (`apps/core/services/testata_guard.py`).

Design-of-record:
[brief-db-liste-righe-documento.md](../../../dev/work-done/brief-db-liste-righe-documento.md).

| Documento | Base path | Lista a catalogo | Sorgente | Ordine del documento |
|---|---|---|---|---|
| Preventivo | `/api/v1/vendite/preventivi/<id>/righe/lista/` | `vendite.preventivo_righe` | `vw_preventivi_righe_dettaglio` | `ordine` |
| Ordine | `/api/v1/vendite/ordini/<id>/righe/lista/` | `vendite.ordine_righe` | `vw_ordini_righe_dettaglio` | `riga_nr` |
| DDT | `/api/v1/vendite/ddt/<id>/righe/lista/` | `vendite.ddt_righe` | `vw_ddt_righe_dettaglio` | `riga_nr` |
| Reso | `/api/v1/vendite/resi/<id>/righe/lista/` | `vendite.reso_righe` | `vw_resi_righe_dettaglio` | `riga_nr` |
| Fattura (sola lettura) | `/api/v1/vendite/fatture/<id>/righe/lista/` | `vendite.fattura_righe` | `vw_fattura_righe_lista` | `ordinamento, riga_nr` |
| Contratto | `/api/v1/vendite/contratti/<id>/righe/lista/` | `vendite.contratto_righe` | funzione `fn_contratto_righe_preview` | `articolo_codice` |
| Offerta | `/api/v1/vendite/offerte/<id>/righe/lista/` | `vendite.offerta_righe` | funzione `fn_offerta_righe_preview` | `articolo_codice` |

### La fattura, e cosa cambia (lotto C, 2026-09-28)

- **Nessuna scrittura** e nessun `…/righe/` completo esposto a parte: la
  lettura completa arriva col dettaglio (`GET fatture/<id>/` → `righe`), dalla
  **stessa vista** della lista;
- **Solo il primo livello**: la riga normale, la parte di plafond, il padre di
  un kit. I componenti esposti di un kit stanno **dentro** il padre
  (`componenti`, jsonb: `fatture_righe_id`, `riga_nr`, `articolo_codice`,
  `descrizione`, `quantita`, `uom_codice`; `componenti_numero`). Paginazione e
  ordinamento spostano il kit intero;
- **La chiave è `riga_key`**, non `id`: `R:<id>` per le righe vere,
  `K:<fattura>:<md5>` per il padre di un kit, che in tabella non c'è. Spareggio
  di ogni ordinamento: `riga_nr`, poi `riga_key`;
- **Nessun filtro `attivo`**: le righe di una fattura non si disattivano;
- **Lo scope dell'operatore** entra nel cancello di testata (`auth_user_id`,
  come dettaglio e giornale): fattura inesistente o fuori scope → `404
  E_FATTURA_NON_TROVATA`, mai una lista vuota;
- il legame riga-riga di una nota di credito porta il numero **parlante** della
  fattura rettificata (`riga_rettificata_documento`) e `riga_rettificata_nr`.

### Il contratto, e cosa cambia (lotto D, 2026-09-30)

- **La sorgente è una funzione**, non una vista: le righe **operative** del
  contratto le calcola `vendite.fn_contratto_righe_preview(contratto)` — con
  listino, le righe del listino con l'overlay delle eccezioni `OVERRIDE` /
  `ESCLUSIONE` più le `AGGIUNTA`; senza listino, le sole `AGGIUNTA`. Una
  sorgente per le due forme: la lista non decide niente per forma. Il BB legge
  `fn(contratto) v` (`_righe_funzione`), senza FK da filtrare;
- **La chiave è `riga_key`**: `L:<articolo>:<uom>` per le righe del listino,
  `A:<id>` per le aggiunte. Le righe del listino non hanno un numero di riga:
  l'ordine di partenza è il **codice articolo**, poi `riga_key`;
- **Nessun filtro `attivo`**: la funzione legge già le sole eccezioni attive;
- **La riga porta le sue azioni**: `azioni` (i verbi che l'origine ammette:
  `SOVRASCRIVI_PREZZO`, `ESCLUDI`, `MODIFICA`, `RIPRISTINA_LISTINO`,
  `RIPRISTINA_ARTICOLO`, `RIMUOVI`) ed `escludi_blocco_codice` (il motivo che
  spegne «Escludi», dalla stessa check del guard). Il backend li trasporta;
- **`prezzo_forzato`** della lista è `override_prezzo` della funzione: il prezzo
  scritto a mano sull'eccezione, vuoto sulle righe che lo prendono dal listino;
- «leggi prima la testata»: contratto inesistente o fuori perimetro → `404
  E_VENDITE_NOT_FOUND`, mai una lista vuota;
- `GET …/righe/` resta la lettura delle righe **persistite** in
  `contratti_righe` (e il `POST` di creazione). L'anteprima intera
  `…/righe-preview/` è ritirata dal 2026-10-04: questa lista ne ha preso il posto.

### L'offerta, gemella del contratto (2026-10-05)

La lista `vendite.offerta_righe` (106) è la **gemella campo per campo** della 103
(brief-db-righe-esclusione-solo-non-si-vende §8.1 e §10.2): stesse colonne,
ordine, preset e attributi. La sorgente `vendite.fn_offerta_righe_preview` e
`fn_contratto_righe_preview` sono involucri dello stesso corpo,
`vendite.fn_documento_righe_preview(documento, id)`: stesse colonne, stessa
`riga_key`, stessi verbi in `azioni`, stesso `escludi_blocco_codice`. Tutto ciò che
è scritto qui sopra per il contratto vale per l'offerta, con tre differenze:

- **l'offerta ha sempre un listino** (`listino_id` NOT NULL): non c'è la forma
  «senza listino». Con una versione non operativa la lista ha le sole eccezioni;
- **le intestazioni hanno chiavi dell'offerta** (`vendite.offerte.col_*`): ogni
  lista di righe ha il suo namespace;
- `GET …/eccezioni/` resta la lettura delle eccezioni **scritte** (e il `POST` di
  creazione); il drawer legge questa lista.

Backend: `OffertaRigheListaRepository` (`RigheListaMixin` sulla funzione),
`OfferteService.list_righe_pagina` (`pagina_dopo_testata`: offerta inesistente
o fuori perimetro → `404 E_VENDITE_NOT_FOUND`), view `ApiOffertaRigheListaView`
ed export dal factory, permesso `("vendite", "offerta_commerciale")`.

## Endpoint

| Metodo / Path | Scopo |
|---|---|
| `GET <base>` | Una pagina delle righe **attive**. Envelope paginato standard (`count`, `page`, `page_size`, `total_pages`, `results`) |
| `GET <base>export/?formato=csv\|xlsx` | Il file delle righe, con la ricerca e l'ordinamento della lista a video (fino a `EXPORT_MAX_ROWS`) |

**Parametri di query** (tutti facoltativi):

- `emittente_fiscale_id` — l'emittente del documento (PK). Lo legge **solo** il
  cancello di perimetro: la lista vive dentro il drawer del documento, che ha
  già il suo emittente, e senza il parametro chi vede più emittenti riceverebbe
  `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`. Non filtra le righe e non allarga
  niente: la visibilità resta allo scope e alla RLS;
- `search` — ricerca libera sulle colonne che il catalogo accende
  (`ricercabile_full`: codice articolo e descrizione; sul reso anche il motivo);
- `order_by` / `order_dir` — un `campo_sorgente` ordinabile della lista.
  **Assente**, l'ordine del documento (tabella sopra), poi la chiave di riga
  (`id`; `riga_key` su fattura e contratto) — lo schema OpenAPI lo legge dal
  repository (`righe_ordine_di_partenza`). Una colonna
  fuori whitelist ripiega sull'ordine del documento. Le date di consegna
  partono DESC quando la direzione manca;
- `limit` / `offset` — pagina (tetto `MAX_LIMIT` di `apps.core.api.constants`).

## ⭐ Perché `…/righe/lista/` e non `…/righe/`

`GET …/righe/` **resta** la lettura completa delle righe attive, nell'ordine
del documento: la usano i dialog di evasione e di ri-consegna (che mostrano
anche le righe chiuse, come consuntivo), le stampe e gli script. La stessa view
serve il `POST` di creazione riga. Il cancello del perimetro emittente scatta su
**ogni** metodo della view che lo dichiara: messo su `…/righe/` avrebbe rifiutato
anche la creazione di una riga a chi vede più emittenti. Sul percorso suo, il
cancello guarda solo la lista (decisione di Tid, 2026-09-28).

## Le tre letture, una sorgente

Sui quattro documenti con una tabella di righe (preventivo, ordine, DDT, reso)
la pagina, la lettura completa e la riga singola (`get_riga`, usata dai
controlli «la riga appartiene al documento») leggono **la stessa vista**, e
tutte e tre filtrano le righe attive (`attivo IS TRUE`). Fattura e contratto
non hanno la riga singola né il filtro (sezioni sopra). L'eliminazione di una
riga è fisica (`DELETE FROM …_righe`) su tutti i documenti, preventivo compreso
(i componenti BoM vanno via in cascata; soft, `attivo = false`, è solo il DELETE
di un **componente**): il filtro sulla riga singola non cambia niente per le
righe eliminate, allinea la riga singola alle altre due letture nel caso, che il
modello ammette, di una riga con `attivo = false`.
