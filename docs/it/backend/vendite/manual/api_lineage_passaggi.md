# API Passaggi documento (lineage/genealogia — BB condiviso, 7 domini vendite)

## Scopo

Esporre la **genealogia/lineage** di un documento vendite per il pannello
"Passaggi" dei drawer: pratica collegata, **frontiera** (documento più
prossimo in esecuzione) e la **catena reale dei transiti** in entrambe le
direzioni (origine + destinazioni). Endpoint identici sui 7 domini (6
documenti + commessa, Fase C), generati
dal factory condiviso `build_passaggi_view`
(`apps/vendite/api/lineage_views.py`) sopra il service
`vendite_service.get_documento_passaggi`.

Design-of-record:
[brief-design-genealogia-transiti-vendite.md](../../../dev/work-done/brief-design-genealogia-transiti-vendite.md)
(decisioni G-1..G-11). Modello DB:
[brief-db-lineage-documenti-vendite.md](../../../dev/work-done/brief-db-lineage-documenti-vendite.md)
— viste `vendite.vw_documento_lineage{_nodi,_archi,}` +
`vendite.fn_documento_lineage` (tutte `security_invoker`: RLS emittente del
chiamante, il BE non passa `auth_user_id`). Piano operativo:
[brief-be-fe-lineage-documenti-vendite.md](../../../dev/work-done/brief-be-fe-lineage-documenti-vendite.md).

| Dominio | Endpoint | Tipo sorgente |
|---|---|---|
| Preventivi | `GET /api/v1/vendite/preventivi/<id>/passaggi/` | `PREVENTIVO` |
| Offerte | `GET /api/v1/vendite/offerte/<id>/passaggi/` | `OFFERTA_COMMERCIALE` |
| Ordini | `GET /api/v1/vendite/ordini/<id>/passaggi/` | `ORDINE_VENDITA` |
| Contratti | `GET /api/v1/vendite/contratti/<id>/passaggi/` | `CONTRATTO` |
| DDT | `GET /api/v1/vendite/ddt/<id>/passaggi/` | `DDT_VENDITA` |
| Resi | `GET /api/v1/vendite/resi/<id>/passaggi/` | `RESO_VENDITA` |
| Commesse (Fase C) | `GET /api/v1/vendite/commesse/<id>/passaggi/` | `COMMESSA` |

## Contesto

- Il grafo (archi A..H + R) vive **interamente nel DB**; qui solo lettura e
  orchestrazione sottile (DB-first).
- La **chiave nodo** è la nativa polimorfa `(tipo_id, uid)` secondo
  `config.sorgenti.key_selector` (vedi
  [Convenzione chiave sorgente](/dbzero/config/manual/sorgenti)): il service
  traduce il pk di dominio (`uid` per preventivi/offerte via query sulla
  `target_table`; `id::text` per gli altri) — **il FE resta ignaro** della
  convenzione (decisione P-1).
- **Commessa** (Fase C): non ha lista/CRUD propria, ma il suo nodo lineage è
  consultabile via drawer leggero (genealogia inversa — sorgenti che l'hanno
  generata + fatture a valle). **Fattura** resta nodo terminale senza endpoint
  (Q4: capolinea, nessuna superficie propria).

## Input

- Path param: pk di dominio del documento (`<int>`).
- Nessun query param: la risposta include **entrambe** le direzioni (P-2).

## Output

`200` — envelope standard, `data`:

- `nodo`: `{tipo_codice, codice, stato_codice_interno, stato_descrizione,
  fase, is_abortito, is_transitato, n_discendenti_diretti,
  n_discendenti_attivi, n_sorgenti}`
- `pratica`: `{pratica_id, pratica_numero, n_pratiche}` oppure `null`
  (conteggio difensivo Q5: il DB non garantisce 1:1)
- `frontiera`: `{tipo_codice, codice, stato_codice_interno, fase,
  n_discendenti_attivi}` oppure `null` (documento non transitato; la
  frontiera "= nodo stesso" della summary è normalizzata a `null`)
- `avanti[]` / `indietro[]`: archi del traversal, ordinati per `ordine`:
  `{livello, ordine, arco (A..H|R), ruolo (ROOT/COLLEGATO|null),
  from_{tipo_id, tipo_codice, uid, codice, stato_codice_interno, fase,
  doc_id}, to_{tipo_id, tipo_codice, uid, codice, stato_codice_interno,
  fase, is_abortito, doc_id}, is_ramo_inverso}` — il lato `from` è decorato
  con stato/fase (JOIN a `vw_documento_lineage_nodi`) perché in direzione
  `indietro` la tappa da mostrare è il nodo FROM.
