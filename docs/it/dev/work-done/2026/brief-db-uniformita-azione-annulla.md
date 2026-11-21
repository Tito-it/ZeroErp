# Brief DB — l'azione «Annulla» non ha lo stesso aspetto in tutti i domini

> ✅ **CHIUSO il 2026-08-06.** Tutte e tre le richieste applicate dal team DB e
> verificate sull'uscita delle funzioni vive (§6), più la validazione a video di
> Tid. Il lato frontend era già pronto: non è servita una riga in più.

<!-- markdownlint-disable-next-line MD028 -->
> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-08-06.
> **A chi:** team DB.
> **Da dove nasce:** validazione in-app di
> [test-be-vie-uscita-operatore.md](test-be-vie-uscita-operatore.md). Tid, provando
> il verbo «Annulla» tornato disponibile su preventivi e ordini, ha notato che **il
> pulsante non è lo stesso nei due domini**.
> **Decisione di Tid (2026-08-06):** l'aspetto resta un **dato**, dove è oggi. Non
> si sposta la scelta grafica in una regola del frontend: si allineano i seed.

---

## 1. Il fatto

Il pulsante di riferimento — quello che Tid ha riconosciuto come standard — è
quello di **ordini e DDT**: sfondo bianco, bordo rosso, scritta rossa. Cioè
`severity: danger` + `outlined: true`.

`severity` è già `danger` su **tutti e otto** i domini. L'unica cosa che diverge
è `outlined` — e, in un caso, l'icona.

| Dominio | `outlined` nel seed | la fn capability lo **emette** | A video |
| --- | --- | --- | --- |
| ordini | `true` | sì | ✅ bordo rosso |
| DDT | `true` | sì | ✅ |
| resi | `true` | sì | ✅ |
| commesse | `true` | sì | ✅ |
| lotti | `true` | sì | ✅ (ma icona diversa, §2.4) |
| **contratti** | **`false`** | sì | ❌ rosso pieno |
| **preventivi** | **assente** | **NO** | ❌ rosso pieno |
| **offerte** | **assente** | **NO** | ❌ rosso pieno |

## 2. Le tre richieste

### 2.1 Il seed — `outlined: true` sui tre outlier

| File | Riga | id | Transizione | Oggi |
| --- | --- | --- | --- | --- |
| `config/transizioni_stati_preventivi.csv` | 3 | 2 | `DRAFT → ANNULLATO` | chiave assente |
| `config/transizioni_stati_preventivi.csv` | 7 | 6 | `EMESSO → ANNULLATO` | chiave assente |
| `config/transizioni_stati_preventivi.csv` | 8 | 7 | `ACCETTATO → ANNULLATO` | chiave assente |
| `config/transizioni_stati_contratti.csv` | 3 | 2 | `→ ANNULLATO` | `"outlined": false` |
| `config/stati_doc_offerte_transizioni.csv` | 3 | 2 | `→ ANNULLATO` | chiave assente |

Le tre righe del preventivo vanno toccate **tutte e tre**: il pulsante è lo stesso
per l'operatore, anche se per la matrice sono transizioni diverse.

### 2.2 ⚠️ Le funzioni — senza questo, il §2.1 non si vede

**È il punto per cui questo è un brief e non una riga di richiesta.**

`fn_available_actions_preventivo` e `fn_available_actions_offerta` **non
emettono affatto** la chiave `outlined` nel `jsonb_build_object` dell'azione: le
altre sei sì (`COALESCE((t.meta->>'outlined')::boolean, false)`). Il frontend
riceve un'azione senza quel campo e applica il default `false`.

Quindi: **cambiare solo il seed lascerebbe il dato fermo nel database**. La
verifica sarebbe verde a interrogare il CSV o la tabella, e il pulsante a video
resterebbe rosso pieno.

