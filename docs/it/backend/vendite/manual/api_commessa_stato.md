# API commessa_stato (Django)

## Scopo

Sulla risorsa `stato` di una commessa:

- **GET** — stato, contatori aggregati e **capability** (azioni di stato ammesse), per
  dashboard e monitoraggio avanzamento;
- **POST** — applica un'**azione di stato utente** (rendi pronta / riapri / chiudi / annulla).

## Contesto

- GET → servizio Python `fn_get_commessa_stato` (`apps.vendite.services.commesse_service`):
  contatori da `CommesseRepository.get_commessa_stato()` + capability da
  `CommesseRepository.get_capabilities()` (`script.fn_available_actions_commessa`).
- POST → servizio `cambia_stato_commessa` → `CommesseRepository.cambia_stato_commessa()`
  (`vendite.fn_cambia_stato_commessa(p_commessa_id, p_stato)`, il verbo del modello del
  documento: brief-modello-documento-vendita §14). Il permesso lo legge la view dalla riga
  del passaggio (§«POST» sotto). ⭐ Verso `ANNULLATA` passa
  **sempre** dal verbo `vendite.fn_annulla_commessa` (`CommesseRepository.annulla()`): vedi
  §«L'annullo, con la conferma dei legami» sotto.

View: `ApiCommessaStato` (`apps.vendite.api.views`) — `def get` + `def post` sulla stessa URL.

