## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_guard_esito_classe`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.trgfn_template_flussi_guard_modalita_esito](trgfn_template_flussi_guard_modalita_esito.md)
> [pratiche.trgfn_flussi_guard_transizione](trgfn_flussi_guard_transizione.md)
>
Tabelle:
>
[pratiche.flussi](flussi.md)
> [pratiche.template_flussi](template_flussi.md)
> [config.esiti_flussi_pratiche](../../config/manual/esiti_flussi_pratiche.md)

---
### 🎯 Scopo Principale

Guard **runtime di classe esito** al completamento del flusso: alla transizione verso
COMPLETATO la classe dell'esito deve corrispondere alla `modalita_esito` del template.
È la **difesa in profondità autoritativa** dell'invariante degli step a esito di
dominio — vale per qualunque percorso di scrittura (BB di dominio, percorso generico,
UPDATE SQL diretto).

| Classe step | Esito ammesso al completamento |
|---|---|
| `modalita_esito = DOMINIO` | solo esiti di **ramo** (`is_verdetto = false`, es. MERCE_PRESENTE/SOLO_SERVIZI) |
| `modalita_esito` ≠ DOMINIO (MANUALE/AUTOMATICO/CONTESTUALE) | solo **verdetti** (`is_verdetto = true`, es. POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE) |

**Origine**: incidente `PRA-0000243` — lo step SMISTAMENTO (bivio, esito calcolato da
`vendite.completa_smistamento`) fu chiuso con `POSITIVO` via percorso generico: il ramo
merce non si attivò, la pratica si auto-chiuse e ordine→commessa furono completati a
mano fuori pratica. La direzione simmetrica (esito di ramo su step normale) prima era
fermata solo dal guard BE lato operatore.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_flussi_a10_guard_esito_classe_ins_upd` | BEFORE | INSERT, UPDATE OF `stato_id` | `pratiche.flussi` |

Fase `_a10_` (guard/block). Ordine lessicografico: `..._guard_esito_classe_...` scatta
**prima** di `..._guard_esito_completato_...` — con esito NULL questo guard esce subito
e il 477 solleva il suo errore.

---

### Regole

* Scatta **solo alla transizione verso COMPLETATO**: INSERT già COMPLETATO, oppure
  UPDATE con `stato_id` realmente cambiato. Le righe **già completate restano
  toccabili** sulle altre colonne: il flusso 543 di `PRA-0000243` porta storicamente un
  verdetto su uno step ora DOMINIO e non deve diventare un sasso intoccabile (nessuna
  migrazione dati).
* `esito NULL` a COMPLETATO → fuori scope, competenza del guard
  `FLUSSI_ESITO_OBBLIGATORIO` (477).
* Flusso **senza template** (`template_flusso_id NULL`) → classe verdetto (trattato come
  MANUALE, coerente col backend).
* Nessuna logica di idempotenza/re-fire: il no-op sugli stati terminali è garantito a
  monte (BE `completa_step_pratica`) e dalla matrice transizioni (nessuna uscita da
  COMPLETATO).

---

### Note operative

* Errore sollevato: `FLUSSI_ESITO_NON_AMMESSO` (504), con l'esito, il codice dello step
  e la classe attesa. Il messaggio contiene la sottostringa stabile **"non ammesso per
  lo step"** — è il marker per `_KNOWN_DB_ERROR_MARKERS` lato BE: non riformularlo senza
  coordinarsi.
* **Complementarità col BE (non ridondanza)**: questo guard enforce l'invariante di
  **valore** (classe esito giusta per lo step); `require_esito_selezionabile_operatore`
  (BE) enforce quella di **autorizzazione** (l'operatore invia a mano solo verdetti) —
  il DB non distingue chi scrive. Insieme: un bivio DOMINIO si completa solo via
  building block di dominio.
* Introdotta con `20260702-17` (brief-db-step-dominio-e-definizioni-versionate, Parte 1).
* Test: `db/pgtap/pratiche/test-guard-esito-classe.sql` (entrambe le direzioni, riga
  legacy, INSERT diretto); fixture adeguata in
  `db/pgtap/pratiche/test-chiusura-nessun-lavoro-pendente.sql` (NP_SMIST → DOMINIO).