Ce ne siamo accorti solo andando a leggere il corpo delle due funzioni: dal nome
del campo sembrava una riga di configurazione, ed era mezza strada. È lo stesso
tipo di trappola del §3.3 del [brief vie d'uscita](brief-db-vie-uscita-operatore.md)
— **un campo si verifica dal percorso che lo attraversa, non dal punto in cui è
scritto.**

Serve quindi aggiungere `'outlined', COALESCE((t.meta->>'outlined')::boolean, false)`
nella costruzione dell'azione di entrambe le funzioni, come già fanno le altre sei.

> ℹ️ Fatto questo, `outlined` diventa disponibile a **tutte** le azioni di quei
> due domini, non solo all'annullamento — che è il comportamento delle altre sei
> e il motivo per cui conviene sistemarlo qui invece che con un caso speciale.

### 2.3 Il nome dello stato di destinazione nelle capability

**Richiesta nuova, aggiunta il 2026-08-06 su decisione di Tid.** Riguarda tutte e
otto le `fn_available_actions_*`, non solo l'annullamento.

La frase di conferma del cambio stato dice «Portare il DDT nello **stato**
{stato}?», ma il frontend può metterci solo **il nome dell'azione** — e infatti
oggi si legge «Portare il DDT nello stato *Annulla DDT*?». `Annulla DDT` non è
uno stato: lo stato è `ANNULLATO`, e all'operatore va detto «*Annullato*».

**Il frontend non può derivarlo, e non è un'opinione.** L'azione espone
`target_state`, che è il `codice_interno`; la forma leggibile è la colonna
`descrizione` della tabella di stato, e non è ricavabile dal codice:

| `codice_interno` | `descrizione` | Cosa darebbe una trasformazione del codice |
| --- | --- | --- |
| `DRAFT` | **Bozza** | «Draft» — sbagliato |
| `ALLOCATO` | **Allocato a magazzino** | «Allocato» — monco |
| `ANNULLATO` | Annullato | corretto per caso |

Con due casi su tre sbagliati, qualunque traduzione lato frontend sarebbe una
seconda copia del vocabolario degli stati: esattamente ciò che il modello
data-driven evita.

**Cosa serve:** accanto a `target_state`, il campo **`target_state_descrizione`**
in ogni entry di `available_actions`. Il `JOIN` sulla tabella di stato **c'è già**
in tutte e otto le funzioni (serve per `sa.codice_interno`): è la colonna
accanto.

```sql
'target_state',              sa.codice_interno,
'target_state_descrizione',  sa.descrizione,   -- <- questa
```

Per le azioni costruite a mano dentro le funzioni (`crea_revisione`,
`push_commessa`, `genera_ordine`, `ristampa`) `target_state` è `NULL`: lì
`target_state_descrizione` resta `NULL` e va bene così — non sono cambi di stato.

✅ **Il frontend è già cablato** (2026-08-06): i sei drawer con conferma leggono
`action.target_state_descrizione` e ripiegano sulla label dell'azione finché il
campo non arriva. Comportamento invariato oggi, frase corretta il giorno stesso
in cui applicate — **zero lavoro FE**.

> ℹ️ La `descrizione` è in italiano anche per l'interfaccia inglese. È già così
> ovunque nell'app (il Tag di stato dei drawer mostra `stato_descrizione` dal DB),
> quindi non introduce un'incoerenza nuova. Se un giorno gli stati diventeranno
> multilingua, sarà un lavoro suo, non di questo campo.

### 2.4 L'icona — si allineano i sette, non il lotto

Il lotto usa `pi pi-times-circle` (una **X dentro un cerchio**), gli altri sette
`pi pi-times` (una X nuda). **Decisione di Tid (2026-08-06): è migliore quella del
lotto**, quindi la direzione è l'opposta di quella che sembrerebbe dal conteggio —
si muovono i sette, il lotto resta.

| File | Righe | Quante |
| --- | --- | --- |
| `config/transizioni_stati_preventivi.csv` | 3, 7, 8 | 3 |
| `config/transizioni_stati_ordini.csv` | 3, 4 | 2 |
| `config/transizioni_stati_ddt.csv` | 3, 5, 9 | 3 |
| `config/transizioni_stati_reso.csv` | 3, 4 | 2 |
| `config/transizioni_stati_contratti.csv` | 3 | 1 |
| `config/stati_doc_offerte_transizioni.csv` | 3 | 1 |
| `vendite/transizioni_stati_commessa.csv` | 4, 7, 9, 12 | 4 |
| `config/stati_doc_fiscale_transizioni.csv` (lotto) | — | **invariato** |

**16 righe**, `"icon": "pi pi-times"` → `"pi pi-times-circle"`. Sono le stesse
righe del §2.1 per preventivi/contratti/offerte: conviene un passaggio solo.

> ℹ️ Prendere le righe **per `action_key = 'annulla'`**, non per numero di riga:
> i numeri qui sopra sono al 2026-08-06 e un append al CSV li sposta.

## 3. Cosa NON stiamo chiedendo, e perché è scritto

Durante l'analisi è emerso che `outlined` porta **sempre lo stesso valore** per la
stessa azione in tutti i domini: non è informazione che varia per transizione, è
la convenzione «distruttivo = bordo rosso su bianco» — che peraltro è già scritta
in `frontend-standards.md` §Azioni Drawer. La si potrebbe ritirare come dato e
farla diventare una regola del design system (`danger` ⇒ outlined), con un solo
posto da guardare invece di otto seed da ricordarsi.

**Tid ha deciso di lasciare le cose come sono**: l'aspetto resta un dato,
governato dal `meta` delle transizioni. Lo annotiamo qui perché la domanda non si
riapra da zero la prossima volta che qualcuno trova un ottavo pulsante diverso —
la scelta è stata fatta consapevolmente, non per inerzia.

## 4. Come si verifica che è fatto

Non dal CSV e non dalla tabella: **dall'uscita della funzione**, che è ciò che il
frontend riceve davvero.

```sql
-- deve dare outlined = true per tutti e otto i domini
SELECT 'preventivo' AS dominio, a->>'outlined' AS outlined, a->>'icon' AS icona
  FROM vendite.preventivi p
  CROSS JOIN LATERAL jsonb_array_elements(
        script.fn_available_actions_preventivo(p.id)->'available_actions') a
 WHERE a->>'key' = 'annulla'
 LIMIT 1;
-- ...e le gemelle su offerta, contratto, lotto.
```

⚠️ Attenzione al caso «chiave assente»: oggi su preventivo e offerta
`a->>'outlined'` torna **NULL**, non `false`. Un controllo scritto come
`<> 'true'` li prende; uno scritto come `= 'false'` **no**. Se il pgTAP di questo
lavoro nasce sul secondo, passa senza aver misurato niente.

## 5. Cosa facciamo noi, in parallelo

Lato frontend non c'è nulla da fare sull'aspetto: il pass-through esiste già e
funziona per i sei domini allineati.

Restano a noi le **label**, che sono testo e vivono nei locales — le sistemiamo
sul nostro lato e non vi riguardano:

| Dominio | Oggi | Atteso |
| --- | --- | --- |
| preventivi | «Annulla» | «Annulla preventivo» |
| contratti | «Annulla» | «Annulla contratto» |
| offerte | «Annulla» | «Annulla offerta» |

(gli altri cinque nominano già l'oggetto: «Annulla ordine», «Annulla DDT», …)

✅ **Fatto il 2026-08-06** (it + en). Tutti e otto nominano ora l'oggetto.

Allineato lo stesso giorno anche il **messaggio di conferma**, sul modello del
DDT scelto da Tid («Portare il DDT nello stato {stato}?»): erano fuori riga
preventivi, resi e commesse. Ora i sei domini con conferma dicono la stessa
frase.

La frase resta quella del DDT; a diventare corretto è **il valore** che ci
finisce dentro, ed è la richiesta del §2.3.

> Perché l'oggetto resta nella label, benché la preferenza iniziale fosse
> «Annulla» secco: `common.cancel` vale **«Annulla»** ed è il pulsante di
> `FormFooter`, in fondo a **ogni** drawer. Con la label secca l'operatore
> avrebbe due «Annulla» nella stessa schermata — uno che scarta quello che sta
> scrivendo, l'altro che manda il documento in `ANNULLATO`, **stato terminale**.
> La più pericolosa è quella che sembra innocua.

---

## 6. Chiusura — verificato sulle funzioni vive (2026-08-06)

Il team DB ha applicato le tre richieste sul database di sviluppo (non ancora
pushate al momento di questa verifica). Misurato **dall'uscita delle funzioni**,
come prescritto dal §4 — non dal CSV, che qui sarebbe stato muto:

| Dominio | `outlined` | `icon` | `target_state` | `target_state_descrizione` |
| --- | --- | --- | --- | --- |
| preventivo | `true` | `pi pi-times-circle` | `ANNULLATO` | «Annullato» |
| ordine | `true` | `pi pi-times-circle` | `ANNULLATO` | «Annullato» |
| DDT | `true` | `pi pi-times-circle` | `ANNULLATO` | «Annullato» |
| reso | `true` | `pi pi-times-circle` | `ANNULLATO` | «Annullato» |
| contratto | `true` | `pi pi-times-circle` | `ANNULLATO` | «Annullato» |
| offerta | `true` | `pi pi-times-circle` | `ANNULLATA` | «Annullata» |
| commessa | `true` | `pi pi-times-circle` | `ANNULLATA` | «Annullata» |
| lotto | `true` | `pi pi-times-circle` | `ANNULLATA` | «Annullata» |

**Otto su otto su tutte e tre le colonne.** I due domini del §2.2 — preventivo e
offerta, quelli che non emettevano affatto `outlined` — ora lo emettono: era la
metà del lavoro che dal seed non si sarebbe vista.

### 6.1 Il campo si chiama come il frontend si aspettava

Controllo fatto per primo, e non per formalità: il cablaggio FE del §2.3 legge
`action.target_state_descrizione`. Se il DB avesse scelto un altro nome, il
fallback avrebbe continuato a funzionare **senza errori** e la frase sarebbe
rimasta quella vecchia — un difetto che non si annuncia. Verificato con una
chiamata reale: il nome coincide, e la chiave è presente in tutte e otto le
funzioni.

### 6.2 Cosa legge l'operatore adesso

```text
Portare il preventivo nello stato Annullato?
Portare l'ordine nello stato Annullato?
Portare il DDT nello stato Annullato?
Portare il reso nello stato Annullato?
Portare il contratto nello stato Annullato?
Portare la commessa nello stato Annullata?
```

La frase è quella del DDT scelta da Tid, e ora dice il vero: dentro c'è lo
**stato**, non il nome dell'azione. Verificata anche la concordanza di genere sui
sei domini con conferma — i cinque maschili ricevono «Annullato», la commessa
«Annullata». Torna perché la descrizione arriva dalla tabella di stato del
dominio, non da una stringa unica condivisa.

### 6.3 Riepilogo di chi ha fatto cosa

| | |
| --- | --- |
| **DB** | `outlined: true` sui 3 seed fuori riga · emissione di `outlined` in `fn_available_actions_preventivo` e `_offerta` · icona `pi-times-circle` sulle 16 righe · `target_state_descrizione` in tutte e otto le funzioni |
| **FE** | label che nominano l'oggetto (8 domini, it + en) · messaggio di conferma allineato al modello DDT (6 domini) · lettura di `target_state_descrizione` col fallback |
| **Nessuno** | l'aspetto: il pass-through esisteva già ed è bastato |
