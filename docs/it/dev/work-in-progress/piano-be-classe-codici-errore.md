# Piano BE — classe dei codici errore

**Chi:** team BE (`dev/backend-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 18 decisioni, le misure, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-db-classe-codici-errore](piano-db-classe-codici-errore.md).
**Stato:** 🟢 **B-1, B-2, B-3, B-4 FATTI** (2026-08-07) — i quattro passi senza prerequisiti DB. 🔴 **B-5, B-6, B-7 restano al cancello D-9.**

> **Verifica dell'equivalenza, prima di tutto il resto.** I **658** codici
> superstiti risolvono **identici** a prima — stesso status, stessa `ui_action`,
> stesso messaggio — confrontando `resolve()` vecchio e nuovo uno per uno; i due
> ripieghi rispondono come prima. Suite Django: **3587 test verdi**, compreso il
> cancello del terzo lato contro il DB vero (`ZEROERP_TEST_DB_E2E=1`).
> L'unica differenza voluta è `PREV_STATO_NON_MODIFICABILE`, che non c'è più (B-1).
>
> ⚠️ **Tre cose sono emerse facendolo, e due cambiano il piano**: il §6.

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

| # | Passo | Dipende da | Costo | Stato |
|---|---|---|---|---|
| **B-1** | Togliere `PREV_STATO_NON_MODIFICABILE` | — | una riga | ✅ 2026-08-07 |
| **B-2** | `classe` senza status ⇒ **eccezione, non ripiego** | — | poche righe + test | ✅ 2026-08-07 |
| **B-3** | Riorganizzare `error_policies.py` in **4 moduli** | — | il grosso del lavoro a mano | ✅ 2026-08-07 |
| **B-4** | La mappa **classe → HTTP** (8 righe) + derivazione dello status | B-3 | piccolo | ✅ 2026-08-07 |
| **B-5** | Il **generatore** di `error_policies_generated.py` | 🔴 DB **D-9** | medio | 🔴 al cancello |
| **B-6** | Il **controllo di divergenza** in CI | B-5 | piccolo | 🔴 |
| **B-7** | La regola «niente nuovi codici generici» | B-6 | coda | 🔴 |

**Cosa esiste ora, in quattro file** (`backend/apps/core/services/`):

| File | Righe | Voci | Chi lo scriverà |
|---|---|---|---|
| `error_policies_generated.py` | 1417 | **658** `codice → classe` | il generatore, dal B-5 |
| `error_policies.py` | 231 | le **8+7+7** righe di regole + la logica | a mano, quasi mai |
| `error_ui_overrides.py` | 540 | **176** `ui_action` fuori default | a mano |
| `error_messages_fallback.py` | 679 | **658** messaggi senza segnaposto | a mano, per ora |
| `apps/core/tests/services/test_error_policies_classi.py` | — | **14 test**, uno per ogni modo nuovo di rompersi | — |

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

---

## 5. ⭐ Cosa il BE consegna al DB, adesso — e cosa il DB deve sapere

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

⚠️ **Quello che resta aperto è la sequenza**, e va deciso: se il DB semina le
note al D-5 (usando il CSV), al B-5 il generatore le riemette come commenti e il
giro si chiude. Se il seed parte **senza** la colonna `note`, il B-5 va fatto
solo dopo averla riempita — o le 731 righe se ne vanno alla prima esecuzione.

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