- `from_doc_id` / `to_doc_id` (bigint | null): **id numerico di dominio** del
  nodo, per aprire il drawer di dettaglio dal FE. `uid::bigint` per i tipi
  `key_selector='id'` (ordine/contratto/ddt/reso/commessa/fattura); per
  preventivo/offerta (`key_selector='uid'`) è la traduzione UUID→id (LEFT JOIN
  a `preventivi`/`offerte_commerciali`). `null` **solo** se il nodo è fuori
  scope RLS (traduzione UUID→id senza match). NB: `doc_id` valorizzato **non**
  implica apribile — è il FE a decidere in base ai tipi con drawer
  (`LINEAGE_DRAWER_TIPI`: i 6 documenti + commessa; la fattura ha `doc_id` ma
  nessun drawer, resta tappa consultiva).

### Esempio di risposta (caso reale: `GET /vendite/preventivi/524/passaggi/` — PRV0000185)

```json
{
  "data": {
    "nodo": {
      "tipo_codice": "PREVENTIVO",
      "codice": "PRV0000185",
      "stato_codice_interno": "EVASO",
      "stato_descrizione": "Evaso",
      "fase": "CHIUSO",
      "is_abortito": false,
      "is_transitato": true,
      "n_discendenti_diretti": 1,
      "n_discendenti_attivi": 0,
      "n_sorgenti": 0
    },
    "pratica": { "pratica_id": 895, "pratica_numero": "PRA-0000818", "n_pratiche": 1 },
    "frontiera": {
      "tipo_codice": "DDT_VENDITA",
      "codice": "DDT0000031",
      "stato_codice_interno": "SPEDITO",
      "fase": "IN_CORSO",
      "n_discendenti_attivi": 0
    },
    "avanti": [
      {
        "livello": 1, "ordine": 1, "arco": "A", "ruolo": null,
        "from_tipo_id": 2, "from_tipo_codice": "PREVENTIVO",
        "from_uid": "…uuid…", "from_codice": "PRV0000185",
        "from_stato_codice_interno": "EVASO", "from_fase": "CHIUSO",
        "from_doc_id": 524,
        "to_tipo_id": 6, "to_tipo_codice": "ORDINE_VENDITA",
        "to_uid": "174", "to_codice": "ORD0000163",
        "to_stato_codice_interno": "EVASO", "to_fase": "CHIUSO",
        "to_is_abortito": false, "to_doc_id": 174,
        "is_ramo_inverso": false
      },
      {
        "livello": 2, "ordine": 2, "arco": "H", "ruolo": null,
        "from_tipo_codice": "ORDINE_VENDITA", "from_codice": "ORD0000163",
        "from_doc_id": 174,
        "to_tipo_codice": "DDT_VENDITA", "to_codice": "DDT0000031",
        "to_stato_codice_interno": "SPEDITO", "to_fase": "IN_CORSO",
        "to_doc_id": 55, "is_ramo_inverso": false
      }
    ],
    "indietro": []
  },
  "meta": { "request_id": "…" }
}
```

Genealogia inversa (Fase C): `GET /vendite/commesse/186/passaggi/` → `indietro`
con 2 archi `B` (`from_codice=PRV0000183, ruolo=ROOT` + `PRV0000184,
ruolo=COLLEGATO`), `avanti` con le eventuali fatture (arco `G`).

## Regole

- **Frontiera** = discendente più a valle attivo (fase ≠ CHIUSO ∧ non
  abortito, G-6/G-10); fan-out F/H aggregato: la summary indica la più
  prossima attiva (G-9), `n_discendenti_attivi` segnala il fan-out.
- **Arco R (DDT→Reso)** = ramo inverso (`is_ramo_inverso=true`): compare nei
  passaggi come "merce che torna", è **escluso** dalla frontiera forward.
- Errori: `E_VENDITE_VALIDATION` (400) su tipo non in whitelist o id non
  valido; `E_VENDITE_NOT_FOUND` (404) su documento inesistente **o fuori
  scope RLS** (indistinguibili per design).

## Dipendenze DB

- `vendite.vw_documento_lineage` (summary nodo: pratica/frontiera/contatori)
- `vendite.fn_documento_lineage(tipo, uid, direzione)` (traversal, cycle
  guard livello < 10)
- `vendite.vw_documento_lineage_nodi` (decorazione lato FROM)
- `config.sorgenti` (vocabolario tipi + `key_selector`/`target_table`)

## Note di migrazione

Nessuna: endpoint read-only additivo (Fase A del brief lineage). Le colonne
lineage nelle liste (Fase B) hanno un prerequisito DB dedicato
([brief-db-liste-lineage-colonne.md](../../../dev/work-done/brief-db-liste-lineage-colonne.md)).

## Consumer FE

`frontend/src/vendite/_shared/lineage/` — `lineageApi.js` (`getPassaggi`) +
`LineagePassaggiPanel.vue` (Panel toggleable lazy, fetch a ogni expand —
freshness — via useApiHandler), montato nei 6 drawer documento + drawer
leggero `CommessaDrawer` (Fase C). Le tappe apribili (`*_doc_id` valorizzato +
tipo con drawer) aprono il **dettaglio impilato** via
`LineageDocumentoDrawerHost.vue` (mappa tipo→drawer con import async in
`lineageDrawers.js`) — comportamento uniforme al link pratica (→ `PraticaDrawer`).
