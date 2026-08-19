# Due richieste al team DB dal lato applicativo · *perimetro emittente*

> **Cos'è.** Le due sole cose che il piano BE/FE di
> [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)
> **non può scrivere da sé**, perché stanno nel database. Tutto il resto del
> piano procede in parallelo e non le aspetta.
>
> **Origine.** Emerse il **2026-08-18** scrivendo §13-bis, misurando il codice
> applicativo contro l'apply DB dello stesso giorno.
>
> **Destinatario**: team DB, branch `dev/db-tid`.
> **Autorizzazione**: Tid, 2026-08-18 — entrambe confermate nel merito.

| # | Cosa | Peso | Blocca |
| --- | --- | --- | --- |
| ✅ **R-1** | Un **codice errore nuovo** a catalogo: il rifiuto del cancello `multi_emittente` | append a due CSV | ⛔ il passo **C-2** del piano BE/FE |
| ✅ **R-2** | Una **chiave nel context** dei ~~due~~ **cinque** punti: `'campo'` al posto di `'column'` | ~~una riga per changeSet~~ | 🔵 niente — è il campo del form che non si evidenzia |

> ## 🟢 CHIUSO il 2026-08-18 — entrambe fatte e applicate (`d28d4a2f2`)
>
> Lato backend: policy rigenerate (**702** voci) e messaggio di ripiego
> aggiunto per `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` — `422` con la frase giusta,
> verificato. Il canale `COLUMN` dei guard parte, e `campiErrati` porta
> `parent_account_id` al form. Niente resta aperto: il ⛔ sulla riga R-1 qui
> sotto descrive cosa **bloccava** allora, non oggi.
>
> **E il team DB ha corretto il perimetro di R-2 in tre punti — tutti e tre
> fondati.** Le rettifiche stanno in §13-bis.2 del brief principale; qui resta
> quello che riguarda **come avevo misurato**, perché è la parte da cui si
> impara qualcosa.
>
> ### 🔴 Due errori miei nella richiesta, non uno
>
> **1. Il perimetro era incompleto: le occorrenze erano CINQUE, non due.** Le
> tre che mancavano stanno in `20260818-05` — **stesso giorno, stesso cantiere,
> stesso campo `parent_account_id`** — e sono più numerose di quelle che avevo
> trovato (5 contro 2).
>
> ⚠️ **E l'errore non è «me n'è sfuggito uno»: è come ho guardato.**
>
> | Cosa ho fatto | Cosa è successo |
> | --- | --- |
> | `grep -rl "'column'," … \| head` per la ricognizione | i file erano **20**, ne ho letti **10**, e ho preso la lista troncata per completa |
> | poi, sul `-05`, ho cercato **`'campo'`** e ho trovato zero | vero, e **inutile**: misurava l'assenza della cosa giusta senza misurare la **presenza** della cosa sbagliata. Il `-05` è uscito dalla richiesta con una verifica che sembrava averlo esaminato |
>
> ⛔ **`head` non va usato su un grep da cui si deriva un perimetro.** Serve a
> guardare, non a contare: se il risultato finisce in una tabella di richiesta,
> si conta (`wc -l`) o si legge tutto.
>
> ⚠️ E il danno sarebbe stato peggiore del difetto: correggere **solo** il `-08`
> avrebbe reso il comportamento **intermittente** sullo stesso campo — un guard
> accende il form, l'altro no. *«Un difetto costante si nota e si segnala; uno
> intermittente fa cercare il problema nel frontend»* (team DB).
>
> **2. La motivazione del «nessun segnaposto» in R-1 non reggeva.** Avevo scritto
> che un messaggio senza `%s` «non ha quel modo di rompersi», citando i tre
> `format()` rotti. Ma **411 messaggi su 913 hanno un `%s`**: non è un pattern
> rischioso da evitare, è la **norma**. Il motivo buono è un altro, ed è quello
> che il team DB ha scritto nel `note`: *chi apre la lista sa già quale lista ha
> aperto — non c'è niente di variabile da dire*. La differenza è pratica: senza
> la ragione giusta scritta, il primo che passa aggiunge un `%s` per uniformità.
>
> ### ⭐ Il criterio giusto, che non avevo formulato
>
> Non è «changeSet nuovo» — è **«è il nome di una colonna che il client può
> correggere»**:
>
> ```text
> 'column', 'parent_account_id'              -> 'campo'   colonna vera      (4×)
> 'column', 'valido_dal'                     -> 'campo'   colonna vera      (1×)
> 'column', 'valido_al_requires_valido_dal'  -> resta     è una REGOLA
> 'column', 'multi_emittente'                -> resta     non è in nessun form
> ```
>
> ⛔ **`20260818-17` non è stata toccata, e ha ragione il DB.** `multi_emittente`
> non compare in `frontend/src/` con nessuna grafia e si scrive solo dal seed:
> mandarla nel canale `COLUMN` direbbe al form di accendere **un campo che non
> esiste in nessuna schermata**. Si passerebbe da «non evidenzia» a «evidenzia
> il vuoto», che è più difficile da vedere — ed è lo stesso uso diagnostico che
> la richiesta voleva preservare nelle funzioni storiche. Avevo elencato il
> changeSet applicando la regola *sintattica* invece di quella *di merito*.


