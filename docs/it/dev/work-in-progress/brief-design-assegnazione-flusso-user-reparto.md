# Brief design — Assegnazione del flusso a operatore o reparto

> **Tipo documento**: brief design (autorevole) BE + FE.
> **Priorità**: 🟢 normale.
> **Data**: 2026-06-18 · **Stato**: 🟡 **design** — niente codice scritto.
> **Prerequisito DB**: modifiche a 2 funzioni + nuovo trigger giornale — vedi
> [brief-db-assegnazione-flusso.md](brief-db-assegnazione-flusso.md)
> ([[feedback_db_actions_passaggio_team]] · [[feedback_be_fe_attende_prerequisiti_db]]).
>
> Sessione dopo [[handoff_20260618_pratiche_esito_configurabile_giornale]]. Estende il
> workflow pratiche: rendere **assegnabile il singolo flusso** (step) a un operatore e/o a
> un reparto, con policy di eligibilità **reparto-first**.

---

## 1. Contesto

Assegnazione oggi **solo a livello pratica** (`pratiche.pratiche.risorsa_umana_id` +
`unita_organizzativa_id`, via `assegna_pratica` + `POST /pratiche/<id>/assegnazione/`,
giornale `ASSEGNAZIONE_CAMBIATA`).

Il **singolo flusso** ha il modello pronto ma non l'azione esplicita né la policy desiderata:

| Pezzo | Stato | Dettaglio |
|---|---|---|
| `pratiche.flussi.risorsa_umana_id` / `unita_organizzativa_id` (+FK) | ✅ esistono | operatore + reparto, nullable |
| `risorse_umane.unita_organizzativa_id` (+FK) | ✅ esiste | reparto **anagrafico** dell'operatore |
| `create_flusso(...)` | ✅ | accetta già i due campi in creazione |
| `prendi_in_carico` (`fn_prendi_in_carico_flusso`) | ⚠️ | auto-presa, ma **competenza OBBLIGATORIA** (`FLUSSI_COMPETENZA_MANCANTE`) |
| `competenze_flussi` (matrice) | ✅ | (template, reparto, operatore) abilitato |
| `fn_coda_lavoro_operatore` (3 livelli) | ⚠️ | ASSEGNATO/COMPETENZA/REPARTO **tutti gated dalla matrice competenze** (il livello REPARTO usa i reparti-da-competenza, NON il reparto anagrafico) |
| **Assegnazione esplicita di un flusso esistente** | ❌ manca | a un altro operatore o a un reparto |
| **Trigger giornale assegnazione flusso** | ❌ manca | la pratica ce l'ha, il flusso no |

## 2. Modello deciso (2026-06-18)

### 2.1 Routing — a chi è destinato il flusso

- `flussi.unita_organizzativa_id` = **reparto** (instradamento a coda di reparto).
- `flussi.risorsa_umana_id` = **operatore specifico**. Per assegnare un operatore "qualcuno
  indica l'operatore **di quel reparto**" → il picker FE mostra **solo gli operatori del
  reparto** (vedi §4). I due campi non sono mutuamente esclusivi.
- **Niente configurato** → il flusso non ha reparto né operatore: lo prende **chi se ne
  prende carico ed esegue** (auto-presa libera, vedi 2.2 caso C). Assegnazione manuale ad
  altri step aperti: ipotesi aperta, **non** in scope ora (se ne parla).

### 2.2 Eligibilità — chi vede/prende un flusso (policy **reparto-first + competenza opzionale**)

Per un flusso `F` `DA_ESEGUIRE` non ancora assegnato e un operatore `O`:

- Sia **skill-lock** = esiste almeno una riga `competenze_flussi` per `F.template_flusso_id`
  (la matrice è configurata per quel tipo di step);
- Sia **competente** = esiste riga `competenze_flussi(template = F.template, operatore = O, attivo)`;
- Sia **nel-reparto** = `F.unita_organizzativa_id IS NOT NULL AND O.unita_organizzativa_id = F.unita_organizzativa_id` (reparto **anagrafico**).

`O` è eligibile se:

| Caso | Condizione su F | Regola eligibilità |
|---|---|---|
| **A — reparto + skill** | reparto valorizzato, skill-lock presente | `competente` (la matrice raffina: solo operatori abilitati di quel reparto) |
| **B — reparto, niente skill** | reparto valorizzato, skill-lock assente | `nel-reparto` (tutti gli operatori del reparto) |
| **C — niente configurato** | reparto NULL, skill-lock assente | **libero**: chiunque (auto-presa, punto 1) |
| **D — skill senza reparto** | reparto NULL, skill-lock presente | `competente` (il lucchetto-skill vale anche senza reparto) |

In una riga: **la competenza è un lucchetto opzionale**; quando per quel template non
esiste alcuna competenza, governa l'appartenenza al reparto (o la presa libera se nemmeno il
reparto è impostato). Questo è esattamente il modello richiesto e **sostituisce** l'attuale
obbligo di competenza incondizionato.

> Differenza con oggi (le 2 contraddizioni risolte): ① oggi senza competenza **nessuno**
> prende → con B/C diventa possibile; ② oggi "reparto" = reparti-da-competenza → diventa il
> reparto **anagrafico** (`risorse_umane.unita_organizzativa_id`).

## 3. Backend — deliverable

### 3.1 Service `assegna_flusso` (`apps/pratiche/services/pratiche_service.py`)

Clone simmetrico di `assegna_pratica`, su `flussi`:

```python
# Scopo: Assegna un flusso esistente a un operatore e/o a un reparto.
def assegna_flusso(
    flusso_id: int,
    *,
    risorsa_umana_id: int | None = None,
    unita_organizzativa_id: int | None = None,
    set_risorsa: bool = False,   # True = applica risorsa_umana_id (anche null = de-assegna)
    set_unita: bool = False,     # True = applica unita_organizzativa_id (anche null)
) -> None:
```

- Guard `flusso_id > 0` (`E_INVALID_ID` + assert). Costruisce `update_data` solo per i campi
  "toccati" (flag `set_*`) → consente l'azzeramento esplicito. Riusa `repo.update_flusso`.
- No-op se nessun flag. Validazione FK (operatore/reparto esistenti+attivi) lasciata al DB
  ([[feedback_bug_logici_modello]]). La coerenza "operatore appartiene al reparto" è un
  vincolo **UX** (picker filtrato), non un guard DB in questa fase.

### 3.2 Endpoint `ApiPraticaFlussoAssegnazione` (`apps/pratiche/api/views.py`)

```text
POST /api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/assegnazione/
```

- `DomainAPIView`, `area_funzionale = "pratiche"`, `post_permission = "assegna_pratica"`
  (riuso stessa azione di processo). `handle_post_json` + handler → `assegna_flusso`, con
  `optional_int(...)` e flag `set_* = "<key>" in payload`. `@extend_schema` inline. Route in
  `urls_v1.py`, name `pratiche-flusso-assegnazione`.

### 3.3 Lookup "operatori del reparto" (NUOVO — serve al picker FE)

Non esiste un lookup risorse umane filtrabile per reparto per la selezione (solo
`OperatoriListView` admin in amm_software). Serve un lookup leggero:

```text
GET /api/v1/pratiche/operatori/?unita_organizzativa_id=<id>   (oppure lookup core dedicato)
```

Ritorna `{id, display}` delle `risorse_umane` attive del reparto. Collocazione da valutare
(core lookup vs endpoint pratiche); `skip_area_check` se consumato cross-area
([[feedback_lookup_skip_area_check]]). Scope emittente da valutare.

### 3.4 Proiezione lettura

`get_flusso` + lista flussi espongono `risorsa_umana_id`/`unita_organizzativa_id` con
**display fields** via JOIN (`risorsa_umana_display`, `unita_organizzativa_descrizione`) —
[[feedback_display_fields_backend]]. Verificare in `pratiche_repository`.

### 3.5 Test

- service: assegna operatore / reparto / entrambi / de-assegna (null) / no-op / guard id.
- api: 200 happy path, payload parziale, permesso negato.
- (la nuova eligibilità vive nelle funzioni DB → test pgTAP lato DB, vedi brief DB).

## 4. Frontend — deliverable

Azione **"Assegna"** sul flusso (entry point: `DrawerActionsBar` del
[FlussoDrawer.vue](../../../../frontend/src/pratiche/components/FlussoDrawer.vue) e/o azione
di riga in [PraticaPercorso.vue](../../../../frontend/src/pratiche/components/PraticaPercorso.vue)).

Dialog `AppDialog` (width `sm`/`md`):
1. **Reparto** — lookup `config.unita_organizzative` (lookup generico se codice/descrizione,
   [[feedback_lookup_whitelist_first]]). Scelto **per primo**.
2. **Operatore** (opzionale) — lookup §3.3 **filtrato sul reparto scelto**; disabilitato finché
   non c'è un reparto. Coerente con "qualcuno indica l'operatore di quel reparto".
3. Entrambi svuotabili (de-assegna → `null` esplicito).

`readonly`-aware ([[feedback_drawer_readonly]]); save via action store già-unwrappata
([[feedback_useapihandler_solo_axios]]); dopo save refresh percorso + giornale.

Store `pratiche.js`: `assegnaFlusso(praticaId, flussoId, payload)` + API client.
i18n: `pratiche.flusso_assegna`, `pratiche.flusso_reparto`, `pratiche.flusso_assegnatario`.

La coda lavoro ([PraticheCodaLavoro.vue](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue))
"cose da fare" **non ancora sviluppata** come vista autonoma piena: oggi mostra i 3 livelli
da `fn_coda_lavoro_operatore`. Con la nuova eligibilità reparto-first i livelli COMPETENZA/REPARTO
cambiano semantica (vedi brief DB). Lavoro FE coda = fase successiva.

## 5. Prerequisito DB (brief separato)

[brief-db-assegnazione-flusso.md](brief-db-assegnazione-flusso.md) — tre interventi:
1. trigger giornale assegnazione flusso (oggi assente);
2. `fn_prendi_in_carico_flusso`: competenza da obbligatoria a **condizionale** (policy §2.2);
3. `fn_coda_lavoro_operatore`: livello REPARTO su reparto **anagrafico** + competenza come
   raffinamento (policy §2.2).

Il BE `assegna_flusso` + endpoint non dipendono da questi (scrivono solo le colonne), ma la
**semantica completa** (presa libera, coda reparto) si chiude solo coi punti 2-3.

## 6. Aperto / rinviato

- Assegnazione manuale ad altri operatori su step già aperti (oltre la presa in carico):
  ipotesi da discutere.
- Algoritmo di **bilanciamento carico** (assegnazione automatica in base a disponibilità/carico
  del personale del reparto): processo successivo, fuori scope.
- Default di assegnazione/reparto sul `template_flussi` (instradamento automatico per
  tipo step): estensione futura.
- Entry point FE definitivo (drawer vs percorso) e collocazione lookup operatori: fase FE.
