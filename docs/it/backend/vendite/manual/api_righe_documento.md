# API Righe documento — la lista configurabile (BB condiviso)

## Scopo

Le righe di un documento di vendita come **lista configurabile**: una pagina
con ricerca e ordinamento, e il suo export. Endpoint identici sui documenti,
generati dal factory condiviso `build_righe_lista_views`
(`apps/vendite/api/righe_lista_views.py`) sopra il mixin repository
`RigheDocumentoRepositoryMixin` (`apps/vendite/db/_righe_repo_mixin.py`).

Design-of-record:
[brief-db-liste-righe-documento.md](../../../dev/work-in-progress/brief-db-liste-righe-documento.md).

| Documento | Base path | Lista a catalogo | Sorgente | Ordine del documento |
|---|---|---|---|---|
| Preventivo | `/api/v1/vendite/preventivi/<id>/righe/lista/` | `vendite.preventivo_righe` | `vw_preventivi_righe_dettaglio` | `ordine` |
| Ordine | `/api/v1/vendite/ordini/<id>/righe/lista/` | `vendite.ordine_righe` | `vw_ordini_righe_dettaglio` | `riga_nr` |
| DDT | `/api/v1/vendite/ddt/<id>/righe/lista/` | `vendite.ddt_righe` | `vw_ddt_righe_dettaglio` | `riga_nr` |
| Reso | `/api/v1/vendite/resi/<id>/righe/lista/` | `vendite.reso_righe` | `vw_resi_righe_dettaglio` | `riga_nr` |

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
  **Assente**, l'ordine del documento (tabella sopra), poi `id`. Una colonna
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

La pagina, la lettura completa e la riga singola (`get_riga`, usata dai
controlli «la riga appartiene al documento») leggono **la stessa vista**, e
tutte e tre filtrano le righe attive (`attivo IS TRUE`). L'eliminazione di una
riga è fisica (`DELETE`): il filtro sulla riga singola non cambia niente per le
righe eliminate, allinea la riga singola alle altre due letture nel caso, che il
modello ammette, di una riga con `attivo = false`.
