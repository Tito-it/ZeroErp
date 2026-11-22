# API — export delle liste configurabili

## Scopo

Un contratto solo per **tutti** gli export di lista dell'applicazione: stesso
parametro, stesso comportamento, stesso tetto. Cambia il dominio, non la regola.

Il renderer e' `apps/ui/services/lista_export_service.py` (CSV/XLSX); i dati li
prende sempre il repository del dominio, mai il renderer — **niente SQL
dinamico**, quindi niente `vista_sql` costruita a runtime.

## 1. Il contratto

| | |
|---|---|
| **Metodo** | `GET` |
| **Path** | `…/export/` in coda alla lista che esporta (tabella al §3) |
| **Parametro** | `formato=csv` (default) oppure `formato=xlsx` |
| **Risposta** | file binario con `Content-Disposition: attachment` |
| **Tetto** | **10.000 righe**; oltre, `E_UI_EXPORT_LIMIT_EXCEEDED` |

⛔ **Il parametro si chiama `formato`, in italiano, e non e' un vezzo.** `format`
e' un **magic param di DRF**: usarlo fa entrare in gioco il content negotiation
del framework e la richiesta muore con **404** prima di arrivare alla view. Il
nome italiano e' la difesa contro una collisione che si manifesta come «endpoint
inesistente», cioe' nel modo piu' difficile da diagnosticare.

## 2. Cosa esce, e perche' non e' «la query di prima con piu' righe»

L'export **rispetta le preferenze di lista dell'operatore**: ordine delle
colonne, colonne nascoste, permessi. Sono gli stessi che il FE usa a video, letti
da `UiService.get_lista_config`.

Il renderer scarta:

* le colonne nascoste dall'utente (`visibile = false` nella configurazione);
* le colonne `BLOCCATO` per i permessi — non arrivano nemmeno nella
  configurazione;
* le colonne con `esportabile = false` **nella configurazione**: il flag lo
  compone `ui.fn_resolve_lista_config`, ed e' falso sia quando l'admin ha
  marcato la colonna non esportabile a catalogo, sia quando il permesso di
  colonna dell'utente e' `LETTURA` (la vede a video, non la porta via). Le
  azioni ci cadono per costruzione: il DB garantisce che un'azione non ha campo
  sorgente e che una colonna senza campo sorgente non e' esportabile.

⛔ Il flag che decide e' quello della **configurazione**, non quello del
catalogo (`ui.lista_colonna.esportabile`): fino al 2026-11-22
`ListaExportService.select_colonne_visibili_da_config` prendeva il secondo, e le
colonne in sola `LETTURA` finivano nel file. Un flag assente non esporta.

Restano identificatori e informazioni, **nell'ordine della configurazione
dell'utente** (quello che vede a video). ⚠️ Conseguenza pratica: **due operatori con permessi
diversi ottengono file diversi dallo stesso endpoint**, ed e' voluto.

I **filtri applicati** viaggiano col file: riga di intestazione commentata (`#`)
nel CSV, foglio «Filtri applicati» nell'XLSX. Servono a non ritrovarsi in mano
un file che nessuno sa piu' da dove venga.

Date e numeri passano da `locale_formatters.format_for_export` — formato
italiano (`DD-MM-YYYY`), mai la serializzazione di default. ⭐ **E nell'ora
dell'azienda** (dal 2026-09-14; dal 2026-10-09 il fuso e' il parametro
`SYSTEM_FUSO_ORARIO` via il BB `fuso_aziendale`, non piu' `TIME_ZONE`): fino al 14-09 un `datetime`
usciva nel fuso che portava, cioe' UTC per ogni timestamptz letto dal DB —
una o due ore indietro rispetto alla lista a video, che il browser converte.
Vale anche per il giorno preso da un datetime (le 23:30 UTC del 14 sono il
15) e per il timestamp nel nome del file.

## 3. Gli endpoint

Ognuno dichiara il proprio `lista_codice`: e' la chiave con cui il BE risolve la
configurazione della lista **e** il cancello del perimetro emittente.

