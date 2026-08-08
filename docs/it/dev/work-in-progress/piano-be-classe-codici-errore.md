# Piano BE — classe dei codici errore

**Chi:** team BE (`dev/backend-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 18 decisioni, le misure, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-db-classe-codici-errore](piano-db-classe-codici-errore.md).
**Stato:** 🟢 **B-1 → B-6 FATTI** (2026-08-07): il generatore è in servizio, `error_policies_generated.py` **non si scrive più a mano** (§9).
🟢 **§12 passi 1-2 FATTI** (2026-08-08): l'envelope porta i **campi da correggere** e li legano **38 componenti** — ⚠️ i campi sì, la `ui_action` **no**, e il perché è misurato (§12.12).
🔵 Resta il **passo 4** (il campo dagli errori PL/pgSQL, `USING COLUMN`) — ora ha senso chiederlo, perché il consumatore esiste su 38 schermate invece che su una.
🔴 Il **B-7 resta aperto per intero**, ed è quasi tutto DB (§11).

> **Verifica dell'equivalenza, prima di tutto il resto.** I **656** codici che
> restano una risposta HTTP risolvono **identici** a prima — stesso status,
> stessa `ui_action`, stesso messaggio — confrontando `resolve()` di prima del
> cantiere e di adesso uno per uno; i due ripieghi rispondono come prima. Suite
> Django: **3601 test verdi**, compreso il cancello del terzo lato e il controllo
> di divergenza, entrambi contro il DB vero (`ZEROERP_TEST_DB_E2E=1`).
>
> **Le sole differenze sono volute, e ognuna è un difetto che se ne va:**
>
> | Codice | Prima | Ora |
> |---|---|---|
> | `PREV_STATO_NON_MODIFICABILE` | 409 | **non esiste più** — policy orfana (B-1) |
> | `W_TXID_NOT_REGISTERED` | **500** col messaggio soppresso | **solleva** — è un avviso, non un guasto (B-2) |
> | i 2 gemelli col prefisso `E_` | risolvevano | **non esistono più** — non erano a catalogo (§9.3) |
>
> ⚠️ **Sette cose sono emerse facendolo**: §6 (tre, scrivendo il B-3), §8 (due,
> dal riallineamento al catalogo — di cui una **toglie** un'eccezione al disegno)
> e §9 (due, generando davvero: un generatore che si mura fuori, e `has()` che
> cambia significato).

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
| **B-5** il **generatore** | `vw_codici_errore_identita` popolata — **D-9** | ✅ **arrivato in serata** |
| **B-6** il controllo di divergenza in CI | B-5 | ✅ **sì, subito dopo** |

**Quattro passi su sei non aspettano niente.** Quando il BE riparte può fare
B-1..B-4 anche se il DB non ha ancora consegnato: sono tutte cose che vivono
dentro `apps/core/services/`, senza toccare il database.

⚠️ **L'unico vero cancello è D-9** (le due viste), che nel piano DB è il passo di
consegna. Prima di quello il generatore non ha da cui generare.

---

## 1. La sequenza

| # | Passo | Dipende da | Costo | Stato |
|---|---|---|---|---|
| **B-1** | Togliere `PREV_STATO_NON_MODIFICABILE` | — | una riga | ✅ 2026-08-07 |
| **B-2** | `classe` senza status ⇒ **eccezione, non ripiego** | — | poche righe + test | ✅ 2026-08-07 |
| **B-3** | Riorganizzare `error_policies.py` in **4 moduli** | — | il grosso del lavoro a mano | ✅ 2026-08-07 |
| **B-4** | La mappa **classe → HTTP** (8 righe) + derivazione dello status | B-3 | piccolo | ✅ 2026-08-07 |
| **B-5** | Il **generatore** di `error_policies_generated.py` | ✅ DB **D-9** consegnato | medio | ✅ 2026-08-07 |
| **B-6** | Il **controllo di divergenza** in CI | B-5 | piccolo | ✅ 2026-08-07 |
| **B-7** | La regola «niente nuovi codici generici» | B-6 | coda | 🔴 **aperto** — e quasi tutto DB (§11) |

**Cosa esiste ora, in quattro file** (`backend/apps/core/services/`):

| File | Righe | Voci | Chi lo scriverà |
|---|---|---|---|
| `error_policies_generated.py` | 1086 | **689** `codice → classe` (79 ritirate) | ⛔ **il generatore** |
| `error_policies.py` | 255 | le **10 + 9 + 9** righe di regole + la logica | a mano, quasi mai |
| `error_ui_overrides.py` | 514 | **176** `ui_action` fuori default | a mano |
| `error_messages_fallback.py` | 703 | i messaggi senza segnaposto (solo i vivi) | a mano, per ora |
| `management/commands/genera_error_policies.py` | 211 | il generatore + `--check` | a mano |
| `tests/services/test_error_policies_classi.py` | 331 | **17 test** sui modi nuovi di rompersi | — |
| `tests/test_error_policies_divergenza_db.py` | 117 | **2 test**: il B-6 | — |

⚠️ **Le righe di regole sono 10 + 9 + 9 e non 8 + 7 + 7** come dice il §2 qui
sotto: il vocabolario è andato a dieci valori (§8.1) e con lui è **sparita** la
mappa per codice che il B-4 aveva scritto. Il §2 resta com'era perché è la
prescrizione originale; dove i numeri divergono, valgono i §6 e §8.

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

**Prerequisito 1: DB D-9.** `config.vw_codici_errore_identita` esiste, è popolata e
ordinata.

🔴 **Prerequisito 2, scoperto scrivendo il B-3 e più insidioso del primo: le
`note` devono essere a catalogo PRIMA della prima rigenerazione.** Oggi
`error_policies_generated.py` contiene **215 blocchi di commento, 731 righe** —
il perché della classe di ogni codice che non ha un override di UI, cioè il
residuo delle 150 decisioni del cantiere del terzo lato. Il generatore li
**riscrive via**. L'estratto pronto per il seed è
[`allegati/codici-errore-classe-note.csv`](allegati/codici-errore-classe-note.csv)
(658 righe `codice,classe,note`, `note` valorizzata su 215). Vedi §6.2.

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

> ⚠️ **Aggiornamento del 2026-08-07 sera: i due accumulatori erano uno, e forse
> nessuno.** Il team DB, eseguendo il D-3, ha contato le **condizioni** invece
> delle funzioni:
>
> | Codice | Punti | Guard di parametro | Altro |
> |---|---:|---:|---:|
> | `E_VALIDAZIONE` | 13 | **13** | **0** |
> | `E_PARAMETRO_INVALIDO` | 177 | 160 (90%) | 17 |
>
> **`E_VALIDAZIONE` non si spezza: il D-3 è chiuso senza fare niente**, e con lui
> sparisce l'unica scadenza del piano DB. ⚠️ E la cosa che ci riguarda: l'esempio
> che reggeva l'argomento era **nostro** (annotazione A1 del brief) —
> *«`fn_annulla_reso` che rifiuta un annullamento è `CONFLITTO_STATO`»* — e quel
> punto non esiste: lì `E_VALIDAZIONE` scatta su `p_reso_id IS NULL OR <= 0`.
>
> ⭐ **La lezione è di metodo, ed è nostra:** *un codice è un accumulatore quando
> copre **condizioni** diverse, non quando è usato in **domini** diversi.* «10
> funzioni, 5 domini» era un numero vero che misurava la cosa sbagliata. La
> regola è ora scritta in [api.md §Tassonomia](../api.md).

* `E_VALIDAZIONE`: ~~lo spezza il DB prima del seed~~ → **non è un accumulatore**,
  `DATO_ERRATO` è giusto per tutti e 13 i punti;
* `E_PARAMETRO_INVALIDO` (177 punti) resta col **denominatore sicuro** e la
  ragione in `note` — ma il cantiere non è più «114 funzioni»: sono **17 punti**
  da guardare con la lente.

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

⚠️ **I codici nuovi creati dal DB non hanno una policy finché il generatore non
c'è.** Cadono sul ripiego 400 di `resolve()`: **non è una regressione** — è il
comportamento di oggi per ogni codice nuovo — ma va saputo. Quando il B-5 sarà
in servizio arriveranno gratis col generatore: non c'è da registrarli a mano.

Oggi sono **tre**, e sono i tre «progettati mai cablati» del push preventivo che
il D-2 ha classificato: `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA`,
`E_VENDITA_COMPETENZA_RICHIESTA` (`DATO_ERRATO`) e
`E_VENDITA_PREVENTIVO_GIA_PUSHATO` (`CONFLITTO_STATO`). ⚠️ Il ripiego dà a tutti
e tre un **400**: sul terzo la verità è **409**. Nessuno li solleva, quindi oggi
non fa danno — ma se qualcuno li caglia prima del B-5, quello è il momento di
registrarli a mano.

~~Lo split di `E_VALIDAZIONE` (D-3)~~ → non si fa: vedi il B-7.

---

## 5. ✅ Cosa il BE ha consegnato al DB — **consumato, il 2026-08-07**

> **Chiuso in giornata.** Il DB ha eseguito D-1 e D-2 con questa consegna: le
> **215 note sono a catalogo**, 213 dirette e 2 rimappate sui gemelli senza
> prefisso, **zero perse, zero collisioni**. Il §6.2 si chiude.
>
> ⚠️ **Il nostro CSV non poteva essere il seed, e la ragione è istruttiva**: ha
> l'universo delle **policy** (658), il seed vuole quello del **catalogo** (689).
> Come seed avrebbe lasciato 33 codici senza padre — violazione di FK al primo
> migrate su DB ricostruito — e aggiunto 2 righe inesistenti. Serviva la sua
> **terza colonna**, e quella è arrivata intera.
>
> ✅ **`allegati/codici-errore-classe-note.csv` RESTA** — decisione di Tid,
> 2026-08-08. Avevo proposto di toglierlo come «secondo elenco»: la proposta era
> sbagliata, ed è utile sapere perché.
>
> **Non è un secondo elenco: è un allegato di consegna.** Un secondo elenco è
> qualcosa da cui il software legge, e che quindi può divergere in silenzio —
> questo non lo legge nessun programma. È la **prova di cosa è stato consegnato
> al DB e in che forma**, e i due piani lo citano come tale (il piano DB al
> D-2-bis, questo file qui e al §6.2).
>
> ⚠️ **La fonte di verità resta una sola e non è questa**:
> `db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv`, presidiata
> dai due ponti del §8.3. L'allegato non entra in nessun confronto: se un domani
> divergerà dal catalogo non sarà un difetto, sarà solo un documento che
> fotografa il 2026-08-07.

### 5.1 🔴 **La sorgente del passo D-1 è cambiata sotto i piedi**

Il piano DB al **D-1** dice: *«uno script che legge
`backend/apps/core/services/error_policies.py` e produce `codice,classe`»*,
mappando lo `http_status` di ogni voce, con l'avvertenza di *«delimitare ogni
voce con la chiave successiva, perché 32 voci sono su una riga sola»*.

⚠️ **Quello script ora non trova più niente**: in `error_policies.py` non c'è
più nessun `http_status=` per codice — ci sono sette righe `classe → status`.

**La buona notizia è che il passo diventa più corto, non più lungo.** La classe
non va più dedotta: è scritta.

```python
# 658 voci, ordinate per codice, nessun parser da scrivere
from apps.core.services.error_policies_generated import CLASSE_PER_CODICE
```

E per chi preferisce non importare Python, la stessa cosa è già un CSV pronto
per `loadUpdateData`: **[`allegati/codici-errore-classe-note.csv`](allegati/codici-errore-classe-note.csv)**,
tre colonne `codice,classe,note`.

Con esso i tre avvertimenti del D-1 si sciolgono da soli:

| Avvertimento del D-1 | Ora |
|---|---|
| «32 voci su una riga sola, il parser le perde» | ✅ non c'è più un parser |
| «5 codici da decidere a mano» (401×4, 502) | ✅ già dentro, con classe `TECNICO` come proposto — ⚠️ resta da **confermare con Tid** |
| «escludere `PREV_STATO_NON_MODIFICABILE`, è morto» | ✅ già escluso (B-1) |

⚠️ **La `classe` dei 5 non cambia più la risposta HTTP**, qualunque sia: lo
status di quei codici è scritto a mano in `HTTP_PER_CODICE` perché non passano
dall'exception handler. Se al seed si preferisse un'altra classe, il BE non se
ne accorge — ed è voluto.

### 5.2 Le `note`: 215 righe già scritte, da seminare

La terza colonna del CSV è la ragione della classe, presa **parola per parola**
dai commenti che il cantiere del terzo lato aveva lasciato accanto a ogni
policy. Sono conformi alla **D18**: una riga sola, gli a capo sono già collassati
in ` · `.

Sono valorizzate su **215 codici su 658** — quelli il cui commento spiega la
*classe*. Gli altri 67 blocchi di commento spiegano una scelta di *interfaccia* e
restano lato BE in `error_ui_overrides.py`: è la ripartizione della §14.3 del
brief, e **nessun paragrafo sta in due posti**.

---

## 6. ⚠️ Tre cose emerse eseguendo B-1..B-4

### 6.1 Gli override sono **176**, non 174 — e il conto quadra

I due `redirect_login` di `E_JWT_SENZA_IDENTITA` e `E_IDENTITA_NON_ATTIVA`. La
misura del brief (174) contava le sette classi di dominio su 654 codici, cioè
**escludeva i 5 fuori vocabolario**; una volta che anche quei 5 prendono una
classe (`TECNICO`, come chiede il seed), due di loro hanno una `ui_action` che
non è il default della classe. Non è una scoperta, è la stessa misura su un
perimetro di 658 invece che di 654 — va scritta perché il numero «174» compare
in tre documenti e adesso ce n'è un quarto che dice 176.

### 6.2 🔴 **I quattro moduli non hanno una casa per il perché della classe**

È il rilievo che conta, e non si vede leggendo il brief: si vede contando.

| | quanti |
|---:|---|
| voci con un commento | **282** |
| di queste, con un **override** di UI → casa stabile in `error_ui_overrides.py` | 67 |
| **senza** override → oggi stanno in `error_policies_generated.py` | **215** |
| righe di ragionamento su quel percorso | **731** |

Il §14.2 del brief sceglie i quattro moduli e ne dà la ragione più forte che ci
sia — *«un CSV non porta un paragrafo, e quei paragrafi sono esattamente la cosa
che questo cantiere è servito a non perdere»*. Ma la **destinazione** di quei
paragrafi (§14.3: *il perché della classe va in `config.codici_errore.note`*)
attraversa il modulo che **verrà riscritto da un generatore**. Non è una
contraddizione del disegno: è un passo mancante nella sequenza.

**Come è stato chiuso**, senza inventare un quinto modulo e senza duplicare
niente:

1. i 215 blocchi **restano dove sono**, in `_generated`, finché quel file è
   scritto a mano — non si perde niente oggi;
2. sono già estratti in `allegati/codici-errore-classe-note.csv`, colonna
   `note`, pronti per il seed del D-5;
3. il B-5 ha ora un **secondo prerequisito** scritto, e l'intestazione del file
   generato lo ripete: *rigenerare senza aver seminato le note è una
   cancellazione silenziosa*.

✅ **CHIUSO la sera stessa.** Il DB ha importato le 215 note al D-2-bis: 213
dirette, 2 rimappate sui gemelli senza prefisso (`E_MESSAGGIO_NON_DEFINITO` ed
`E_W_TXID_NOT_REGISTERED` puntavano a nomi che a catalogo non esistono), **zero
perse, zero collisioni**. Il prerequisito 2 del B-5 è soddisfatto: quando il
generatore partirà, le riemetterà dal catalogo.

⚠️ **Un difetto del nostro estrattore, segnalato dal DB e corretto.** Prendeva il
blocco di commento immediatamente sopra la policy — ma per il **primo codice di
ogni sezione** quel blocco è il **titolo del gruppo**, non la motivazione del
codice: 23 note avevano il titolo davanti, 22 erano *solo* il titolo. La regola
che mancava, ora nell'estrattore: *un blocco che è solo `── … ──` appartiene alla
sezione, non alla voce.* Rigenerando i moduli con la regola giusta, **39 blocchi
si sono rivelati puri titoli** («── Pratiche ──», «── 400 · campo da correggere
──») e sono spariti: erano raggruppamenti per status, e lo status ora è la classe.

### 6.3 Il default di `DATO_ERRATO`: scelto il **banner**, e la ragione è asimmetrica

117 contro 117 non è una maggioranza da rispettare: è una scelta da fare. È stato
scelto `show_error_banner`, e non per il pareggio — per l'asimmetria del danno:
**promettere un campo da evidenziare che non esiste è peggio del contrario.** Un
banner su un errore che aveva un campo da evidenziare è un'occasione persa; un
`highlight_form_fields` su un errore che non ha un campo nel form è
un'indicazione falsa.

⚠️ **E vale anche per i codici che ancora non esistono**: il default è quello
che prenderà ogni codice nuovo classificato `DATO_ERRATO` dal generatore, senza
che nessuno lo rilegga.

---

## 7. Due cose verificate e **non** fatte, con la ragione

* **nessun test sul prefisso dei codici.** Sembrava il presidio ovvio — «ogni
  codice registrato comincia per `E_` o `W_`» — e sarebbe **rosso**: **51**
  codici registrati non hanno il prefisso (`PRATICHE_*`, `FLUSSI_*`, `PREV_*`,
  `CF_NON_VALIDO`…). Sono i codici ereditati fuori convenzione, e
  [api.md](../api.md) li registra così **di proposito** dal 2026-08-05. Il
  presidio giusto ce l'hanno già, lato DB: il controllo (B) del guardrail, che
  rifiuta i **nuovi**;
* **i due ripieghi di `resolve()` non sono stati toccati**, come chiede il B-2:
  sono ciò che tiene in piedi i codici nuovi che il DB sta seminando mentre il
  generatore non c'è. Il momento di ridiscuterli è **dopo** il B-5.

---

## 8. ⭐ Il riallineamento al catalogo (2026-08-07 sera) — **e un'eccezione che sparisce**

Il DB ha consegnato `codici_errore.csv` (**689 righe**, D-1 + D-2 chiusi). Da
quel momento **fa fede il catalogo**, e il BE si è allineato: sei classi
divergevano.

### 8.1 ⭐ Il vocabolario va a **dieci**, e il BE ci guadagna una semplificazione

Il brief dichiarava 401 e 502 *«fuori dal vocabolario di dominio, da mappare a
mano nel backend»*, e il B-4 aveva fatto esattamente questo: una mappa
`HTTP_PER_CODICE` di cinque righe, l'unica eccezione del disegno.

**Era falso, e il DB l'ha mostrato dal lato giusto:** quei cinque sono righe del
catalogo come tutte le altre, quindi con `classe NOT NULL` una classe la
vogliono. Tid ha confermato `NON_AUTENTICATO` (401, 4 codici) ed `ERRORE_ESTERNO`
(502, 1).

⭐ **Conseguenza sul BE, ed è più di un allineamento: `HTTP_PER_CODICE` è stata
cancellata.** Con le due classi a vocabolario non c'è più nessuna mappa per
codice — si deriva *tutto* dalla classe. L'eccezione non è stata spostata: non
esiste più. E il prossimo codice di autenticazione prenderà il suo 401 senza che
nessuno lo scriva.

⚠️ **Su `NON_AUTENTICATO` il default è di nuovo un pareggio** — due
`redirect_login` contro due banner — e lì l'asimmetria del §6.3 morde più forte:
un `redirect_login` sbagliato **butta l'operatore fuori dall'applicazione**.
Default = banner, i due `redirect_login` sono override espliciti.

### 8.2 ⭐ Il primo `AVVISO` vero: `W_TXID_NOT_REGISTERED` **ora solleva**

A catalogo è `AVVISO`. Nel BE era registrato a **500** — perché nessuno l'aveva
mai classificato, non perché qualcuno l'avesse deciso.

È il **collaudo della garanzia del B-2**, sul codice per cui era stata scritta:
`resolve()` ora solleva `ClasseErroreSenzaStatus` invece di restituire un guasto
tecnico col messaggio soppresso. Nessun punto del backend lo nomina (verificato),
il DB lo scrive nel diario con `fn_log_error_only` e non lo solleva mai, e il
controllo (E) del guardrail SQL impedisce a chiunque di sollevarlo: **se quella
eccezione scatta, è un errore di programma e si comporta come tale.**

⚠️ Vale anche per il gemello `E_W_TXID_NOT_REGISTERED`, che a catalogo non
esiste: la classe la prende dal fratello, perché è lo stesso codice sotto un
altro nome.

**Cosa succede davvero se scatta — verificato, non dedotto.** L'eccezione
propaga fuori da `exception_to_error_response`, che la chiama *prima* di
loggare: il client riceve un **500 non-JSON** e il traceback finisce in
`django.request` nominando il codice e la ragione. Il frontend degrada pulito
(messaggio di ripiego del chiamante + toast di sistema, essendo ≥ 500).
⛔ **Da non "aggiustare" con un `except` che produca un envelope pulito**:
sarebbe il ripiego silenzioso appena tolto, sotto un altro nome.

### 8.3 ⭐ I due ponti verso il B-6, che non aspettano il D-9

Il controllo di divergenza vero (B-6) leggerà `vw_codici_errore_identita` e vuole
il database. Ma **i CSV di seed stanno nel repo**, e presidiano lo stesso fatto
senza DB, su due assi:

* `test_nessuna_classe_diverge_dal_catalogo` — le 658 classi del BE contro le 689
  del catalogo;
* `test_il_vocabolario_non_diverge_dal_catalogo` — le 10 classi di `CLASSI_ERRORE`
  contro `classi_errore.csv`, **nei due versi**.

⭐ **Il secondo è quello che mancava, e la differenza si vede sul calendario.**
Senza, una classe nuova a catalogo il BE la scopre il giorno in cui **un codice
la usa** — cioè quando `resolve()` non sa più che status dare e solleva. Con,
la scopre il giorno del seed, quando l'unica cosa da fare è aggiungere due righe.
Nel verso opposto: una classe che il BE conosce e il catalogo no è una regola che
non governa più niente, e resta lì a sembrare viva.

⚠️ **Fallisce solo su una classe diversa, mai su un codice in più o in meno**, e
la ragione va scritta perché è la differenza fra un presidio che sopravvive e uno
che viene spento: i due insiemi **non devono** coincidere. Il catalogo ha 33
codici che il BE non conosce (30 ritirati + 3 progettati mai cablati), il BE ne
ha 2 che il catalogo non ha (i gemelli col prefisso, la cintura della campagna di
rinomina). Un test che pretendesse l'uguaglianza sarebbe rosso il giorno dopo.

### 8.4 🔴 **`ui_action` non la legge nessuno** — misurato su tutto il repo

Cercata dopo aver scritto due volte che «il discriminante è dove manca il dato»:
né `ui_action` né `uiAction` né **uno solo dei sette valori** compare in
`frontend/src`, o altrove fuori da backend/docs/db. Il frontend legge
`error.message` (`useApiHandler.extractErrorMessage`) e lo **status**: ≥ 500 →
toast di sistema, 401 → refresh token, 401/403 → il polling si ferma.

⚠️ **E [api.md](../api.md) diceva l'opposto**, in una frase usata per decidere:
*«in questa app la maggior parte del comportamento la decide `ui_action`, non lo
status»*. Corretta.

**Cosa cambia, detto senza sconti:**

* le **176** decisioni di override oggi **non cambiano niente a video**. Non sono
  sprecate — sono un contratto **emesso e non ancora consumato**, e tenerlo costa
  zero — ma il pareggio 117-117 su `DATO_ERRATO` decide cosa troverà il frontend
  *il giorno in cui lo implementerà*, non cosa vede l'operatore adesso;
* **lo status non è la parte che conta meno**: al momento è l'unica che il client
  guarda davvero;
* il giorno in cui il frontend leggerà `ui_action`, quelle 176 righe vanno
  riguardate **prima** di accenderlo.

⚠️ **E c'era un difetto conseguente, corretto.** Dei due percorsi che costruiscono
l'envelope, `exception_to_error_response` spediva `ui_action` e
`drf_exception_handler` la **calcolava e la buttava via**: lo stesso codice usciva
con due forme diverse a seconda di chi l'aveva sollevato. Nessuno se n'era accorto
proprio perché il campo non lo legge nessuno — ed è la ragione per cui il fix ha
un test suo: *un contratto che nessuno consuma è precisamente quello che si sfila
senza che un rosso lo dica*.

*(Nello stesso punto c'era un ramo morto: `if policy is not None` dopo
`resolve()`, che non ha mai restituito `None`. Tolto.)*

### 8.5 ⚠️ Due cose da guardare al B-5

* **i due gemelli col prefisso `E_`** non hanno riga di catalogo: il generatore
  non li produrrà e cadranno sul ripiego. Vanno tenuti a mano (una riga) o
  lasciati cadere **consapevolmente** — non scoperti spariti;
* **`E_PARAMETRO_INVALIDO` ha `highlight_form_fields`**, e la misura nuova del DB
  dice che **160 dei suoi 177 punti sono guard di parametro**, cioè valori che
  arrivano dal *chiamante* e non da un form dell'operatore. È esattamente
  l'asimmetria del §6.3 al contrario: quella `ui_action` promette un campo da
  evidenziare che nel 90% dei casi non esiste. ⚠️ **Non l'ho cambiata**: è una
  decisione del cantiere precedente su un codice nominato da 177 punti, e la
  chiamata è di Tid.

---

## 9. ⭐ B-5 e B-6 — il generatore, e la prima generazione vera (2026-08-07 sera)

Il DB ha consegnato il **D-9**: `config.vw_codici_errore_identita` esiste, è
popolata (689 righe, 79 ritirate, 203 note) e ordinata.

### 9.1 Il generatore

[`manage.py genera_error_policies`](../../../../backend/apps/core/management/commands/genera_error_policies.py)
— management command e non script sciolto, per due ragioni: prende settings e
connessione da Django senza reinventarle, ed è **importabile**, quindi il
controllo di divergenza (B-6) può eseguire *la stessa funzione di rendering*
invece di riscriverla. Un presidio che confronta con una seconda
implementazione presidia le due implementazioni, non il fatto.

```bash
./manage-env.sh genera_error_policies           # riscrive il modulo
./manage-env.sh genera_error_policies --check   # non scrive; esce 1 se diverge
```

⚠️ **La sorgente è la vista di identità e va detto perché**, perché l'errore è
attraente: `config.vw_codici_errore` ha una riga per *(codice, lingua)* ed è un
`LEFT JOIN`, quindi un codice senza messaggio ci compare con `lingua IS NULL`.
Filtrarla per lingua non darebbe un errore: **toglierebbe righe in silenzio**.

### 9.2 🔴 Il difetto trovato eseguendolo — un generatore può murarsi fuori

Alla prima esecuzione il renderer ha prodotto `frozenset("A", "B", …)` invece di
`frozenset({…})`: 79 argomenti a una funzione che ne accetta uno.

Il file non si importava più — e siccome è `apps.core.services` a importarlo,
**Django non partiva, quindi non partiva nemmeno il generatore.** Per rientrare
serviva ripristinare il file a mano. È una classe di guasto che vale la pena
avere in testa: *uno strumento che scrive un file necessario alla propria
esecuzione può chiudersi fuori dalla stanza*.

**Rimedio, ed è più forte di un `compile()`:** `verifica_prodotto` **esegue** il
testo reso in uno spazio dei nomi isolato e controlla che i due dizionari ci
siano coi conti giusti, **prima** di scrivere. Un `compile()` non sarebbe
bastato: quello era un errore di *runtime*, non di sintassi.

### 9.3 Cosa è cambiato con la prima generazione vera

| | a mano | generato |
|---|---:|---:|
| voci | 658 | **689** |
| di cui ritirate | — | **79** |
| **classi cambiate** | | **0** |

⭐ **Zero classi cambiate**: l'allineamento al catalogo dell'§8 era già completo,
e la generazione lo ha confermato invece di scoprirlo.

Le differenze sono tutte di **perimetro**, e ognuna era prevista:

* **+33 dal catalogo** — 30 ritirati e i 3 «progettati mai cablati» del push
  preventivo, che ora hanno anche il loro messaggio di ripiego (scritto adesso,
  perché il giorno in cui qualcuno li caglierà non sia anche il giorno in cui si
  scopre che non hanno una frase);
* **−2**: `E_MESSAGGIO_NON_DEFINITO` ed `E_W_TXID_NOT_REGISTERED`, i gemelli col
  prefisso `E_` di codici che a catalogo stanno senza. Erano irraggiungibili — il
  codice arriva dal campo strutturato col nome esatto del catalogo, e il ripiego
  a regex cerca `\bE_[A-Z]…`, quindi il nome senza prefisso da lì non passa
  comunque e quello con prefisso non lo scrive nessuno.

⛔ **E `W_TXID_NOT_REGISTERED` resta `W_`.** La `W` non è un prefisso sbagliato da
uniformare: è un'**altra famiglia** — si scrive nel diario, non si solleva — e la
regola di naming è `^[EW]_` proprio per questo. Il divieto è ora scritto in due
punti del codice, perché è la «correzione» che qualcuno tenterà.

### 9.4 ⚠️ `has()` ha cambiato significato, e l'ha detto un test diventando rosso

`test_conferma_non_e_un_errore_http` chiedeva `has("E_AI_CONFIRMATION_REQUIRED")
is False` — «non è registrato». Andava bene finché il registro era scritto a
mano: bastava non scriverci il codice.

Ora il registro è **generato dal catalogo**, e il catalogo contiene *tutti* i
codici, ritirati compresi. Quindi:

> **`has()` oggi risponde «lo conosco», non «è buono».**

La domanda «questo codice si può usare?» si fa su **`CODICI_RITIRATI`** — ed è la
stessa intenzione detta più forte: non «l'abbiamo dimenticato», ma «l'abbiamo
deciso», con la decisione in un dato invece che in un'assenza.

⭐ **Da lì è nato un verso nuovo del guardrail dei punti di chiamata**: *nessun
punto di chiamata deve nominare un codice ritirato*. ⚠️ **Non è il B-7 né una
sua metà** — l'avevo scritto e non regge: il B-7 vieta i codici **generici**,
questo presidia i codici **ritirati**, che è un'altra proprietà (§11). È diventato calcolabile solo adesso — prima del B-5 il backend
non sapeva quali codici fossero ritirati, perché `obsoleto_dal` viveva solo lato
DB. **Misurato alla nascita: 0 su 213 codici usati.** Nasce in pari.

### 9.5 I presidi, e cosa misura ciascuno

| Presidio | Confronta | DB? |
|---|---|---|
| `test_error_policies_divergenza_db` (**B-6**) | il **testo** del modulo ↔ la vista, adesso | sì (opt-in CI) |
| `test_error_codes_db_policy_guardrail` | i codici che le **funzioni vive** sollevano ↔ il registro | sì (opt-in CI) |
| `test_nessuna_classe_diverge_dal_catalogo` | le classi ↔ il **CSV di seed** | no |
| `test_il_vocabolario_non_diverge_dal_catalogo` | le 10 classi ↔ `classi_errore.csv` | no |
| `test_error_codes_declared_guardrail` | i **punti di chiamata** ↔ registro **e ritirati** | no |

⚠️ **Il B-6 non sostituisce il cancello del terzo lato**, e il piano diceva
«cambia mestiere»: sono **due mestieri**. Il B-6 confronta il registro col
*catalogo*; il terzo lato confronta le *funzioni vive* col registro. Un codice
sollevato da una funzione e mai messo a catalogo passerebbe il primo e verrebbe
preso dal secondo.

✅ **Il rosso è stato provato, non supposto**: cambiando a mano una classe nel
modulo, il test fallisce con il diff esatto e `--check` esce 1.

### 9.6 ⭐ Il collaudo non l'ho scritto io: è arrivato da solo, due ore dopo

A generazione fatta e suite verde, i due presidi sono diventati **rossi insieme**.
Non per una mia modifica: il team DB aveva eseguito la rinomina
`MESSAGGIO_NON_DEFINITO` → `E_MESSAGGIO_NON_DEFINITO` — l'ultima riga del registro
dei codici fuori convenzione, che con quella va a **zero** e si droppa.

I due l'hanno vista **da due lati diversi, e nessuno dei due da solo bastava**:

| Presidio | Cosa ha detto |
|---|---|
| **B-6** divergenza | il diff esatto: una riga in meno col nome vecchio, una in più col nuovo |
| **terzo lato** | `script.fn_log_error_only` nomina `E_MESSAGGIO_NON_DEFINITO`, che non ha una policy |

**Il rimedio è stato una riga di comando** — `genera_error_policies` — più **una
riga a mano**: il messaggio di ripiego, che vive nel modulo `fallback` e che il
generatore non tocca.

> È la prova che valeva più del test che l'aveva anticipata: prima del B-5 quella
> rinomina sarebbe passata **silenziosa**, e `fn_log_error_only` — il *ripiego del
> ripiego*, quello che parla quando manca un messaggio a catalogo — avrebbe
> cominciato a nominare un codice che il backend non conosceva. Si sarebbe visto
> il giorno in cui fosse mancato un messaggio: **il peggiore per scoprire un
> guasto**, ed è esattamente il rischio che il brief §7.2 aveva scritto.

---

## 10. ⭐ La classe è **vera**? Prima misura — 2026-08-08

Il brief chiude il §9.2 con una rinuncia: *«il disegno presidia la nascita di un
codice, non la sua vita — nessuno presidia che la classe resti vera»*. Con la
vista `dbops.vw_codici_errore_forme_condizione` (DB **D-10**) quella rinuncia si
può finalmente misurare, perché esistono **due letture indipendenti** dello
stesso codice:

* la **classe** — cosa dovrebbe essere (catalogo);
* la **famiglia della guardia** — cosa fa il punto che solleva.

Incrociate, la matrice `famiglia × classe` sui codici vivi e classificabili:

| famiglia | classe dominante | fuori dominante |
|---|---|---|
| `ECCEZIONE` | `TECNICO` 15 | 1 |
| `NOT_FOUND` | `NON_TROVATO` 19 | 20 (10 `DATO_ERRATO`, 6 `TECNICO`, 4 `CONFLITTO_STATO`) |
| `PARAMETRO` | `DATO_ERRATO` 14 | 3 |
| `ENUM` | `CONFLITTO_STATO` 6 | 4 |

**Il predicato più stretto — guardia di solo parametro e classe diversa da
`DATO_ERRATO` — dà zero.** Allargando alle famiglie miste escono **4 codici**, e
letti uno per uno **nessuno è un difetto**:

| Codice | Perché è flaggato | Verdetto |
|---|---|---|
| `E_GENERICO` | 68 punti, 4 famiglie | **per costruzione**: è il pavimento del percorso d'errore, `TECNICO` è giusto. Una misura del genere lo flagga sempre |
| `E_ARTICOLO_NOT_FOUND` | guardia `PARAMETRO`, classe `NON_TROVATO` | **decisione deliberata**, e sta scritta nella funzione: *«Guard parametro NULL: riconducibile a NOT FOUND»*. È lo stesso ragionamento che il DB ha applicato a `E_BOM_RIGA_NOT_FOUND` |
| `E_DEFINIZIONE_NON_TROVATA` | idem | idem |
| `E_ERRORE_PARAMETRI` | `ECCEZIONE`+`PARAMETRO`+`IGNOTO`, 7 funzioni in 2 schemi | 🔴 **difetto vero, letto punto per punto — §10.1** |

⚠️ **Il denominatore va detto ogni volta che si cita il risultato**: 75 codici
classificabili su 344, gli altri 269 sono `solo_ignoto` — la vista *dice* di non
sapere, ed è la colonna che rende la misura onesta. **«Zero contraddizioni» vale
sul quinto del perimetro che si riesce a leggere**, non su tutto.

> ⭐ Ma nei limiti in cui è misurabile, la risposta alla domanda del §9.2 oggi è
> **sì: la classe è vera**. Ed è la prima volta che quella domanda ha una
> risposta che non sia «bisognerebbe rileggere 150 funzioni».

### 10.1 🔴 `E_ERRORE_PARAMETRI` — **4 punti su 13 dicono il falso**

L'incrocio l'aveva segnalato; leggendo i 13 punti che lo sollevano, uno per uno,
il sospetto diventa una misura. **Non è il nome della funzione: è la condizione.**

| Condizione al punto che solleva | Punti | Classe vera |
|---|---:|---|
| `p_<x> IS NULL` / `<= 0` / `btrim = ''` / `NOT IN (…)` — guardia di parametro | **9** | `DATO_ERRATO` ✅ |
| `TG_NARGS < 1` e `TG_NARGS <> 2` — **il trigger è montato con gli argomenti sbagliati** | 2 | `TECNICO` |
| `EXCEPTION WHEN OTHERS` in `trgfn_guard_utility_tipo_ruolo_by_cols` | 1 | `TECNICO` |
| `v_stato_chiuso_id IS NULL` in `fn_subentro_cliente` — ma **non è un parametro**: esce da `SELECT … FROM config.stati_cliente WHERE codice_interno = …`, cioè da una **configurazione mancante** | 1 | `TECNICO` |

⚠️ **E i tre precedenti sono già decisi in questo progetto**, il che rende il
verdetto meccanico invece che opinabile:

* *argomenti del trigger sbagliati* → `E_ATTIVO_REQUIRE` è **500** proprio per
  questo («un montaggio sbagliato»);
* *`EXCEPTION WHEN OTHERS`* → è la ragione per cui `E_SNAPSHOT_ID_NOT_FOUND` è
  stato spostato a **500** nel cantiere del terzo lato;
* *lookup di configurazione che non trova* → `E_REGOLA_FATTURAZIONE_MANCANTE` e
  `E_PIPELINE_NOT_FOUND`, entrambi **500** col criterio «chi può rimediare».

**Quindi non è un caso da riclassificare, è da spezzare**, e per il criterio già
scritto in [api.md](../api.md): i significati chiedono **reazioni diverse** —
*«correggi quel campo»* contro *«chiama chi ha configurato il sistema»*. Oggi su
quei 4 punti l'operatore riceve un **400** che gli dice che ha sbagliato lui, e
lo manda a cercare un campo che non esiste.

⚠️ **Perimetro DB**: sono codici nuovi + quattro funzioni da toccare. Il BE non
ha niente da cambiare — la classe la prende dal catalogo, e i codici nuovi
arrivano col generatore.

> ⭐ **La cosa che vale oltre questo codice**: `E_VALIDAZIONE` sembrava un
> accumulatore e non lo era; `E_ERRORE_PARAMETRI` non era nella lista dei
> sospetti e lo è. Entrambe le volte la risposta è venuta dal **contare le
> condizioni**, non dal guardare i nomi — e la seconda volta l'ha trovata una
> misura invece di una persona.

---

## 11. ⚠️ Il B-7, e una mia etichetta sbagliata (2026-08-08)

Avevo scritto che il B-7 era «per metà fatto», e che la metà chiusa era il verso
nuovo del guardrail — *nessun punto di chiamata usa un codice ritirato*, misurato
**0 su 213**.

**Il numero è vero, l'etichetta no.** Il B-7 vieta i codici **generici**; quel
presidio riguarda i codici **ritirati**. Sono due proprietà diverse, e vietare
l'uso dei ritirati non chiude il rubinetto dei generici: un codice appena nato
può essere genericissimo e non è ritirato.

**Quindi il B-7 è aperto per intero**, e il presidio sui ritirati è un presidio
in più — buono, ma suo.

### 11.1 E il B-7 lato BE è quasi vuoto — vale la pena dirlo

La regola è *«un codice nuovo non deve coprire più condizioni»*. Il fatto che la
decide è la **forma della guardia al punto che solleva**, e quei punti stanno in
PL/pgSQL: il backend non li vede e non li crea. Il rubinetto si chiude **dove il
codice nasce**, cioè al catalogo.

Il contributo del BE al B-7 c'è, ma è **il criterio, non un cancello**: *si
contano le condizioni, non i domini* — ora scritto in
[api.md §Tassonomia](../api.md), dove lo legge chi sta per aggiungere un codice.
Il cancello vero è la misura del DB (D-10), che quel criterio lo calcola.

⚠️ **Quello che il BE può ancora fare, se si decide che serve**, è un verso in
più sul guardrail dei punti di chiamata: *un codice nominato da più di N punti
Python diversi è un candidato*. Ma sarebbe la misura debole — quella per
**domini**, appena smentita — applicata al backend invece che al DB. **Meglio
niente che una misura che sbaglia sul suo caso più noto.**

---

## 12. 🔵 `ui_action` — analisi per la decisione (2026-08-08)

> **Stato: 🟡 il passo 1 è FATTO** (§12.7), il resto è analisi. Serve a decidere se
> `ui_action` si implementa o resta un contratto dormiente, e — se si fa — a non
> cominciare dalla parte sbagliata. **Contiene anche la parte DB**, perché il
> disegno non si può decidere per metà.

### 12.1 Il fatto, in tre righe

Il backend, con ogni errore, manda un suggerimento su come la pagina dovrebbe
reagire: banner, campo evidenziato, stato vuoto, toast, ritorno al login.
**Il frontend non lo legge** (§8.4): mostra il messaggio in un toast, sempre
uguale per tutti i 689 codici. Le uniche differenze le fa lo **status** — ≥ 500
toast più lungo, 401 rifare il login, 401/403 il polling si ferma.

### 12.2 ⭐ Il buco vero non è il frontend: è che **non si dice quale campo**

Il valore che porterebbe il guadagno è `highlight_form_fields` — *«evidenzia il
campo sbagliato»* — e sono **125 codici**. Ma nell'envelope **non c'è il nome del
campo**: ci sono `code`, `message`, `detail`, `hint`, `ui_action`, e basta.

Quindi anche se il frontend leggesse `ui_action` **oggi non saprebbe cosa
evidenziare**. Implementare `ui_action` senza chiudere questo buco non produce
niente.

⚠️ **E non è un buco solo: sono due, di dimensione molto diversa.**

| Dove nasce l'errore | Codici `highlight_form_fields` | Il nome del campo… |
|---|---:|---|
| **codice Python** | **42** | ⭐ **c'è già** — e viene buttato via |
| **funzione PL/pgSQL** | **83** | manca davvero |

### 12.3 Lato backend: il dato **esiste già** e si perde nell'ultimo passo

`ServiceError` porta un `context`, e **497 punti di chiamata lo valorizzano già**
con `{campo: valore}` — i validator centralizzati lo fanno per costruzione
(`guard_positive_int`, `guard_non_empty_string`, …). Il dato viaggia fino
all'eccezione.

Poi `ErrorTranslator.to_api_error` costruisce l'`ApiError` **senza `context`**:
la dataclass quel campo non ce l'ha. Si perde a un passo dall'uscita.

⚠️ **Una cautela, ed è l'unica cosa non meccanica di questo pezzo:** nel
`context` ci sono anche i **valori** (`{"partita_iva": "12345678901"}`), che sono
dati del cliente. Nell'envelope vanno le **chiavi**, non i valori — il valore
l'operatore ce l'ha già davanti, è quello che ha scritto lui.

### 12.4 Lato DB: il trasporto **esiste già nel protocollo**, e non lo usa nessuno

`script.fn_log_and_raise_error` riceve **anche lei** un contesto `jsonb` (es.
`jsonb_build_object('codice id_cliente', v_codice_chiuso)`) — ma quel contesto
finisce in `dbops.error_log`, **non nell'eccezione**. Cioè: entrambi i lati
raccolgono già il campo, nessuno dei due lo trasmette.

⭐ **E non serve inventare un canale nuovo.** `RAISE` di PostgreSQL ha già le
opzioni strutturate `COLUMN`, `TABLE`, `SCHEMA`, `DATATYPE`, `CONSTRAINT`, e
psycopg le espone tutte (`diag.column_name`, `diag.table_name`, …). **Verificato
su psycopg 3.3.4.**

È esattamente il meccanismo che questo progetto **usa già**: dal 2026-08-05 il
codice errore viaggia in `CONSTRAINT` e lo legge `db_error_fields.py`. Il nome
del campo viaggerebbe in `COLUMN`, letto dallo **stesso modulo**, che resta il
punto unico di lettura.

```sql
-- lato DB: una opzione in piu' sul RAISE, nessun parametro nuovo da inventare
RAISE EXCEPTION '%', v_messaggio
  USING ERRCODE = 'P0001', CONSTRAINT = p_error_code, COLUMN = 'partita_iva';
```

⚠️ **Il contratto va scritto prima di usarlo**, come si è fatto per `CONSTRAINT`:
*«`P0001` + `COLUMN` valorizzato = il campo che l'operatore deve correggere»*, e
un guardrail che verifichi che nessun altro `RAISE` scriva `COLUMN` per altro.
Un secondo mittente sullo stesso canale non farebbe fallire niente: farebbe
**evidenziare il campo sbagliato**, che è peggio di non evidenziarne nessuno.

### 12.5 🔴 L'ordine — e **no, il DB non viene prima**

La domanda naturale è «prima si aggiornano loro?». **No, e farlo sarebbe
l'errore.** Toccare 83 punti PL/pgSQL *prima* di sapere se a video il guadagno si
sente è esattamente il modo di lavorare che questo cantiere ha evitato tre volte:
si misura, poi si costruisce.

| # | Passo | Chi | Perché lì |
|---|---|---|---|
| ✅ **1** | ~~il `context` entra nell'envelope~~ **FATTO** 2026-08-08 — §12.7 | **BE** | il dato c'era già, non dipendeva da nessuno |
| ✅ **2** | ~~il frontend legge `ui_action` + i campi~~ → **legge i CAMPI**, esteso a 38 componenti | **FE** | ⚠️ la `ui_action` è rimasta fuori, e non per pigrizia: §12.12 |
| **3** | ⏸️ decisione: si estende o ci si ferma | **Tid** | dopo il 2, con una cosa vista invece che immaginata |
| **4** | `USING COLUMN` sui punti che servono | **DB** | 83 punti: si fanno **se** il 3 dice di sì, e solo quelli dei domini toccati |

⚠️ **Una cosa sola va decisa insieme e SUBITO, prima del passo 1**: la **forma
del campo nell'envelope**. Se il BE sceglie una chiave e il DB un domani ne
manda un'altra, il frontend deve leggere due formati — ed è il difetto di questo
intero filone, in miniatura. La proposta: **una sola chiave**, valorizzata dai
due lati con la stessa semantica.

> Quindi il DB non è «prima»: è **secondo**, con **una decisione condivisa in
> testa**. Ed è utile che sappiano da adesso che il loro pezzo, se si farà, è
> `USING COLUMN` e non un parametro nuovo di `fn_log_and_raise_error`.

### 12.6 Se invece resta dormiente

Tenerlo costa **zero** — è già scritto e viaggia. Ma una regola va detta,
perché è la parte che costa se la si dimentica:

⛔ **Non spendere tempo a scegliere la `ui_action` dei codici nuovi.** Il default
della classe va bene. Finché il frontend non la legge, ragionarci sopra è lavoro
che non produce niente — ed è già successo: i **117 contro 117** su
`DATO_ERRATO` sono stati discussi a lungo, misurati due volte e scritti in tre
documenti, per un campo che nessuno guarda.

⚠️ E il giorno in cui si accende, quelle **176 righe di override vanno rilette
prima**, non dopo: sono decisioni prese quando nessuno poteva verificarle a
video.

### 12.7 ✅ Passo 1 fatto — 2026-08-08

L'envelope d'errore porta `fields`: i **nomi** dei campi da correggere.

```json
{"code": "E_CORE_VALIDATION", "message": "Campo 'denominazione' obbligatorio.",
 "ui_action": "highlight_form_fields", "fields": ["denominazione"]}
```

⭐ **Non è stato scritto niente di nuovo, è stato smesso di buttarlo via.** La
riga sopra esce da una chiamata reale a `PayloadValidator.require_string` — non
da un test costruito ad arte: quel nome il backend lo aveva già in mano, e si
fermava un passo prima dell'uscita.

**Le tre decisioni dentro le venti righe di codice**, che sono la parte che
conta:

1. **si legge solo `context["field"]`**, non tutte le chiavi. È la decisione che
   separa il dato dal rumore: nel `context` ci sono anche `lotto_id`,
   `contratto_id`, `order_dir`, che **non sono campi di un form**. Mandarli
   direbbe al frontend di evidenziare cose che sullo schermo non esistono —
   *un dato falso al posto di un dato mancante, che è un peggioramento*;
2. **esce il nome, mai il valore**: nel context c'è anche quello che l'operatore
   ha scritto, e non ha nessun motivo di tornare indietro. C'è un test che prova
   che il valore non compare **da nessuna parte** nel JSON;
3. **il nome deve sembrare un identificatore** (regex, max 64): i nomi li scrive
   il service, ma un chiamante che passasse una chiave dinamica farebbe
   rimbalzare al client testo altrui.

⚠️ **Il punto dove si perdeva, e dove si riperderebbe:** `_apply_policy`
costruisce un `ApiError` **nuovo**, e quello che non si nomina lì sparisce. Ha un
test suo per questo, non per il caso dritto.

**6 test** in `tests/services/test_error_translator_campi.py`, suite completa
verde. Restano fuori gli **83 codici sollevati dal database**: lì il canale
esiste (`USING COLUMN`) e non è ancora usato — passo 4, e solo se il pilota del
passo 2 dice che ne vale la pena.

### 12.8 ✅ Passo 2 fatto — il pilota, 2026-08-08

`useApiHandler` espone **`campiErrati`** (da `error.fields`) e **`azioneUi`** (da
`ui_action`). Pilota: [`CategoriaClienteDrawer`](../../../../frontend/src/amministrazione/components/CategoriaClienteDrawer.vue),
i cui cinque campi legano `:invalid="campiErrati.includes('…')"`.

⭐ **Il frontend aveva già la forma giusta, e questo ha deciso il disegno.** I
form del progetto ricevono da sempre `errors: Array` di nomi campo e fanno
`:invalid="errors.includes('nominativo')"` (`ContattoForm`, `ContoBancarioForm`,
…). Il backend adesso manda **esattamente quella forma**: non è stata inventata
nessuna convenzione nuova né lato server né lato client — le due metà si sono
incontrate a metà strada perché la stessa idea era già scritta da entrambi i
lati, e nessuna delle due la trasmetteva.

**Dove sta il valore, detto senza gonfiarlo:** `canSave` copre le regole che il
frontend conosce (obbligatorietà, formato); `campiErrati` copre **quelle che
stanno nel service** — unicità, coerenza fra entità, vincoli di stato. Prima
l'operatore leggeva «Campo 'ordinamento' non valido» in un toast e doveva
cercarselo nel form.

**Le regole scritte negli standard FE**, perché sono decisioni e non dettagli:

* si azzera a ogni `execute` — descrive l'**ultimo** errore, non la storia del drawer;
* si popola anche in `silent` — evidenziare senza toast è legittimo;
* **nessun messaggio sotto il campo**: il testo è già nel toast. Il bordo rosso
  dice *dove*, il toast dice *cosa*; ripeterlo sarebbe rumore e una stringa i18n
  in più da mantenere;
* il nome è quello del **payload API**, non del `v-model`.

⚠️ **`azioneUi` è esposto ma non lo legge nessuno**, ed è voluto — la ragione
piena, misurata, è nel §12.12: legare l'evidenziazione alla `ui_action`
**romperebbe proprio il caso migliore**. Esporlo ora evita di rimettere le mani
nel composable il giorno in cui servirà.

**Cosa è verificato e cosa no**, per non far credere più di quanto è provato:

| | |
|---|---|
| ✅ il backend produce `fields` sul percorso reale (`PayloadValidator`) | provato |
| ✅ l'errore arriva davvero a `execute` — lo store non lo ingoia, l'interceptor 401 non lo trasforma | letto nel codice |
| ✅ `invalid` esiste su `InputText`, `InputNumber`, `ToggleSwitch` (PrimeVue 4) | verificato nei tipi |
| ✅ eslint + `vite build` | verdi |
| ⚠️ il rosso a video | **non provato**: nel progetto non c'è un test runner frontend. Serve un click di Tid |

### 12.9 ✅ Tutti i duplicati — il campo lo porta il vincolo (2026-08-08)

Su richiesta di Tid, il campo non si scrive più chiamata per chiamata: **lo
dichiara la mappa dei vincoli**. Ogni voce di `unique_constraints` /
`fk_constraints` / `check_constraints` può essere `(codice, messaggio)` oppure
`(codice, messaggio, campo)`.

⚠️ **Il campo sta sulla VOCE, non nel `context` condiviso**, ed è la ragione per
cui la modifica è nel building block e non nei service: una mappa può avere due
vincoli su campi diversi, e un `field` nel contesto comune si applicherebbe a
qualunque dei due facesse match. Il client accenderebbe l'input sbagliato —
**peggio che non accenderne nessuno, perché manda l'operatore a correggere un
campo giusto.** Ha un test suo, con due vincoli nella stessa mappa.

**Coperti: 12 vincoli.** Tutti quelli in cui il campo è **vero**, cioè una
chiave del payload che l'operatore compila: i `codice` (categorie clienti,
listini, offerte, promo, definizioni/colonne/preset lista, template documenti e
asset), i `codice_interno`, `codice_versione`.

⚠️ **E quelli che ho lasciato a due elementi, che è la parte che conta:**

| Caso | Perché niente campo |
|---|---|
| `uq_contratti_numero` | ⭐ il numero **lo assegna il service** (`_FORBIDDEN_TESTATA_CREATE`): non è un campo del form, accenderlo indicherebbe qualcosa che l'operatore non può toccare |
| `uq_fornitori_soggetto_ruolo_id`, `uq_emittenti_fiscali_ruolo` | `soggetto_ruolo_id` non è una chiave di payload: è derivato dal soggetto |
| `uq_offerte_commerciali_uid`, `uq_template_asset_emittente_sha256` | uid e hash sono **generati**, non scritti |
| coppie di FK (`offerta_id`+`articolo_id`, `utility_id`+`tipo_ruolo_id`, …) | il duplicato è la **combinazione**: sceglierne una sarebbe arbitrario |
| `uq_ordini_v_anno_serie_numero`, `uq_documenti_generati_*` | numerazione e progressivi di sistema |

⭐ **Il controllo che ha fatto la differenza:** i primi due casi li avevo dati
per buoni leggendo il nome del vincolo — la colonna esiste, il nome è
plausibile. Sono saltati fuori verificando che il nome fosse una **chiave del
payload** e non solo una **colonna del database**. È la stessa lezione del §11 e
del D-3, per la terza volta: *il nome non basta, si guarda il percorso reale.*

⚠️ **Una cosa trovata e non fatta: esistono due meccanismi paralleli.**
`create_with_constraint_mapping` (usato da fornitori e clienti) mappa
`vincolo → messaggio`, senza codice errore e senza campo. È lo stesso fatto
gestito in due posti, cioè il difetto che questo intero filone cura — ma
unificarlo è un refactor da dichiarare, non da fare di nascosto.

### 12.10 ✅ Il difetto segnalato al §12.9 — corretto, ed era peggio (2026-08-08)

Avevo scritto: *«esistono due meccanismi paralleli per lo stesso fatto»*, e
proposto di unificarli. Aprendoli, il difetto era più grosso di come l'avevo
descritto.

⚠️ **Le due copie non erano identiche.** `map_integrity_error` riconosce il
vincolo con una **word boundary**, e il commento accanto spiega perché: senza,
`uq_foo` matcha anche `uq_foo_bar` e a decidere quale voce vince è l'ordine del
dizionario. `create_with_constraint_mapping` faceva la stessa cosa con un `in`
nudo — **cioè aveva ancora il difetto che l'altra aveva già corretto**, e non
c'era niente che legasse le due: nessuno poteva accorgersi che una era rimasta
indietro.

⭐ **È lo stesso guasto del cantiere dei codici errore, in miniatura**: due
elenchi della stessa cosa, tenuti a mano, che si sfilano in silenzio. Con la
differenza che qui non si è sfilato un dato — si è sfilata una **correzione**.

**Cosa ho unificato e cosa no**, perché non sono la stessa domanda:

| | |
|---|---|
| ✅ **unificato**: il *riconoscimento* | `vincolo_violato` in `payload_helpers`, usata da entrambe. Chi traduce un `IntegrityError` non riscrive più il match |
| ⛔ **NON unificato**: la *politica di ripiego* | `map_integrity_error` maschera sempre con un `fallback_code`; `create_with_constraint_mapping` senza match e senza default **RILANCIA**. Non sono due copie della stessa decisione: sono due decisioni diverse, entrambe documentate. Fonderle avrebbe cambiato il comportamento di due domini per amore di simmetria |

E con l'unificazione il campo arriva anche di là: la mappa accetta `messaggio`
oppure `(messaggio, campo)`. Coperti `uq_fornitori_codice` → `codice` e
`uq_clienti_istanza_utility` → `istanza_utility_id`.

**5 test nuovi**, di cui uno è la rete sul difetto corretto: con due vincoli in
cui un nome è prefisso dell'altro, deve vincere quello giusto — col vecchio `in`
sarebbe rosso.

### 12.11 ✅ Il pattern esteso — da 1 drawer a 38 (2026-08-08)

Da pilota a comportamento dell'applicazione: **38 componenti, 136 binding**.

⭐ **Non è stato un «lega tutto»**, ed è la parte che rende il numero onesto.
Prima di toccare un file ho estratto **quali nomi il backend può davvero
mandare** — dai `context={"field": …}` e dalle chiavi passate ai validator:
**122 nomi**. Un input il cui campo non è in quella lista non è stato legato:
sarebbe una riga che non decide niente, e 350 righe così avrebbero fatto
sembrare coperto ciò che non lo è.

Per questo dei 70 candidati ne sono stati toccati **36 in automatico + 2 a
mano**: gli altri hanno campi su cui il backend non parla.

| | |
|---|---|
| candidati (usano `useApiHandler` e hanno input) | 70 |
| **legati** | **38** |
| non legati: nessun campo nella lista dei 122 | 49 |
| che solo *nominano* `useApiHandler` in un commento | 4 |

⚠️ **Due file li ha rotti lo script, e vale la pena scrivere come.** Il regex che
riconosce il tag si fermava al primo `>` — ma un `>` può stare **dentro un
attributo** (`:filter="catalogo.length > 5"`, `righeCount > 0`). Su
`ContrattoDrawer` e `ListaColonnaPermessoDrawer` l'attributo è finito in mezzo a
un'espressione. **Li ha presi il build, non io**: `vite build` e `eslint` sono
andati rossi con l'errore di parsing esatto. Ripristinati da git e rifatti a
mano.

> ⭐ La lezione non è «attento ai regex»: è che una modifica meccanica su decine
> di file **ha bisogno di un cancello che non sia la lettura**. Qui il cancello
> c'era già (build + lint) e ha fatto il suo mestiere in dieci secondi.

Dopo il ripristino: **eslint pulito, build verde**, e i diff riletti a campione
per verificare che l'attributo fosse sul tag giusto — cosa che il build non può
dire.

### 12.12 🔴 La `ui_action` NON entra, e il caso migliore lo dimostra

Il passo 2 di questo piano diceva *«il frontend legge `ui_action` + i campi»*.
**Legge solo i campi, ed è la scelta giusta.** Lo dice una misura, non una
preferenza.

| Codice | classe | `ui_action` | porta il campo? |
|---|---|---|---|
| **`E_ANAG_DUPLICATO`** | `CONFLITTO_STATO` | **`show_error_banner`** | ✅ sì, `codice` |
| `E_ANAG_VALIDAZIONE` | `DATO_ERRATO` | `highlight_form_fields` | ✅ sì |

⭐ **Il duplicato di categoria — il caso su cui il pattern è stato validato in
app — ha `ui_action = show_error_banner`.** Se l'evidenziazione fosse
condizionata a `ui_action === 'highlight_form_fields'`, quel caso **non
funzionerebbe**: proprio il migliore dei due, quello in cui il form è compilato
bene e la validazione client non ha niente da dire.

**La ragione di fondo, che vale oltre questo codice:**

> `fields` è un **fatto** — «so quale campo è».
> `ui_action` è un **suggerimento** — «ecco come reagire».
> Subordinare il fatto al suggerimento butta via il fatto.

E il suggerimento, su quel codice, è stato scelto quando il campo **non esisteva
nemmeno**: `show_error_banner` era la scelta giusta *allora*, perché non c'era
niente da evidenziare.

### 12.12.1 E leggerla oggi non aggiungerebbe niente

| valore | codici | cosa cambierebbe |
|---|---:|---|
| `highlight_form_fields` | 125 | **già coperto** da `fields`, e in modo più preciso |
| `show_toast_error` | 12 | è già quello che succede |
| `redirect_login` | 2 | già fatto dall'interceptor sul 401 |
| `show_error_banner` | 467 | banner al posto del toast: scelta di **design dell'interfaccia** |
| `show_empty_state` | 50 | serve il contesto della lista — `useApiHandler` da solo non può |
| `show_retry_dialog` | 2 | serve un componente che non esiste |

Le prime tre non aggiungono nulla; le altre tre sono decisioni di interfaccia,
non del catalogo degli errori.

⚠️ **Conseguenza sul §12.6**, che va aggiornato nella sostanza: la regola
«quando si accende `ui_action`, rileggere prima le 176 righe di override» non è
più un'ipotesi prudente. **La prima che ho guardato era già sbagliata** per
l'uso nuovo — non perché fosse una decisione cattiva, ma perché descriveva un
mondo in cui il campo non arrivava.

### 12.13 ✅ Il lato che RICEVE il `COLUMN` — pronto prima che serva (2026-08-08)

Mentre il DB valuta il passo 4, il backend è stato messo in condizione di non
avere lavoro da fare quando arriverà: `structured_db_error_field` legge
`diag.column_name` e lo mette in `fields`, esattamente come
`structured_db_error_code` legge `constraint_name` dal 2026-08-05.

⭐ **E una metà è già viva senza che nessuno faccia niente.** Su una violazione
**NOT NULL** (SQLSTATE `23502`) `column_name` lo valorizza **PostgreSQL da
solo**, ed è già la colonna mancante: quel caso funziona da oggi, senza una riga
di PL/pgSQL.

⚠️ **Perché qui NON c'è il guard sullo SQLSTATE** che protegge la lettura del
codice — l'asimmetria sorprende e va scritta: su un `23xxx` `constraint_name`
contiene il nome del **vincolo**, e prenderlo per un codice applicativo
produrrebbe un codice inesistente, quindi un 500 al posto di un 409 parlante.
`column_name` invece contiene sempre e solo un nome di **colonna**: non esiste
un secondo mittente da cui difendersi. Stesso meccanismo, rischio diverso.

**6 test** su un'eccezione costruita a mano, senza database — compresa la
trappola già pagata sul codice (*campo che nasce da un'espressione NULL: arriva
come stringa vuota, non come None*) e il percorso intero fino all'envelope.

> ⚠️ Resta un limite da dire adesso: il nome è quello della **colonna**. Dove il
> service rinomina rispetto al payload, il client non trova l'input e non
> evidenzia nulla — **inerte, non sbagliato**. Se capiterà spesso, la risposta
> non è indovinare lato FE: è che la funzione dichiari il nome del campo API.

### 12.14 ⚠️ `SoggettoDrawer` mancava — e il buco era nel mio metodo (2026-08-08)

Segnalato dal team DB collaudando: il drawer del soggetto non era cablato,
mentre la loro metà era pronta (`fn_validate_cf_piva_it` emette
`CONSTRAINT = E_CF_NON_VALIDO` + `COLUMN = codice_fiscale`, changeSet
`20260808-07`).

⭐ **La catena intera è stata provata contro il DB vero**, ed è la prima volta:

```
codice = E_CF_NON_VALIDO   campo = codice_fiscale
envelope: {"code": "E_CF_NON_VALIDO", "fields": ["codice_fiscale"],
           "ui_action": "highlight_form_fields"}
```

`fn_validate_cf_piva_it` → `fn_log_and_raise_error` (legge `p_context->>'campo'`,
emette `USING COLUMN`) → `diag.column_name` → `structured_db_error_field` →
envelope. **Nessun anello mancante.**

#### Perché il mio script non l'aveva preso — due ragioni, e la seconda conta

1. **la forma del binding**: in `SoggettoDrawer` il form è `soggetto.form.x`, non
   `form.x` — e i campi CF/P.IVA non stanno nemmeno lì: stanno in
   `core/components/SoggettoForm.vue`, un form **condiviso** che riceve il
   modello dal padre. Cablarlo ha richiesto una prop (`campiErrati`), come fa già
   `ContattoForm` con `errors`;
2. 🔴 **la whitelist era solo del Python.** L'avevo costruita dai
   `context={"field": …}` e dalle chiavi passate ai validator — cioè **una sola
   delle due sorgenti**. I nomi che le funzioni PL/pgSQL emettono (chiave
   `'campo'` nel contesto) non c'erano: `piva_gruppo_acquisto` era invisibile per
   costruzione.

> ⭐ **È lo stesso errore di misura del §11 e del D-3, in una forma nuova**: non
> ho guardato il nome sbagliato, ho guardato **un solo percorso su due**. Il
> numero «122 nomi» era vero e misurava metà del mondo.

**Rifatta l'unione**: 121 dal Python + 9 dal DB = **126 nomi**. Ripassati tutti i
drawer con la lista completa: **zero nuovi cablaggi** — nessuno degli altri
quattro nomi del DB (`data_inizio`, `data_fine`, `cod_int_tipo_contatto`,
`stato_doc_fiscale_id`) ha un input nel frontend. Il buco quindi era **uno solo**,
ma non lo si poteva sapere senza rifare la misura.

⚠️ **`piva_gruppo_acquisto` resta senza binding**: nel frontend non esiste un
input con quel nome. Il canale è pronto dal lato DB e non ha un consumatore —
si cabla il giorno in cui quel campo comparirà in un form.

**Componenti che legano `campiErrati`: 40.**
