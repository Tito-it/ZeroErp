# API — ristampa fedele di un documento (percorso 3)

## Scopo

Riprodurre un documento **com'era**: con la versione di template con cui nacque
e il contesto congelato di allora. È il terzo dei tre percorsi documentali, e
l'unico che mantiene la promessa di riproducibilità sui documenti privi di file
salvato.

I tre percorsi, che prima si confondevano in due:

| # | Percorso | Endpoint | Cosa produce |
| --- | --- | --- | --- |
| 1 | **Scarica originale** | `GET .../documenti/<id>/file/` | Il file prodotto allora, byte per byte. Richiede che il file esista |
| 2 | **Genera nuovo documento** | `POST .../documenti/genera/` | Un documento **diverso**: modello pubblicato oggi + dati di oggi |
| 3 | **Ristampa fedele** | `GET .../documenti/<id>/ristampa/` | L'originale ri-renderizzato: versione pinnata + contesto congelato |

> ⚠️ Fino al 2026-08-03 il percorso 2 era commentato come «ristampa». Non lo è:
> per un documento del 2025 produrrebbe il modello del 2026 con i dati di oggi.
> Il codice faceva bene il suo mestiere — era il nome a mentire, e il nome
> faceva credere al chiamante di avere una ristampa.

## Contesto

La persistenza dei file è iniziata il **2026-07-21**: i documenti anteriori non
hanno un file su storage, e per loro il percorso 1 risponde `404`. Il percorso 3
è l'unico modo di riprodurli — ed è anche l'unico modo di **verificare** che un
file conservato sia davvero quello giusto (confronto con `pdf_hash`).

La riproducibilità era già garantita dal modello: ogni riga di
`documenti.documenti_generati` conserva `template_versione_id` (la versione
usata), `context_json` (i dati usati) e i tre hash. Il database ne impedisce la
riscrittura (`trgfn_documenti_generati_protect_snapshot`) e la cancellazione
delle versioni referenziate. Mancava solo chi la esercitasse.

## Input

```text
GET /api/v1/vendite/<dominio>/<sorgente_id>/documenti/<documento_id>/ristampa/
```

Cablato su tutti e **6** i domini sorgente (preventivi, offerte, contratti,
ordini, DDT, fatture) — presidiato da
`apps/documenti/tests/api/test_ristampa_routing.py`.

Nessun parametro: gli ingredienti sono già tutti nel documento. È l'assenza di
parametri a rendere il percorso quello che è — non c'è niente da scegliere,
perché tutto è stato scelto quando il documento è nato.

## Output

`200` — stream `application/pdf` con `Content-Disposition: inline` (è una
consultazione, come l'anteprima, non un salvataggio).

| Header | Valori | Significato |
| --- | --- | --- |
| `X-Ristampa-Pdf-Hash-Match` | `1` / `0` | `1` = identico all'originale byte per byte; `0` = fedele nel **contenuto** ma non nei byte |

Il verdetto di fedeltà viaggia in header perché il corpo è il PDF. Il frontend
lo traduce in un toast di successo o di warning: **entrambi sono esiti positivi**
— `0` non è un errore (vedi «Fedeltà» sotto).

Errori:

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_DOCUMENTI_NOT_FOUND` | 404 | Documento inesistente o fuori scope emittente (404 unificato, no leak); oppure versione pinnata sparita |
| `E_DOCUMENTI_VALIDATION` | 400 | Documento senza `template_versione_id` o con `context_json` vuoto: non è ristampabile fedelmente, e va detto |
| `E_DOCUMENTI_RENDER_FAILED` | 500 | Il render della versione storica fallisce |

## Regole

1. **La versione è quella pinnata**, caricata anche se `OBSOLETA` — è il caso
   normale, non l'eccezione: il modello del 2025 oggi è obsoleto ed è
   esattamente quello che si vuole. Il servizio usa
   `DocumentiRepository.get_versione_by_id`, che non filtra per stato; usare
   `get_versione_pubblicata_attiva` qui sarebbe il difetto.
2. **Il contesto si legge, non si ricostruisce.** Arriva da `context_json`;
   nessun `context_builder` viene invocato. Un contesto ricostruito è un
   documento nuovo travestito da vecchio — ed è la ragione per cui i test
   presidiano *chi viene chiamato*, non il PDF prodotto.
3. **Non persiste nulla**: nessuna riga in `documenti_generati`, nessun
   progressivo consumato, nessuno stato sorgente toccato. L'unica scrittura è
   l'evento di audit.
4. **Traccia**: evento `RISTAMPA_FEDELE` sul documento esistente, con
   `esito = OK` oppure `WARN` (byte diversi) e il dettaglio di fedeltà.
   Best-effort come il `SCARICATO` del download: se l'INSERT fallisce il PDF
   esce comunque — negarlo per un log mancante sarebbe peggio del log mancante.
5. **Scope**: lo stesso degli altri endpoint documentali (whitelist emittenti
   sul documento). L'`id` della versione arriva da una riga già passata per lo
   scope, quindi la lettura della versione non ne ha bisogno.

### Fedeltà — cosa si promette davvero

Il confronto autoritativo è sul **contenuto**: gli stessi ingredienti
(`template_versione_id` + `context_json`) producono lo stesso documento per
costruzione. Il `pdf_hash` viene comunque ricalcolato e confrontato, ma una
differenza di byte **non è un errore**: un renderer può non essere
deterministico fra versioni della libreria (font, metadati, data di
produzione). Il sistema lo **dichiara** invece di nasconderlo.

L'alternativa — pinnare anche la versione del motore di render — è più forte e
molto più cara; scartata (decisione 2026-08-03).

Il servizio espone anche `template_hash_match`: se il template_hash congelato
non combacia con quello ricalcolato sulla versione caricata, la versione è stata
modificata dopo la generazione (possibile solo su BOZZA, il DB protegge le
PUBBLICATE). Non blocca, ma è dichiarato.

## Dipendenze DB

- `documenti.documenti_generati` — snapshot congelato (lettura
  `get_documento_generato_snapshot`: testata + `context_json`, separata dalle
  altre letture perché il contesto può essere grande e serve solo qui)
- `documenti.template_documenti_versioni` — versione pinnata, qualunque stato
- `documenti.documenti_generati_eventi` — evento di audit

`RISTAMPA_FEDELE` è nel CHECK `chk_documenti_generati_eventi_evento_tipo` dal
2026-08-03 (`20260803-05`), insieme al pgTAP che lo asserisce ammesso con esito
`WARN`. ℹ️ L'INSERT dell'evento resta **best-effort** in transazione separata
(come il `SCARICATO` del download): se fallisse, il servizio logga
`documenti.ristampa_fedele.evento_fallito` e il PDF esce comunque — negarlo per
un log mancante sarebbe peggio del log mancante.

## Note di migrazione

La lista documenti per sorgente espone ora `has_file_principale` (EXISTS sul
file principale): permette alla UI di **disabilitare con la ragione** l'azione
«Scarica originale» sui documenti privi di file, invece di lasciarla fallire con
un 404 generico, e di proporre al suo posto la ristampa fedele.