| endpoint | `lista_codice` |
|---|---|
| `GET /api/v1/anagrafiche/clienti/export/` | `anagrafiche.clienti` |
| `GET /api/v1/anagrafiche/fornitori/export/` | `anagrafiche.fornitori` |
| `GET /api/v1/anagrafiche/soggetti/export/` | `anagrafiche.soggetti` |
| `GET /api/v1/anagrafiche/soggetti/{soggetto_id}/titoli-iva/export/` | `anagrafiche.soggetto_titoli_iva` |
| `GET /api/v1/catalogo/articoli/{articolo_id}/componenti/lista/export/` | `catalogo.articolo_componenti` |
| `GET /api/v1/vendite/preventivi/export/` | `vendite.preventivi` |
| `GET /api/v1/vendite/offerte/export/` | `vendite.offerte` |
| `GET /api/v1/vendite/contratti/export/` | `vendite.contratti` |
| `GET /api/v1/vendite/ordini/export/` | `vendite.ordini` |
| `GET /api/v1/vendite/ddt/export/` | `vendite.ddt` |
| `GET /api/v1/vendite/fatture/export/` | `vendite.fatture` |
| `GET /api/v1/vendite/resi/export/` | `vendite.resi` |
| `GET /api/v1/vendite/resi/da-accreditare/export/` | `vendite.resi_da_accreditare` |
| `GET /api/v1/vendite/resi/da-riconsegnare/export/` | `vendite.resi_da_riconsegnare` |
| `GET /api/v1/vendite/preventivi/{id}/righe/lista/export/` | `vendite.preventivo_righe` |
| `GET /api/v1/vendite/offerte/{id}/righe/lista/export/` | `vendite.offerta_righe` |
| `GET /api/v1/vendite/contratti/{id}/righe/lista/export/` | `vendite.contratto_righe` |
| `GET /api/v1/vendite/ordini/{id}/righe/lista/export/` | `vendite.ordine_righe` |
| `GET /api/v1/vendite/ddt/{id}/righe/lista/export/` | `vendite.ddt_righe` |
| `GET /api/v1/vendite/fatture/{id}/righe/lista/export/` | `vendite.fattura_righe` |
| `GET /api/v1/vendite/resi/{id}/righe/lista/export/` | `vendite.reso_righe` |
| `GET /api/v1/vendite/famiglie/export/` | `vendite.famiglie_documento` ¹ |
| `GET /api/v1/vendite/giornale/export/` | `vendite.giornale` |
| `GET /api/v1/vendite/lotti/export/` | `vendite.lotti` |
| `GET /api/v1/vendite/lotti/{lotto_id}/fatture/export/` | `vendite.lotto_fatture` |
| `GET /api/v1/vendite/lotti/{lotto_id}/gruppi/export/` | `vendite.lotto_gruppi` |
| `GET /api/v1/vendite/lotti/{lotto_id}/task-runs/export/` | `vendite.lotto_task_runs` |
| `GET /api/v1/vendite/lotti/{lotto_id}/segnalazioni/export/` | `vendite.lotto_segnalazioni` |
| `GET /api/v1/vendite/commesse/{commessa_id}/attivita/export/` | `vendite.commesse_attivita` |
| `GET /api/v1/vendite/fondi-fattura/da-decidere/export/` | `vendite.fondi_fattura_da_decidere` |
| `GET /api/v1/vendite/dashboard-aperto/documenti/export/` | `vendite.dash_aperto_documenti` |
| `GET /api/v1/vendite/dashboard-backlog/documenti/export/` | `vendite.dash_backlog_documenti` |
| `GET /api/v1/vendite/dashboard-competenza/gruppi/export/` | `vendite.dash_competenza_gruppi` |
| `GET /api/v1/vendite/dashboard-competenza/commesse/export/` | `vendite.dash_competenza_commesse` |
| `GET /api/v1/vendite/dashboard-competenza/residui/export/` | `vendite.dash_competenza_residui` |
| `GET /api/v1/vendite/dashboard-competenza/errori/export/` | `vendite.dash_competenza_errori` |
| `GET /api/v1/pagamenti/distinte/{contabile_id}/righe/export/` | `pagamenti.distinta_righe` |
| `GET /api/v1/pagamenti/fatture/{fattura_id}/sistemazioni/export/` | `pagamenti.sistemazioni_fattura` |
| `GET /api/v1/magazzino/inventari/export/` | `magazzino.inventari` |
| `GET /api/v1/magazzino/inventari/{id}/righe/export/` | `magazzino.inventario_righe` |
| `GET /api/v1/magazzino/inventari/{id}/piano/export/` | `magazzino.inventario_piano` |
| `GET /api/v1/magazzino/rettifiche/export/` | `magazzino.rettifiche` |
| `GET /api/v1/magazzino/rettifiche/{id}/righe/export/` | `magazzino.rettifica_righe` |
| `GET /api/v1/magazzino/magazzini/export/` | `magazzino.magazzini` |
| `GET /api/v1/magazzino/magazzini/{magazzino_id}/ubicazioni/export/` | `magazzino.ubicazioni` |
| `GET /api/v1/magazzino/lotti/export/` | `magazzino.lotti` ¹ |
| `GET /api/v1/magazzino/disponibilita/export/` | `magazzino.disponibilita` |
| `GET /api/v1/magazzino/disponibilita/articoli/export/` | `magazzino.disponibilita_articoli` |
| `GET /api/v1/magazzino/movimenti/export/` | `magazzino.movimenti` |
| `GET /api/v1/amm-software/error-log/export/` | `dbops.error_log` ² |