---

## R-1 · Il codice errore del cancello `multi_emittente` ⛔

### Cosa serve

| | |
| --- | --- |
| **Codice** | `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` |
| **Classe** | `NON_ESEGUIBILE` |
| **Messaggio** | *«Questa lista non dice da quale emittente arriva ogni riga: scegli un emittente per entrare.»* |
| **Dove** | append a `80_data/sql/config/codici_errore.csv` + `messaggi_errore.csv` |

⚠️ **Solo append ai CSV**, mai un `INSERT`/`UPDATE` SQL a parte: i due file sono
mirror `loadUpdateData` `runOnChange`, e un SQL sulla stessa tabella creerebbe la
seconda sorgente di verità che diverge fra dev e CI (AGENTS.md, §80_data).

⚠️ **Nessun segnaposto nel messaggio.** Il testo sopra non ne ha, ed è
deliberato: tre righe del catalogo mandavano in crash `format()` proprio per un
segnaposto scritto male, e il difetto si è visto solo il giorno in cui l'errore
è scattato davvero (passo 3, §12). Un messaggio senza `%s` non ha quel modo di
rompersi.

### Chi lo solleva, e perché non è un 403

Lo solleva il **backend**, non una funzione PL/pgSQL: è
`apps/core/services/perimetro_emittente.guard_lista`, quando una lista con
`multi_emittente = false` viene aperta da chi ha in scope **più di un**
emittente (o l'universo). Il catalogo serve perché *ogni* codice che l'app
nomina deve avere la sua classe — il cancello del terzo lato non distingue
fra codici nati nel DB e codici nati nel backend.

**Classe `NON_ESEGUIBILE` (422), non `NON_PERMESSO` (403)**, e la ragione è di
merito: il diritto **c'è**. Manca una precondizione che l'utente scioglie da sé,
scegliendo un emittente dalla combo di topbar. Il flag *«non è un permesso»*
(P-2b): non decide *cosa* si può vedere — quello lo decidono scope e RLS —
decide se una schermata è **leggibile** nella condizione in cui sta per essere
aperta. Un 403 racconterebbe una bugia sul motivo, e fra sei mesi qualcuno
cercherebbe un diritto da concedere a qualcuno.

### Come si verifica che è arrivato

```bash
cd backend
./manage-env.sh genera_error_policies --check   # deve segnalare la divergenza PRIMA
./manage-env.sh genera_error_policies           # poi rigenera
```

**Fatto quando**: il codice ha la sua classe in `error_policies_generated.py` e
`test_error_codes_db_policy_guardrail` è verde.

> ✅ **ARRIVATA il 2026-08-18**, poche ore dopo la richiesta. Seminata con la
> classe chiesta; lato BE: policy rigenerate (701 → **702** voci) e **messaggio
> di ripiego aggiunto** — che è la seconda metà di «registrare un codice» e non
> era nella richiesta perché è lavoro BE, non DB.
> Verificato: `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` → classe `NON_ESEGUIBILE`,
> **422**, messaggio giusto. **Il passo C-2 è sbloccato.**

---

## R-2 · Il canale del campo è muto nei due guard nuovi 🔵

### La misura

`script.fn_log_and_raise_error` porta al client **due** cose strutturate: il
codice di dominio nel canale `CONSTRAINT` e il **nome del campo da correggere**
nel canale `COLUMN`. Il secondo lo legge dal context, e legge **una chiave
precisa**:

```sql
v_campo := nullif(btrim(coalesce(p_context ->> 'campo', '')), '');
IF v_campo IS NULL THEN
    v_campo := nullif(btrim(coalesce(p_context ->> 'parametro', '')), '');
    v_campo := nullif(regexp_replace(coalesce(v_campo, ''), '^p_', ''), '');
END IF;
```

I due changeSet applicati il 2026-08-18 scrivono invece `'column'`:

| ChangeSet | Punto | Oggi | Serve |
| --- | --- | --- | --- |
| `20260818-08-create-fn-guard-albero-ba-emittente` | i due `PERFORM` (verso padre, verso figli) | `'column', 'parent_account_id'` | `'campo', 'parent_account_id'` |
| `20260818-17-create-trgfn-lista-definizione-guard-multi-emittente` | il `PERFORM` del guard | `'column', …` | `'campo', …` |

⚠️ **Non è un refuso di distrazione, ed è il motivo per cui vale la pena
scriverlo**: `'column'` è una chiave che altre funzioni usano da tempo come
annotazione **diagnostica** del context (`trgfn_qta_from_operativa`,
`trgfn_lock_columns`, …), quindi ha l'aria giusta e non salta all'occhio in
review. Il canale verso il form si chiama `'campo'`, e la differenza si vede
solo leggendo il corpo della funzione che lo consuma — non il nome della chiave.

### Perché conta, e quanto

Il `note` a catalogo di **tre** dei codici nuovi dichiara in chiaro *«Campo da
dichiarare al client: `parent_account_id`»*: l'intenzione era esplicita e non
arriva a destinazione. Lato applicativo il pezzo c'è già tutto —
`apps/core/services/db_error_fields.py` legge `diag.column_name`,
`ErrorTranslator` lo mette in `error.fields`, `useApiHandler` lo espone come
`campiErrati` e i form lo usano per `:invalid`.

**Effetto oggi**: chi sbaglia il padre di un billing account riceve il messaggio
giusto in un banner, ma il campo «Account padre» **non si accende**. Piccolo, e
silenzioso — che è precisamente la categoria di difetto che questo cantiere ha
passato due giorni a rendere rumorosa.

⚠️ **Il perimetro sono i changeSet nuovi, non una bonifica.** Le funzioni
storiche che usano `'column'` per diagnostica **non si toccano**: lì quella
chiave significa un'altra cosa e la sta dicendo bene.

### Come si verifica

Un pgTAP che provochi il guard e asserisca il **campo strutturato**, non il
messaggio:

```sql
-- il codice esce da CONSTRAINT, il campo da COLUMN: due canali, due asserzioni
```

⚠️ Con `throws_like` sulla frase si verifica il messaggio, **non** il canale:
un test scritto così resterebbe verde con `'column'` ancora al suo posto — verde
per sottrazione, sul difetto che stiamo correggendo.

**Fatto quando**: `column_name` arriva valorizzato all'eccezione, e il form
evidenzia `parent_account_id`.

---

## Cosa NON si chiede

- **nessuna migrazione applicata da me**: qui si scrive la richiesta, l'apply lo
  autorizza Tid per quel comando;
- **nessuna bonifica** dei `'column'` storici (sopra);
- **nessun secondo parametro** a `fn_log_and_raise_error`: la firma finisce con
  `VARIADIC` e il canale del context esiste apposta — è scritto nel suo `COMMENT`.
