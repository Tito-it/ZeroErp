# Piano BE — classe dei codici errore

**Chi:** team BE (`dev/backend-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 18 decisioni, le misure, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-db-classe-codici-errore](piano-db-classe-codici-errore.md).
**Stato:** ⏸️ **in attesa che il BE riparta** — ma vedi il §0: quasi tutto è già sbloccato.

---

## 0. Cosa serve dal DB per cominciare — meno di quanto sembra

Decisione di Tid (2026-08-07): **si sviluppa tutto il DB per primo, poi il BE.**
Verificando la sequenza è però emerso che *«prima il DB»* è una **scelta di
comodo, non un vincolo tecnico**:

| Passo BE | Prerequisito DB | Si può fare adesso? |
|---|---|---|
| **B-1** togliere la policy morta | — | ✅ **sì** |
| **B-2** `classe` senza status ⇒ eccezione | — | ✅ **sì** |
| **B-3** riorganizzare in 4 moduli | — (parziale, vedi sotto) | ✅ **sì, in gran parte** |
| **B-4** la mappa classe → HTTP, 8 righe | il **vocabolario**, già deciso nel brief §4 | ✅ **sì** |
| **B-5** il **generatore** | 🔴 `vw_codici_errore_identita` popolata — **D-9** | ❌ no |
| **B-6** il controllo di divergenza in CI | B-5 | ❌ no |

**Quattro passi su sei non aspettano niente.** Quando il BE riparte può fare
B-1..B-4 anche se il DB non ha ancora consegnato: sono tutte cose che vivono
dentro `apps/core/services/`, senza toccare il database.

⚠️ **L'unico vero cancello è D-9** (le due viste), che nel piano DB è il passo di
consegna. Prima di quello il generatore non ha da cui generare.

---

## 1. La sequenza

| # | Passo | Dipende da | Costo |
|---|---|---|---|
| **B-1** | Togliere `PREV_STATO_NON_MODIFICABILE` | — | una riga |
| **B-2** | `classe` senza status ⇒ **eccezione, non ripiego** | — | poche righe + test |
| **B-3** | Riorganizzare `error_policies.py` in **4 moduli** | — | il grosso del lavoro a mano |
| **B-4** | La mappa **classe → HTTP** (8 righe) + derivazione dello status | B-3 | piccolo |
| **B-5** | Il **generatore** di `error_policies_generated.py` | 🔴 DB **D-9** | medio |
| **B-6** | Il **controllo di divergenza** in CI | B-5 | piccolo |
| **B-7** | La regola «niente nuovi codici generici» | B-6 | coda |

---

## 2. I passi, in dettaglio

### B-1 · Togliere la policy morta

`PREV_STATO_NON_MODIFICABILE` (senza prefisso) in `error_policies.py` è **orfana**:
il gemello vivo `E_PREV_STATO_NON_MODIFICABILE` è a catalogo (id 714), e la riga
senza prefisso il DB l'ha cancellata il 2026-08-05 (`20260805-16`, «doppione
superato»).

Una riga da togliere. Nessun rischio: nessuno la risolve più.

---

### B-2 · `classe` senza status ⇒ eccezione

⚠️ **Oggi la garanzia non c'è, e il brief la dava per acquisita.** Verificato su
`ErrorPolicyRegistry.resolve`: **non fallisce mai**, ha due ripieghi —

| Codice non registrato | Cosa restituisce |
|---|---|
| comincia per `E_` | ripiego **400** «Errore di validazione» |
| tutto il resto, quindi ogni `W_` | `E_GENERICO` → **500** |

Quindi un **avviso** (classe `AVVISO`, che non ha uno status per progetto) che
sfuggisse al controllo (E) del guardrail non farebbe rumore: diventerebbe un
**500 tecnico col messaggio soppresso** — il difetto `E_DATABASE` da cui è nato
tutto il filone.

**Cosa fare:** nel percorso che deriva lo status dalla classe, *classe senza
status mappato ⇒ solleva*. La garanzia va scritta in una riga di codice,
altrimenti non c'è.

⚠️ **Non toccare i due ripieghi esistenti in questo passo.** Restano finché il
generatore non è in servizio: sono ciò che tiene in piedi i codici nuovi che il DB
sta creando (lo split di `E_VALIDAZIONE`) mentre il BE è fermo.

---

### B-3 · I quattro moduli — separati per **quando cambiano**

È il criterio scelto: non per contenuto, per **destino**. Il valore sta nel fatto
che ogni file ha una vita sua.

| Modulo | Cosa | Chi lo scrive | Quando cambia |
|---|---|---|---|
| `error_policies_generated.py` | `codice → classe`, 659 voci | **generato dal DB** (B-5) | a ogni seed |
| `error_policies.py` (registry) | `classe → (status, ui_action di default)` — 8 righe + la logica | a mano | quasi mai |
| `error_ui_overrides.py` | i **174** `ui_action` fuori default, **coi loro commenti** | a mano | quando cambia una scelta di UI |
| `error_messages_fallback.py` | i `user_message` | a mano, **per ora** | quando si spostano al catalogo |

**Si può fare adesso**, con i contenuti attuali scritti a mano: il modulo
`_generated` nasce come file normale e diventa generato al B-5. Il resto della
separazione non dipende dal DB.

⚠️ **I 194 blocchi di commento vanno con il pezzo che spiegano**, ed è la ragione
per cui gli override stanno in codice e non in un CSV: sono **decisioni con una
motivazione**, e un CSV non porta un paragrafo. Esempio, su `E_CONTO_BANCARIO`:

> *«la guard è `attivo IS NOT TRUE`, che copre DUE casi: conto disattivato e conto
> inesistente. Il 400 col campo evidenziato è corretto in entrambi; un 404
> sarebbe giusto solo nel secondo e svuoterebbe la pagina nel primo.»*

**La regola su dove va ciascun commento:**

| Il perché di… | Va in |
|---|---|
| **la classe** | `config.codici_errore.note` — lato DB |
| **la `ui_action`** | `error_ui_overrides.py` |
| **un ritiro, una storia** | il brief che l'ha deciso |

⭐ **Sul quarto modulo, il nome è la sostanza.** I `user_message` **non
duplicano** il catalogo: sono la variante **senza segnaposto** — misurato, **0 su
656** contengono `%s` contro **371 a catalogo** (56%). Sono il ripiego per quando
il messaggio del DB non è arrivato. Chiamare il file `fallback` fa due cose: dice
la verità su cosa sono, e rende la mossa futura una **cancellazione di file**
invece che un refactor.

⚠️ **E quella mossa futura costa più di come sembrava**: spostarli al catalogo
richiede una **seconda variante argument-free** per **371 codici**, non «muovere
659 stringhe».

---

### B-4 · La mappa classe → HTTP, e la derivazione dello status

Otto righe scritte a mano — sette status più `AVVISO`, che non ne ha uno:

| classe | HTTP |
|---|---|
| `DATO_ERRATO` | 400 |
| `CONFLITTO_STATO` | 409 |
| `NON_TROVATO` | 404 |
| `TECNICO` | 500 |
| `NON_PERMESSO` | 403 |
| `NON_ESEGUIBILE` | 422 |
| `NON_DISPONIBILE` | 501 |
| `AVVISO` | **nessuno** → B-2: solleva |

**Restano fuori 5 codici**, mappati a mano perché non passano dall'exception
handler: `E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`,
`E_AUTHENTICATION_FAILED`, `E_NOT_AUTHENTICATED` (401) e `E_AI_PROVIDER_ERROR`
(502).

⚠️ **`ui_action` non si deriva dalla classe, e il numero conta.** Misurato
659/659:

| classe | totale | dominante | override |
|---|---|---|---|
| `DATO_ERRATO` (400) | 234 | `show_error_banner` **117** | **117** |
| `CONFLITTO_STATO` (409) | 224 | `show_error_banner` 205 | 19 |
| `NON_TROVATO` (404) | 84 | `show_empty_state` 50 | **34** |
| `TECNICO` (500) | 63 | `show_error_banner` 62 | 1 |
| `NON_PERMESSO` (403) | 23 | `show_error_banner` 23 | 0 |
| `NON_ESEGUIBILE` (422) | 22 | `show_error_banner` 20 | 2 |
| `NON_DISPONIBILE` (501) | 4 | `show_error_banner` 3 | 1 |
| | | **totale** | **174** |

⚠️ **Sulla classe più numerosa il default è un lancio di moneta: 117 contro 117.**
Non «quasi a metà» — esattamente a metà. Il discriminante non è la classe ma
**dove manca il dato**: sul form in corso (campo evidenziato) o sull'entità
collegata (banner). È un'informazione che la classe non porta e non può portare.

Il guadagno resta reale ma va detto per quello che è: **da 659 voci a 174 + 8
regole**, non «a otto».

---

### B-5 · Il generatore — 🔴 **qui serve il DB**

**Prerequisito: DB D-9.** `config.vw_codici_errore_identita` esiste, è popolata e
ordinata.

```sql
-- Sorgente di error_policies_generated.py.
-- Una riga per codice, nessun join, nessun filtro lingua da sbagliare.
SELECT codice, classe, obsoleto_dal, note
  FROM config.vw_codici_errore_identita
 ORDER BY codice;
```

⚠️ **Non usare `config.vw_codici_errore`**: è la vista di *revisione*, ha **una
riga per (codice, lingua)** e, essendo un `LEFT JOIN`, un codice senza messaggio
ci compare con `lingua IS NULL`. Filtrarla per `lingua = 'it'` perderebbe proprio
quei codici.

⚠️ **`ORDER BY codice` anche nella query**, benché la vista lo porti già: un
generatore che produce **diff spurii per riordino** diventa un file che nessuno
rilegge, e da lì a non accorgersi di una **classe cambiata** è un passo solo.

**Il file generato deve dirlo di sé**: intestazione «generato, non modificare a
mano», con il comando che lo rigenera.

---

### B-6 · Il controllo di divergenza in CI

`test_error_codes_db_policy_guardrail` **cambia mestiere per la seconda volta**:
da unico presidio, a rete di sicurezza, a **controllo che il file generato non
diverga dal DB**.

⚠️ **Vale la stessa fragilità dei 3 end-to-end**: il test ha bisogno di una
connessione a un DB **provvisto da Liquibase**, e ce l'ha solo perché nessun test
Django dichiara un database. Il giorno in cui uno lo farà, va adeguato insieme
agli altri — sta scritto in `.codex/AGENTS.md` §Regole test Django.

⚠️ **E un cancello che salta non presidia niente**: se il guard di `setUpClass`
lo fa skippare, va riportato su un DB provvisto, non lasciato skippato.

---

### B-7 · Niente nuovi codici generici

Coda del lavoro, insieme al DB. La classe **non cura** gli accumulatori: assegna
una classe ufficiale a un codice che ne vorrebbe cinque.

* `E_VALIDAZIONE` lo spezza il DB **prima del seed** (D-3);
* `E_PARAMETRO_INVALIDO` (112-114 funzioni) resta col **denominatore sicuro** e la
  ragione in `note`: è un cantiere suo.

La regola vieta i **nuovi**, come si è fatto per i codici fuori convenzione:
rincorrere gli esistenti senza chiudere il rubinetto è la forma in cui questi
registri non calano mai.

---

## 3. Cosa **non** cambia, e non va toccato

* il **multilingua dei messaggi**: `config.messaggi_errore` resta chiavata
  `(codice, lingua)`, `script.fn_get_messaggio` resta identica;
* la lettura del codice dall'eccezione — `apps/core/services/db_error_fields.py`
  resta il punto unico, e il contratto *«`P0001` + `CONSTRAINT` valorizzato =
  errore di dominio»* non cambia;
* `dbops.error_log` continua a puntare alla riga tradotta.

---

## 4. Da sapere mentre il DB lavora

⚠️ **I codici nuovi creati dal DB non hanno una policy finché il BE è fermo.**
Lo split di `E_VALIDAZIONE` (D-3) crea codici che cadono sul ripiego 400 di
`resolve()`. **Non è una regressione** — è il comportamento di oggi per ogni
codice nuovo — ma significa che lo split **non cambia niente di visibile** finché
il BE non riparte. Quando riparte, i nuovi codici arrivano gratis col generatore
(B-5): non c'è da registrarli a mano.
