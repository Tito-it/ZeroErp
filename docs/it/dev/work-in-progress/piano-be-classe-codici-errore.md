# Piano BE — classe dei codici errore

**Chi:** team BE (`dev/backend-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 18 decisioni, le misure, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-db-classe-codici-errore](piano-db-classe-codici-errore.md).
**Stato:** 🟢 **B-1 → B-6 FATTI** (2026-08-07). Il D-9 è arrivato in serata e il generatore è in servizio: `error_policies_generated.py` **non si scrive più a mano** (§9). 🟡 Resta il B-7, per metà (§9.4).

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
| **B-7** | La regola «niente nuovi codici generici» | B-6 | coda | 🟡 metà fatta (§9.4) |

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
> 🔴 **Conseguenza: `allegati/codici-errore-classe-note.csv` è servito e ora è un
> secondo elenco.** Il suo contenuto vive a catalogo, che fa fede. Va **tolto dal
> repo** — richiesta a Tid, non lo cancello da solo. Il seed vero è
> `db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv`.

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

⭐ **Da lì è nato il verso nuovo del guardrail dei punti di chiamata** (metà del
B-7, quella che si poteva chiudere): *nessun punto di chiamata deve nominare un
codice ritirato*. È diventato calcolabile solo adesso — prima del B-5 il backend
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