¹ Liste senza perimetro emittente (catalogo globale, `perimetro_emittente =
false`): dichiarano `lista_codice` ma non hanno cancello. ² Su `AdminAPIView`
(solo SUPER_ADMIN): dichiara `lista_codice` (da una costante di modulo), e il
cancello del perimetro emittente non c'e', perche' sta solo su `DomainAPIView`.
Il registro delle esenzioni e' `test_perimetro_emittente_copertura`.

⭐ Dal 2026-11-22 (giro 6 di brief-db-revisione-ui) la **partenza** della lista
(ordinamento e misura di partenza, vedi
[api_ui_liste § Regole](api_ui_liste.md#regole)) la accende `_ApiViewBase` su
**ogni** porta che dichiara `lista_codice`, quindi anche sugli export ¹ e ².

**I filtri sono quelli della lista corrispondente**: l'export accetta gli stessi
query param della sua `GET` di lista e li applica agli stessi campi. Per il
dettaglio dei filtri di un dominio si guarda la pagina di quel dominio, non
questa.

## 4. Il perimetro emittente vale anche qui — anzi, soprattutto qui

`lista_codice` non serve solo a leggere la configurazione: e' la dichiarazione su
cui `DomainAPIView` applica il **cancello del perimetro emittente** prima di
servire i dati (`E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`, 422).

⚠️ **E l'export e' la porta piu' larga**: una sola richiesta porta via fino a
10.000 righe. Rifiutare a video quel che si concede in un file e' il modo
peggiore di avere un presidio — per questo `test_perimetro_emittente_copertura`
pretende che lista ed export dichiarino la stessa cosa **nei due versi**: se una
lista lo dichiara, il suo export deve farlo; e viceversa.

## 5. Codici errore

| codice | quando |
|---|---|
| `E_UI_EXPORT_FORMAT_INVALID` (400) | `formato` diverso da `csv` / `xlsx` |
| `E_UI_EXPORT_LIMIT_EXCEEDED` (422) | oltre 10.000 righe: si stringono i filtri, non si alza il tetto |
| `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` (422) | perimetro emittente non risolto — **non e' un 403**: il diritto c'e', manca una precondizione che l'operatore scioglie da se' |

## 6. Aggiungere un export a una lista nuova

1. la view estende `DomainAPIView` e dichiara `lista_codice` — **lo stesso** della
   lista che esporta;
2. il repository di dominio produce le righe (whitelist colonne/filtri gia' sue);
3. la serializzazione va delegata a `ListaExportService`: non si riscrive un CSV
   a mano, o si perdono formattazione locale, filtri in testata e cap;
4. il parametro si chiama **`formato`**;
5. si aggiunge la riga alla tabella del §3, altrimenti il prossimo che cerca
   «come esporto X» non lo trova — ed e' il motivo per cui questa pagina esiste.

## Dipendenze

* `apps/ui/services/lista_export_service.py` — renderer CSV/XLSX, cap, filtri in testata
* `apps/ui/services/ui_service.py` — `get_lista_config` (colonne, ordine, permessi, `esportabile`)
* `apps/core/services/locale_formatters.py` — `format_for_export`
* `apps/core/api/base_views.py` — `lista_codice` (dichiarato su `_ApiViewBase`: la partenza) e cancello perimetro (`DomainAPIView`)
* [api_ui_liste](api_ui_liste.md) — la configurazione delle liste, di cui l'export e' la proiezione su file