> **Vedi anche — genealogia commessa (Fase C lineage, 2026-07-15):**
> `GET /api/v1/vendite/commesse/<id>/passaggi/` espone la genealogia della
> commessa (sorgenti che l'hanno generata, ROOT/COLLEGATO, + fatture a valle).
> Contratto nel manuale del BB condiviso:
> [api_lineage_passaggi.md](api_lineage_passaggi.md). Consumer FE:
> `CommessaDrawer` leggero aperto dalle tappe COMMESSA dei pannelli "Passaggi".

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/commesse/<commessa_id>/stato/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri path:
  - `commessa_id` (int) — ID della commessa

## Output

- `200`: commessa trovata

```json
{
  "data": {
    "commessa_id": 1,
    "stato_codice_interno": "PRONTA_FATTURAZIONE",
    "stato_commessa_id": 4,
    "stato_commessa": "PRONTA_FATTURAZIONE",
    "chiude_commessa": false,
    "emittibile": true,
    "modificabile": true,
    "policy_fatturazione": "DA_DOCUMENTO",
    "fatturazione_immediata": false,
    "priorita_operativa": null,
    "billing_account_id": 1001,
    "utility_id": 2,
    "emittente_soggetto_ruolo_id": 555,
    "total_attivita": 10,
    "total_approvate": 8,
    "total_non_approvate": 2,
    "total_emesse": 5,
    "total_non_emesse": 5,
    "total_prezzo_da_riallineare": 0,
    "last_update": "2026-06-15T10:00:00",
    "descrizione": "Impianto sede di Verona",
    "data_apertura": "2026-09-01",
    "responsabile_risorsa_umana_id": 7,
    "responsabile_display": "Bianchi Anna",
    "capabilities": {
      "available_actions": [
        {"key": "chiudi", "target_state": "CHIUSA", "label_key": "vendite.commesse.azione_chiudi",
         "requires_confirm": true, "outlined": false},
        {"key": "annulla", "target_state": "ANNULLATA", "label_key": "vendite.commesse.azione_annulla",
         "requires_confirm": true, "outlined": true}
      ],
      "can_change_state": true,
      "can_edit_righe": true,
      "is_emittibile": true,
      "stato_codice": "PRONTA_FATTURAZIONE"
    }
  },
  "meta": { ... }
}
```

Campi (2026-06-15): l'endpoint ora propaga **tutto** ciò che `fn_get_commessa_stato`
espone, non più i soli 3 contatori. In dettaglio:

- `stato_codice_interno` (2026-06-10): codice stato interno della testata
  (`vendite.stati_commessa.codice_interno`) — verifica l'esito del ponte di
  emittibilità post-push senza una seconda chiamata. **Dal 2026-06-16 è derivato dal
  blob `capabilities.stato_codice`** (stessa fonte `codice_interno`), evitando un
  round-trip DB dedicato; valore invariato.
- **Stato + governance** (da `vendite.stati_commessa`): `stato_commessa_id`,
  `stato_commessa` (= `codice`, etichetta di stato), flag `chiude_commessa` /
  `emittibile` / `modificabile`.
  > Nota: `stato_commessa` (`codice`) e `stato_codice_interno` (`codice_interno`) sono
  > due **colonne distinte** di `stati_commessa` (oggi con lo stesso valore nel seed, ma
  > separate per design: display vs chiave interna stabile) — non sono un duplicato.
- **Config testata**: `policy_fatturazione`, `fatturazione_immediata`,
  `priorita_operativa` (**stringa**, codice `NORMALE`/`ALTA`/`BASSA`, nullable — non un
  intero), `billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`.
- **Contatori righe** `commesse_attivita`: `total_attivita`,
  `total_approvate` / `total_non_approvate`, `total_emesse` / `total_non_emesse`,
  `total_prezzo_da_riallineare`.
- `last_update` (ISO 8601, nullable): max tra update testata e ultima riga.
- **Testata leggibile** (2026-09-14, Blocco C di
  `brief-db-modifiche-certe-ciclo-vendita-e-articolo`): `descrizione` (nullable,
  max 255), `data_apertura` (ISO, mai `null`: la scrive il default
  `script.fn_data_operativa()` alla nascita), `responsabile_risorsa_umana_id` +
  `responsabile_display` (nome della persona, dalla vista modello
  `anagrafiche.vw_risorse_umane_dettaglio` — la stessa del lookup, così picker e
  dettaglio la chiamano nello stesso modo; entrambi `null` senza responsabile). ⚠️ Non escono da `fn_get_commessa_stato`: il repository li
  legge da `vendite.commesse` (`get_commessa_testata`) e il service li fonde
  nello stesso payload — un secondo endpoint sarebbe una seconda chiamata per tre
  colonne della stessa riga. Si scrivono con il `PATCH` qui sotto.
- `capabilities` (2026-06-16): blob data-driven da `script.fn_available_actions_commessa`
  (pattern gemello di ordini/preventivi/offerte/contratti):
  - `available_actions`: array delle **azioni di stato utente** ammesse dallo stato
    corrente (transizioni `meta.manuale=true` della matrice) **che l'operatore ha il
    permesso di chiedere** (dal 2026-10-26: un passaggio la cui riga porta un'azione si
    nasconde a chi non ce l'ha), ognuna con `key`
    (`rendi_pronta`/`riapri`/`chiudi`/`annulla`), `target_state` (codice stato destinazione),
    `label_key` (i18n), `requires_confirm`, `outlined` — pensate per
    renderizzare i pulsanti FE senza logica cablata (icona e colore li sceglie il
    frontend dal `key`). Array vuoto negli stati terminali;
  - `can_change_state` (bool), `can_edit_righe` (= `modificabile`),
    `is_emittibile` (= `emittibile`), `stato_codice`.

I campi nullable possono valere `null` (es. `priorita_operativa`, `last_update`).

- `400`: `commessa_id` non valido (`E_COMMESSA_VALIDATION`)
- `404`: commessa non trovata (`E_COMMESSA_NOT_FOUND`)

---

## PATCH `/api/v1/vendite/commesse/<id>/` — La testata leggibile

Scrive `descrizione` e `responsabile_risorsa_umana_id` (2026-09-14, Blocco C del
brief modifiche certe). **PATCH parziale**: si scrive solo ciò che il payload
porta; `null` esplicito **azzera** (togliere il responsabile è un gesto
legittimo). Risponde con il dettaglio aggiornato — lo stesso payload del `GET
/stato/`. Permesso: livello d'area `vendite` (`change`), come le testate degli
altri documenti; nessuna `Idempotency-Key` (aggiornamento parziale, api.md
§PATCH).

```json
{ "descrizione": "Impianto sede di Verona", "responsabile_risorsa_umana_id": 7 }
```

Regole:

- `data_apertura` **non** si scrive: la mette il default alla nascita, e una
  chiave estranea è un `400` (`E_COMMESSA_VALIDATION`, whitelist chiusa).
- Il responsabile deve essere una **risorsa umana attiva**, e lo dice il DB:
  il require sul figlio (`trg_commesse_a10_risorse_umane_require_attivo_ins_upd`,
  nato da `ci_apply`) risponde `409` `E_ATTIVO_PADRE_NON_ATTIVO` con la colonna
  nel campo (`fields: ["responsabile_risorsa_umana_id"]`). Una persona che non
  esiste è la FK: `400` `E_VENDITE_FK` col campo. Il service non legge la
  persona prima dell'`UPDATE`: fino al 2026-11-07 lo faceva, perché il require
  rispondeva `E_ATTIVO_REQUIRE` (`TECNICO`, 500); ritirato con
  `brief-db-revisione-dbops` BE3. Prova sul DB vero:
  `vendite/tests/db/test_commessa_testata_db.py`.
- Nessun guard di **stato**: il DB non ne mette, di proposito — la descrizione
  di una commessa chiusa si può correggere.
- Zero righe toccate (commessa inesistente **o fuori scope RLS**) → `404`
  `E_COMMESSA_NOT_FOUND`, come ogni dettaglio by-id.
- Il picker del responsabile è `GET /anagrafiche/risorse-umane/lookup/`
  (cross-dominio, `skip_area_check`; envelope `{"results": [...]}`).

---

## POST — Azione di stato utente

- Metodo: `POST`
- Path: `/api/v1/vendite/commesse/<commessa_id>/stato/`
- Header: `Authorization: Bearer <token>` + **`Idempotency-Key` obbligatoria**
- Permesso: **dalla riga del passaggio** (`post_passaggio = PassaggioDocumento(testata="vendite.commesse", documento_kwarg="commessa_id", campo_stato="nuovo_stato")`, M-3; dal 2026-10-27, brief-modello-documento-vendita §14.6): la catena legge l'azione della riga della matrice dallo stato corrente a `nuovo_stato`, prima della transazione. Oggi:

  | Passaggio | Azione |
  | --- | --- |
  | «rendi pronta» (BOZZA, APERTA → PRONTA_FATTURAZIONE) | `cambia_stato_commessa` |
  | «riapri» (PRONTA_FATTURAZIONE → APERTA) | `cambia_stato_commessa` |
  | «chiudi» (PRONTA_FATTURAZIONE, APERTA → CHIUSA) | `cambia_stato_commessa` |
  | annullo di una commessa non in bozza | `cambia_stato_commessa` |
  | annullo della bozza | nessuna: il livello sul documento (C-1, M-4) |

  Senza l'azione della riga → `403 E_PERMISSION_DENIED`, e il service non parte. ⚠️ Cambio visibile del 2026-10-27: fino ad allora un `post_permission = "cambia_stato_commessa"` la chiedeva su **ogni** passaggio, compreso l'annullo della bozza. Il `GET` resta libero nell'area.
- Body JSON:
  - `nuovo_stato` (string) — **codice stato di destinazione** (`target_state` preso da una
    delle `capabilities.available_actions`, es. `PRONTA_FATTURAZIONE` / `APERTA` / `CHIUSA` /
    `ANNULLATA`). IN_ESECUZIONE è ritirato (C-3): chiesto, il verbo risponde
    `E_STATO_WORKFLOW_NON_TROVATO`.
  - `legami_confermati` (int, facoltativo) — solo verso `ANNULLATA`, alla **conferma**:
    quanti legami l'operatore ha visto (`GET …/legami/`). Assente al primo tentativo.

Output `200`:

```json
{ "data": { "commessa_id": 1, "stato_da": "PRONTA_FATTURAZIONE", "stato_a": "CHIUSA" },
  "meta": { ... } }
```

Errori:

- `400` `E_COMMESSA_VALIDATION` — `commessa_id` ≤ 0 o `nuovo_stato` mancante;
- `404` `E_COMMESSA_NON_TROVATA` — commessa inesistente o fuori perimetro, dal verbo (dal
  2026-10-27 il service non lo ridice con `E_COMMESSA_NOT_FOUND`: regola del 1, Tid);
- `404` `E_STATO_WORKFLOW_NON_TROVATO` — `nuovo_stato` non è uno stato attivo della commessa;
- `409` `E_DOC_GIA_NELLO_STATO` — la commessa ha già lo stato chiesto;
- `409` `E_DOC_PASSAGGIO_DI_PROCESSO` — un passaggio di processo chiesto a mano (prima riga
  comune del verbo). ⛔ Ritirata il 2026-10-27 la «difesa applicativa» del service
  (`E_COMMESSA_AZIONE_NON_AMMESSA`, lo stato ammesso solo se era una `available_action`
  abilitata): ripeteva queste regole e quelle del guard, che ora il verbo dice da sé;
- `409` `E_DOC_ANNULLO_CON_LEGAMI` (`ui_action = confirm_and_retry`) — annullo di una commessa
  con righe non ancora emesse, senza la conferma o con un numero di legami che non
  corrisponde: è una **domanda**, non un rifiuto (§sotto);
- `409` `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE` — righe già emesse: l'annullo è vietato, e il
  verbo lo dice **prima** della conferma. Nella capability l'azione è spenta col motivo;
- `409` `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` / `409` `E_COMMESSA_NESSUNA_RIGA_APPROVATA`
  — sollevati dal guard DB se la coppia non è in matrice / precondizione non soddisfatta.

## L'annullo, con la conferma dei legami

> brief-db-annullo-a-valle-riapre-a-monte (D-1, D-2, D-6, D-7, D-8 di Tid, 2026-10-11/12).
> Stessa forma di bolla, ordine, preventivo e contratto
> (brief-db-annullo-documento-con-legami): un meccanismo solo.

Annullare una commessa **riapre a monte** ciò che l'ha riempita, e non in silenzio. Un
**legame** per ogni riga **non ancora emessa** (`vendite.fn_documento_legami('COMMESSA', id)`).
`origine` è il codice di `config.sorgenti` (dal 2026-10-19, brief-db-grammatica-unica-documenti
lotto 2b), tranne `ONERE`, che non è una sorgente:

| `origine` | `natura` | Che cosa succede annullando |
| --- | --- | --- |
| `PREVENTIVO`, `ORDINE_VENDITA`, `CONTRATTO`, `DDT_VENDITA` | `CONSUMO` | la riga esce dalla commessa (`ANNULLATA`, col registro) e il documento torna **da mandare in commessa**. Il preventivo EVASO torna ACCETTATO (dal DB); l'**ordine non cambia stato** (D-6: «Evaso» lo dicono solo le bolle) |
| `ATTIVITA_CONSUMI` | `CONSUMO` | il consumo torna da mandare |
| `RESO_VENDITA` | `CONSUMO` | la rettifica del reso esce, l'accredito si annulla: il reso torna **da accreditare** |
| `ONERE` | `ANNULLO` | niente a monte: l'onere **si annulla** con la commessa |

Il giro (`useForzaturaConfermata` + `DocumentoAnnulloLegamiDialog` a video):

1. `POST …/stato/` `{"nuovo_stato": "ANNULLATA"}` → con legami `409 E_DOC_ANNULLO_CON_LEGAMI`
   (`confirm_and_retry`), la frase del DB nomina la commessa e il numero; senza legami la
   commessa si annulla al primo colpo;
2. `GET /api/v1/vendite/commesse/<id>/legami/` → `{documento: "COMMESSA", id, legami, righe[]}`
   (factory `build_legami_view`, BB `legami_del_documento`): `legami` è il numero da
   dichiarare; ogni riga porta `riga_id` (la riga di commessa), `origine`, `natura`,
   `origine_id`, `origine_riga_id` (la riga di reso dell'accredito), `qta` e, dal lineage
   della commessa, `origine_tipo_codice_interno` e `origine_codice` (nulli per consumi e
   oneri, che non sono nodi del lineage). Prima la testata: commessa inesistente o fuori
   perimetro → `404 E_COMMESSA_NOT_FOUND` (il lettore del DB è `SECURITY DEFINER`);
3. `POST …/stato/` `{"nuovo_stato": "ANNULLATA", "legami_confermati": N}` → il verbo
   `vendite.fn_annulla_commessa` ritira i legami e porta la commessa ad `ANNULLATA`, in una
   transazione. Se nel frattempo i legami sono cambiati, il DB chiede di nuovo.

Output `200` del verbo: la stessa forma del cambio di stato
(`{commessa_id, stato_da, stato_a: "ANNULLATA"}`).

⚠️ **Prima ciò che vieta, poi ciò che chiede conferma** (D-3): con righe già **emesse**
l'annullo è vietato (`E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`, `script.fn_check_commessa_annullabile`)
e la conferma non viene chiesta.

## GET `/api/v1/vendite/commesse/<id>/registro/` — Il registro delle righe

Gli eventi che il DB scrive su `vendite.commesse_attivita_log` (oneri aggiunti,
righe annullate a mano, ritirate alla chiusura del documento di origine,
riportate da emettere, accrediti): chi, quando, con quale motivo. View
`ApiCommessaRegistro` → `fn_commessa_registro` →
`CommesseRepository.list_registro_attivita`. Area `vendite`, sola lettura.

Query:

- `commessa_attivita_id` (int, facoltativo) — restringe a una riga; assente = tutta la commessa;
- `limit` (int, default 100 `DEFAULT_LIMIT_EVENTI`, 1..`MAX_LIMIT`), `offset` (int ≥ 0, default 0);
  fuori intervallo o non interi → `400 E_VALIDATION_INPUT` (`pagina_da_query`, nella view;
  fino al 2026-10-21 `E_COMMESSA_VALIDATION` dal service).

Ordine fisso: `data_insert DESC, id DESC`. Il vocabolario degli eventi è del DB
e aperto: nessun filtro per evento.

```json
{ "data": { "commessa_id": 1, "count": 3, "rows": [
  { "id": 90, "commessa_attivita_id": 412, "evento": "RIGA_MANUALE_ANNULLATA",
    "dettaglio": { "motivo": "doppio carico" }, "motivo": "doppio carico",
    "data_insert": "2026-10-01T09:12:00+02:00", "user_insert": "mrossi",
    "segment_key": "...", "stato_emissione": "ANNULLATA", "tipo_movimento": "ONERE",
    "articolo_codice": "ONR-TRASP", "articolo_descrizione": "Trasporto" } ] } }
```

Lo scope passa dal `JOIN` su `vendite.commesse_attivita` (che ha la RLS; il log
no): commessa inesistente o fuori perimetro → `count: 0`, `rows: []`, non 404.

## Regole

- **GET** read-only, nessuna `Idempotency-Key`. **POST** write, `Idempotency-Key` obbligatoria.
- Endpoint v1 richiede JWT.
- `commessa_id` deve essere > 0, altrimenti errore di validazione.
- GET: stato, flag di governance e contatori calcolati nel DB in un round-trip
  (`fn_get_commessa_stato`) + capability da `fn_available_actions_commessa`.
- POST: il permesso dalla riga del passaggio (view); tutto il resto lo dice il verbo
  `fn_cambia_stato_commessa` (o `fn_annulla_commessa`), anche l'esistenza nel perimetro
  (`404 E_COMMESSA_NON_TROVATA`). Il lettore leggero (`get_commessa_stato_codice`) resta
  solo per lo `stato_da` della risposta dell'annullo. Il verbo di stato: la prima riga comune (stato che ha già, passaggio di
  processo, azione), poi la scrittura attraverso la porta, dove il guard giudica matrice e
  condizioni. Firma **senza `p_user`** (C-4): chi scrive lo dice l'audit dalla sessione.
- Il passaggio a pronta della **push** non passa da qui: lo scrive la proiezione
  `vendite.fn_commessa_proietta_stato_emittibile` (dal ponte
  `fn_rendi_commessa_emittibile`), col permesso della push e non con l'azione del passaggio
  manuale (C-2).
- Implementa il pattern standard `handle_post_json` (POST) / `success_response` (GET).

## Dipendenze DB

- `vendite.fn_get_commessa_stato` (stato + contatori)
- `script.fn_available_actions_commessa` (capability / azioni di stato)
- `vendite.fn_cambia_stato_commessa(bigint, varchar)` (il verbo: prima riga comune, porta, guard)
- `script.fn_doc_azione_passaggio` (l'azione della riga, per il `403` della view)
- `vendite.fn_annulla_commessa` (verbo dell'annullo: conferma, ritiro dei legami, stato)
- `vendite.fn_documento_legami` (lettore unico dei legami: avviso, verbo, finestra)
- `vendite.commesse`, `vendite.commesse_attivita`, `vendite.transizioni_stati_commessa`,
  `vendite.stati_commessa`
