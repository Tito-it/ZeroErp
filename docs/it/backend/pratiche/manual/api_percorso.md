# API percorso (Django)

## Scopo

Restituisce il **percorso suggerito** di una pratica = i `template_flussi` **attivi**
della **definizione workflow assegnata alla pratica** (`pratiche.definizione_id`, non il
solo `tipo_prestazione`: con più edizioni dello stesso tipo la join per tipo duplicherebbe
le righe), in ordine, ciascuno con lo stato di istanziazione. Alimenta
la roadmap FE (`PraticaPercorso.vue`).

## Contesto

I flussi **non** sono materializzati alla creazione della pratica (percorsi
condizionali, §6 brief FE): si creano progressivamente. Questo endpoint mostra il
percorso completo dal catalogo e, per ogni step, se esiste già un flusso
istanziato (l'**ultimo** per quel template, via `LEFT JOIN LATERAL`).

Delega a `pratiche_service.get_percorso` → `PraticheRepository.get_percorso_pratica`.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/percorso/`
- Header: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "template_flusso_id": 9001,
        "template_flusso_codice": "RICHIESTA_CLIENTE",
        "template_flusso_descrizione": "Richiesta del cliente",
        "sequenza": 10,
        "obbligatorio": true,
        "direzione": "ENTRATA",
        "has_handler": false,
        "template_attende_sorgente_tipo_id": null,
        "template_azione_ui_key": null,
        "flusso_id": 50,
        "stato_codice_interno": "COMPLETATO",
        "stato_descrizione": "Completato",
        "esito": "POSITIVO",
        "esito_descrizione": "Positivo",
        "ripetibile_adesso": false,
        "completato": true,
        "percorribile": true,
        "bloccante": false,
        "ramo": "COMPLETATO"
      },
      {
        "template_flusso_id": 9004,
        "template_flusso_codice": "CONFERMA",
        "sequenza": 40,
        "has_handler": true,
        "flusso_id": null,
        "stato_codice_interno": null,
        "esito": null,
        "ripetibile_adesso": true,
        "completato": false,
        "percorribile": false,
        "bloccante": false,
        "ramo": "FUTURO"
      }
    ]
  }
}
```

- `flusso_id = null` → step non ancora creato (`has_handler=true` → step automatico).
- `stato_descrizione` / `esito_descrizione` — le descrizioni umane dello stato e
  dell'esito dell'ultima istanza (`config.stati_flussi_pratiche`,
  `config.esiti_flussi_pratiche`); `null` senza istanza.
- `template_azione_ui_key` — la chiave dell'azione UI del template (`pratiche.azioni_ui`);
  `template_attende_sorgente_tipo_id` — il tipo di documento sorgente che lo step attende
  (step guidato dalla proiezione); entrambi `null` se assenti.
- Ogni step porta anche i campi `doc_*` (sotto).
- `400`: `pratica_id` non valido (`E_INVALID_ID`).
- `401`: JWT mancante o non valido.

### Campi workflow v2 (2026-06-12, D3/D4 analisi-pratiche-workflow-v2)

- `ripetibile_adesso` (bool, da `fn_check_ripetibilita_flusso`) — una NUOVA
  istanza dello step è creabile ora, secondo la regola del template
  (`MAI` / `SE_NON_POSITIVO` / `SEMPRE`) e l'ultima istanza (`MAX(id)`).
  Il FE mostra "Ripeti" solo se `true` **e** esiste già un'istanza.
- `completato` / `percorribile` / `bloccante` (bool, da
  `fn_check_chiusura_pratica`) — fotografia chiusura: `bloccante=true` =
  obbligatorio, non completato, ancora percorribile (impedisce CHIUSA,
  guard DB 485).
- `ramo` (string) — sintesi per la resa visiva, 4 stati:
  - `COMPLETATO` — almeno un'istanza chiusa;
  - `PERCORRIBILE` — prerequisiti soddisfatti, eseguibile ora;
  - `FUTURO` — prerequisiti non ancora decisi (step a valle);
  - `RAMO_CHIUSO` — un prerequisito è stato DECISO (istanza COMPLETATO)
    ma mai con l'esito richiesto: il bivio ha preso l'altra strada. Stato
    "attuale": un retry del predecessore (se ripetibile) può riaprirlo.
  La verità esito-aware resta nella fn DB `fn_check_prerequisiti_flusso`
  (riusata nella query, nessuna regola duplicata lato BE).

### Descrittore documento sorgente `doc_*` (2026-07-02, proiezione V10 fase MOSTRA)

Ogni step espone lo stato **vivo** del documento di dominio agganciato al suo
flusso (`pratiche_sorgenti.flusso_id`), via
`script.vw_flusso_doc_sorgente` (una riga per flusso, dal 2026-11-08,
brief-db-sorgente-documento-e-riga BE-Z.1-a: la regola sta a DB, la copia BE
`_doc_sorgente_lateral` è ritirata). Ordine: prima il `ROOT`, poi risolto, non
terminale, il più recente — read-time, nessun mirror. Display fields puri:

- `doc_risolto` (bool|null) — `true` = proiezione reale; `false` = documento
  collegato ma dominio senza resolver (il FE degrada al milestone manuale);
  `null` = nessun documento agganciato allo step;
- `doc_stato_codice_interno` / `doc_stato_descrizione` — stato nativo del
  documento (display);
- `doc_fase` ∈ `APERTO · IN_CORSO · IN_ATTESA · CHIUSO` — vocabolario
  universale dichiarato dal dominio (colonne su `config.stati_doc_*`);
- `doc_esito` — verdetto proiettato (`POSITIVO`/`NEGATIVO`/… o null);
- `doc_terminale` (bool) — il documento non evolverà più;
- `doc_sorgente_descrizione` — etichetta del tipo sorgente (`config.sorgenti`).

Stessi campi esposti da coda lavoro (ancora per flusso, la stessa vista) e
dettaglio/lista pratiche (àncora della pratica, `script.vw_pratica_doc_sorgente`). Nota: la proiezione fotografa lo **stato scritto** sul
documento (es. scadenza flippata dal job notturno, non ricalcolata qui).

## Regole

- Ordine per `sequenza, template_flusso_id`.
- Un solo flusso per template nel risultato (l'ultimo per id), anche se ne
  esistono più d'uno (con la regola di ripetibilità D3 le istanze multiple
  sono legittime: vince la più recente per `MAX(id)`).
- La creazione del flusso template-bound avviene via
  `POST /api/v1/pratiche/<id>/flussi/` con `template_flusso_id`; i guard DB
  BEFORE INSERT rifiutano se lo step non è abilitato (prerequisiti
  esito-aware) o non è ripetibile (`409 E_PRATICHE_FLUSSO_NON_RIPETIBILE`,
  catalogo DB id 483).
- Permission: area `pratiche` (lettura).

## Dipendenze DB

- `pratiche.template_flussi` (i template attivi della definizione pinnata sulla pratica)
- `pratiche.azioni_ui`, `config.esiti_flussi_pratiche` (display)
- `pratiche.flussi` (istanze) + `config.stati_flussi_pratiche`
- `pratiche.fn_check_ripetibilita_flusso` (D3 — `ripetibile_adesso`)
- `pratiche.fn_check_chiusura_pratica` (D4 — `completato`/`percorribile`/`bloccante`)
- `pratiche.fn_check_prerequisiti_flusso` (distinzione `RAMO_CHIUSO`/`FUTURO`)
