# Brief — Annullamento di una riga manuale di commessa

> **Tipo**: brief misto — **§4 al team DB** (`dev/db-tid`), §5-§6 BE/FE
> (`dev/backend-tid`) · **Data**: 2026-07-28 · **Owner**: Tid ·
> **Stato**: ⬜ **DA FARE** — §4 (madre DB) è **prerequisito** di §5
> ([[feedback_be_fe_attende_prerequisiti_db]]) ·
> **Priorità**: 🟠 MEDIA (buco operativo reale, nessun dato a rischio) ·
> **Rev. 2026-07-28 (analisi critica)**: §4-§6 corretti sui punti G1-G10,
> piano operativo in **§9**. Vedi registro §8.
>
> **Origine**: emerso il 2026-07-28 durante la validazione in-app della porta
> oneri ([brief-db-immutabilita-quantita-e-porta-oneri](brief-db-immutabilita-quantita-e-porta-oneri.md)
> step 10). Domanda di Tid: *«un onere caricato manualmente potrebbe essere
> cancellato o corretto?»*
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]) → breaking secchi ammessi.

---

## 1. Il buco, in una frase

Un onere caricato per errore — causale sbagliata, cliente sbagliato, doppio
click — **non si può togliere in nessun modo**, e finisce in fattura.

---

## 2. Perché oggi non c'è rimedio

Verificato sul codice vivo il 2026-07-28.

| Via di uscita | Esito | Perché |
|---|---|---|
| Cancellare la riga | ❌ | Non esiste **nessun** endpoint DELETE su `vendite.commesse_attivita` |
| Correggere l'importo | ⚠️ parziale | `variazione-prezzo-eccezionale`, ma richiede `prezzo > 0`: una penale da 500 € inserita per sbaglio può diventare da 1 €, **non può sparire**. E si chiude appena la riga è fatturata (`fattura_riga_id` valorizzato) |
| Stornare con un onere negativo | ❌ | `fn_aggiungi_onere_commessa` vieta `p_importo <= 0`: *«una NC travestita (importo negativo) è vietata per costruzione»* |
| Azzerare l'importo | ❌ | Stesso guard `prezzo > 0` lato service |
| Cambiare la quantità | ❌ | È 1 per costruzione, e il guard di immutabilità la protegge |

### 2-bis. La tensione logica che sta sotto (non solo un endpoint mancante)

Il brief porta-oneri §0 dichiara: *«I fatti non si modificano: si correggono con
altri fatti — righe nuove, mai UPDATE»*.

Su una riga onere il modello si comporta **all'opposto**:

- il guard di immutabilità protegge la **quantità**, che su un onere vale sempre
  1 → non protegge nulla di sostanziale;
- tutto il contenuto economico sta nel **prezzo**, che è deliberatamente
  mutabile con UPDATE (autorizzato);
- e la correzione «con un altro fatto» — un onere di storno — è **vietata**.

Le due regole sono giuste per le righe da push, dove la quantità **è** il fatto
e il prezzo è un attributo negoziabile. Su un onere quel rapporto si inverte, e
nessuna delle due era stata ripensata. Questo brief non riapre le regole:
aggiunge la terza via, l'unica coerente col libro giornale — **annullare senza
cancellare**.

---

## 3. La buona notizia: il meccanismo esiste già

`vendite.commesse_attivita.stato_emissione` ha un CHECK a **tre** valori:
`NON_EMESSA`, `EMESSA`, **`ANNULLATA`**. Il terzo non è mai stato usato, ma è
già onorato ovunque conti. Verificato una porta per volta:

| Dove | Filtro | Effetto su una riga `ANNULLATA` |
|---|---|---|
| `fn_emit_attivita_fatturabili_da_commessa` | `WHERE ca.stato_emissione = 'NON_EMESSA'` | **non emessa** → nessuna AF → **mai in fattura** |
| `fn_list_commesse_emittibili` | `AND ca.stato_emissione = 'NON_EMESSA'` | la commessa non compare se ha solo righe annullate |
| `fn_list_emittibili_lane` | idem | nessuna terna, nessun lotto |
| `vw_dash_competenza_attivita` | `WHERE … AND ca.stato_emissione <> 'ANNULLATA'` | **sparisce dal cockpit**: fuori da contatori, lista attività e lista gruppi |

L'ultima riga era il rischio maggiore: senza l'esclusione nella vista, la riga
sarebbe rimasta a video come «da emettere» pur non essendo emettibile —
contatore bugiardo e gruppo fatturabile selezionabile che poi non produce nulla.
**È già gestito.**

### 3-bis. Altre tre porte, trovate in verifica (2026-07-28)

Il conto di §3 era **prudente**. Rileggendo tutti i lettori di
`commesse_attivita` ne sono emerse altre tre, tutte a favore:

| Dove | Filtro | Effetto |
|---|---|---|
| `vw_dash_fatturazione_commesse` | `AND ca.stato_emissione <> 'ANNULLATA'` | quinta porta verso il cockpit, già chiusa |
| `fn_approva_commessa_attivita` | `AND ca.stato_emissione = 'NON_EMESSA'` | una riga annullata **non è ri-approvabile**: il «nessun ripristina» di §7 è già strutturale, non solo una scelta |
| `script.fn_check_commessa_chiudibile` | motivo ostativo = `APPROVATA + NON_EMESSA` | annullare una riga **sblocca la chiusura della commessa**. Non ovvio, e decisivo: senza, una commessa con un onere sbagliato restava incastrata per sempre fra un guard di chiusura e un onere non togliibile |

> **Conseguenza**: niente colonna nuova, niente migration di schema, nessun
> cambio ai filtri. Manca solo **il modo di impostare quel valore** — più il
> ritocco ai contatori di testata di §3-ter, che è l'unica porta rimasta aperta.

### 3-ter. L'unica porta rimasta aperta: i contatori di testata

`vendite.fn_get_commessa_stato` conta `total_non_emesse` come
`stato_emissione <> 'EMESSA'` — cioè **include le annullate** — e la riga resta
dentro `total_attivita` e `total_approvate`. Dopo l'annullamento la testata del
drawer mostrerebbe *Attività 3, Approvate 3, Emesse 0*: identico a prima. È lo
stesso «contatore bugiardo» che §3 si complimenta di aver evitato sulla vista,
ripresentato sulla testata — e §6 promette proprio un «refresh dei contatori».

**Decisione Tid (2026-07-28): si corregge.** `total_approvate` e
`total_non_emesse` escludono `ANNULLATA`; `total_attivita` resta il conteggio
**fisico** delle righe (una riga annullata esiste, e il totale non deve
mentire sull'esistenza). È il changeset **D3** di §9.

---

## 4. [DB] Cosa serve — funzione madre `fn_annulla_commessa_attivita`

⚠️ **Prerequisito di §5.** Sono **due scritture** (UPDATE dello stato + INSERT
dell'evento di log): la regola di casa preferisce una madre DB a un
`transaction.atomic()` lato Python ([api.md §Atomicità](../api.md)), e il
gemello `fn_aggiungi_onere_commessa` è già costruito così.

> **Nome (rev. 2026-07-28, G8)**: `fn_annulla_commessa_attivita`, non
> `fn_annulla_riga_manuale_commessa`. Allineato a
> `fn_approva_commessa_attivita`, la sorella che agisce sulla stessa tabella,
> e distinguibile a colpo d'occhio da `script.fn_check_commessa_annullabile`
> e dallo stato commessa `ANNULLATA` (codice 558) — due annullamenti diversi
> sullo stesso aggregato. «Manuale» è un **guard** (§4c), non parte
> dell'identità della funzione.

### 4a. Firma

```sql
vendite.fn_annulla_commessa_attivita(
    p_commessa_attivita_id bigint,
    p_motivo               text
) RETURNS bigint
```

> **`RETURNS bigint` e non `boolean` (rev. 2026-07-28, G2)**: con i guard di
> §4b la funzione può solo riuscire o sollevare, quindi un booleano non
> porterebbe alcuna informazione. Torna il `commessa_attivita_id`, come il
> gemello `fn_aggiungi_onere_commessa` torna l'id della riga creata: utile al
> payload di risposta e simmetrico alla porta.

### 4b. Cosa deve fare

1. **Guard parametri** (AGENTS.md): `p_commessa_attivita_id` NULL o `<= 0` →
   errore parlante; `p_motivo` obbligatorio, non vuoto dopo `btrim`.
2. **Caricare la riga** — inesistente → errore dedicato.
3. **Guard «già annullata»**: `stato_emissione = 'ANNULLATA'` → errore
   **dedicato**. Vedi il riquadro sotto.
4. **Guard «è manuale»**: `sorgente_tipo_id IS NULL`. Vedi §4c: è il
   discriminante, e non è negoziabile.
5. **Guard «non emessa»**: `stato_emissione = 'NON_EMESSA'`. Una riga già emessa
   ha generato un'AF: annullare la riga di commessa **non la toglierebbe dalla
   catena**, lascerebbe un'AF orfana.
6. `UPDATE … SET stato_emissione = 'ANNULLATA'`.
7. **INSERT in `commesse_attivita_log`** — evento `RIGA_MANUALE_ANNULLATA`,
   `dettaglio` con `motivo`, `stato_precedente`, `prezzo_snapshot`,
   `tipo_movimento`, `segment_key`. `tx_id` e audit li mettono i trigger della
   tabella. ✅ **Verificato**: `commesse_attivita_log.evento` non ha CHECK né
   tabella-vocabolario → nessuna migration di seed per il nuovo evento.

> ⚠️ **Perché il guard 3 esiste ed è separato (rev. 2026-07-28, G1)**. Nella
> stesura originale il guard era il solo `stato_emissione = 'NON_EMESSA'`,
> altrimenti `E_RIGA_COMMESSA_GIA_EMESSA`. Ma una riga **già ANNULLATA** non è
> `NON_EMESSA`: cadeva nello stesso ramo, e chi cliccava due volte leggeva
> *«è entrata nella catena di fatturazione»* — falso. È esattamente l'errore
> che §4d condanna. Niente no-op silenzioso: l'`Idempotency-Key` di §5 copre
> già il replay di rete, e il doppio click consapevole ha diritto di sapere
> che non ha fatto nulla.
>
> **E l'ordine dei guard non è indifferente.** «Non manuale» viene **prima** di
> «già emessa» perché è l'**identità** della riga, non una sua condizione: a una
> riga da push emessa dire *«già emessa»* suggerisce che, se non lo fosse, si
> potrebbe annullare — falso. *«Nasce dal documento X, il rimedio è a monte»* è
> l'unica risposta che porta l'operatore dove deve andare. «Già annullata» resta
> in testa perché una riga `ANNULLATA` è per costruzione manuale (nessun altro
> percorso scrive quel valore), quindi non toglie mai il posto a una diagnosi
> migliore.

Sul fronte opposto — quello che poteva impedire l'UPDATE — non c'è nulla da fare:

> ✅ **Verificato (2026-07-28) — i trigger `BEFORE UPDATE` della tabella non
> si oppongono**, ed era il punto tecnicamente più delicato:
> `trgfn_commesse_attivita_guard_quantita_immutabile` scatta solo se cambia
> `quantita` (qui non cambia); `trgfn_commesse_attivita_guard_tipo_doc_emittibile`
> legge `NEW` e la sua condizione è `APPROVATA + NON_EMESSA`, quindi passando
> ad `ANNULLATA` **si spegne** invece di scattare. Nessun bypass GUC
> necessario.

### 4c. Il discriminante «riga manuale» — deciso: `sorgente_tipo_id IS NULL`

Tre candidati valutati; la scelta **non** è una preferenza di stile.

| Criterio | Verdetto |
|---|---|
| `tipo_movimento = 'ONERE'` | ❌ È la **natura** del movimento, non l'origine. Il CHECK ammette già `RETTIFICA`: il giorno che nasce una porta rettifiche manuale, il filtro su ONERE la escluderebbe **in silenzio** |
| `segment_key LIKE 'MAN:%'` | ❌ Vietato dal progetto stesso: il brief emissione mirata (D-1, nota) dice che i prefissi di `segment_key` sono *«una convenzione di leggibilità, non un contratto»* e derivarne semantica è un accoppiamento fragile |
| **`sorgente_tipo_id IS NULL`** | ✅ **Sourceless = non nata da un documento** = la definizione stessa di «manuale» |

Il terzo è già **consacrato dal modello**: `fn_build_gruppo_fatturabile_key`
definisce il gruppo «oneri di commessa» esattamente come *riga sourceless*
(→ chiave `MAN:<commessa_id>`). Il CHECK `chk_commesse_attivita_sorgente_pair`
ne garantisce la coerenza (coppia tutta NULL o tutta valorizzata, mai mezza).

Conseguenza pratica: se domani nasce un altro tipo di riga manuale,
l'annullamento la copre **senza toccare nulla**. È il vantaggio del criterio —
ed è anche il suo costo, da accettare consapevolmente (rev. 2026-07-28, G9):
chi ha `carica_voce_manuale` potrà annullare un tipo di riga futuro con regole
proprie (per dire: una rettifica manuale agganciata a un documento contabile),
senza che nessuno abbia ripensato il perimetro. Il giorno che nasce il secondo
tipo di riga sourceless, questo guard va **riletto**, non dato per buono.

> ⚠️ **Cautela onesta**: `fn_upsert_commessa_attivita` ha
> `p_sorgente_tipo_id DEFAULT NULL`, quindi «sourceless» è garantito dalla
> disciplina di chi chiama, non dalla struttura. Nella pratica il push passa
> sempre la sorgente — è così che nascono i `segment_key` `ORD:`/`CTR:`/`DDT:` —
> ma il guard di §4b.3 resta necessario e **non va dato per implicito**.

### 4d. Codici errore (nuovi, da aggiungere al CSV messaggi)

| Codice | Quando |
|---|---|
| `E_RIGA_COMMESSA_NON_MANUALE` | la riga ha una sorgente: nasce da un documento, il rimedio è a monte |
| `E_RIGA_COMMESSA_GIA_EMESSA` | `stato_emissione = 'EMESSA'`: è entrata nella catena di fatturazione |
| `E_RIGA_COMMESSA_GIA_ANNULLATA` | `stato_emissione = 'ANNULLATA'`: l'operazione era già stata fatta (rev. 2026-07-28, G1) |
| `E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO` | motivo assente o vuoto |

Errori **distinti** e non uno generico: ogni causa porta l'operatore a
un'azione diversa, e un messaggio unico lo lascerebbe a indovinare. È lo stesso
argomento che ha imposto il terzo codice: *«già emessa»* detto a chi ha
riannullato una riga è un'informazione **falsa**, non solo imprecisa.

Ids CSV: **564-567** (ultimo occupato al 2026-07-28: 563 — `E_FATTURA_SENZA_RIGHE`).
Solo **append** al CSV, nessun loader nuovo ([[feedback_messaggi_errore_no_new_loader]]).

### 4e. Garanzie DB (da coprire con pgTAP)

| # | Deve essere vero |
|---|---|
| A1 | Riga manuale NON_EMESSA → passa a `ANNULLATA` e l'evento è scritto nel log |
| A2 | Riga **con sorgente** → respinta con `E_RIGA_COMMESSA_NON_MANUALE`, stato invariato |
| A3 | Riga **già EMESSA** → respinta con `E_RIGA_COMMESSA_GIA_EMESSA`, stato invariato |
| A3-bis | Riga **già ANNULLATA** → respinta con `E_RIGA_COMMESSA_GIA_ANNULLATA` (G1), nessun secondo evento nel log |
| A4 | Motivo vuoto/assente → respinta, nessuna scrittura |
| A5 | Dopo l'annullamento, `fn_emit_attivita_fatturabili_da_commessa` sulla stessa commessa **non produce AF** per quella riga |
| A6 | Dopo l'annullamento la riga **non compare** in `vw_dash_competenza_attivita` né in `vw_dash_competenza_gruppi` |
| A7 | L'operazione è **atomica**: se l'INSERT del log fallisce, lo stato non cambia |
| A8 | Annullati **tutti** gli oneri della commessa, l'emissione mirata con `p_gruppi = ARRAY['MAN:<commessa_id>']` produce **zero AF** e il gruppo sparisce da `vw_dash_competenza_gruppi` |
| A9 | Dopo l'annullamento i contatori di `fn_get_commessa_stato` **non** contano più la riga fra le approvate né fra le non emesse (G6, changeset D3) |

> A5, A6 e A8 sono quelli che contano davvero: verificano l'effetto *voluto* —
> la riga fuori dalla fattura e fuori dal cockpit — non solo che la colonna sia
> cambiata. **A8 in particolare** batte la strada dell'emissione mirata per
> gruppo fatturabile (`fn_select_attivita_fatturabili` con `p_gruppi`), arrivata
> il 2026-07-27 e quindi mai incrociata con `ANNULLATA`: tutti gli oneri di una
> commessa formano **un solo** gruppo `MAN:<commessa_id>`, ed è lì che si vede
> se annullarli lo svuota davvero.

Una sola garanzia va riscritta, perché così com'è non si può verificare:

> ⚠️ **A7 non è testabile come scritta (rev. 2026-07-28, G7)**: nulla può far
> fallire spontaneamente quell'INSERT. Due opzioni oneste — toglierla
> (l'atomicità è strutturale: una madre unica, una sola `SELECT`), oppure
> provarla con **fault injection**. Si sceglie la seconda: dentro il `BEGIN` del
> pgTAP si crea un trigger `BEFORE INSERT` temporaneo su
> `commesse_attivita_log` che solleva, si verifica che lo stato della riga sia
> rimasto `NON_EMESSA`, e si fa `DROP`. Costa poche righe ed è l'**unico** test
> che dimostra la tesi «madre DB» invece di darla per buona.

---

## 5. [BE] Endpoint

Da fare **dopo** §4.

- `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/annulla/`
- Body: `{ "motivo": "<testo>" }` · `Idempotency-Key` obbligatoria
- `post_permission = "carica_voce_manuale"` — **decisione Tid**: chi può
  caricare una voce manuale può annullarla, nessun permesso dedicato
- Il service **rilegge la riga** e applica i guard di §4b prima di chiamare
  la madre: la difesa DB resta l'ultima parola, ma l'errore deve arrivare al
  client come 4xx parlante, non come traduzione di un `RAISE`
- Mapping dei **quattro** codici in `error_policies.py` (409 per stato
  incoerente — incluso `GIA_ANNULLATA` —, 400 per motivo mancante)

### 5-bis. Tre correzioni dalla verifica del 2026-07-28

Emerse leggendo il BE vivo. **Nessuna** è lavoro DB: sono per la sessione
`dev/backend-tid`.

1. **G3 — §5 oggi non è implementabile.** Il lettore che tutte e tre le azioni
   prezzo usano, `CommesseRepository.get_attivita_pricing`, restituisce 21
   colonne e **non** espone `stato_emissione`, `sorgente_tipo_id` né
   `tipo_movimento`: il service non può distinguere una riga manuale da una da
   push. Vanno aggiunte le tre colonne a quella `SELECT` — sono su `ca`, zero
   costo di join. Precedente identico: è ciò che è stato fatto per `fatturata`
   (changeset `20260724-07`), citato da §6.
2. **G4 — lo scoping riga↔commessa va scritto, non sottinteso.** L'endpoint è
   annidato sotto `commessa_id` ma la madre prende solo `attivita_id`: senza
   controllo l'id nell'URL è decorativo e si annulla la riga di un altro cliente
   indovinando un intero. **La RLS non copre il buco**: la policy
   `rls_commesse_attivita_ef_whitelist` è `ENABLE ... NO FORCE` e l'app gira
   come owner, quindi oggi la bypassa. Rimedio a costo zero: riusare
   `_get_attivita_pricing_or_raise(commessa_id, attivita_id)`, la cui `WHERE`
   ha già entrambi.
3. **G5 — guard «commessa modificabile» (decisione Tid: sì, lato BE).** Le tre
   azioni sorelle chiamano tutte `_assert_commessa_modificabile` (data-driven su
   `stati_commessa.modificabile`), e il FE gatea il kebab su
   `capabilities.can_edit_righe` per lo stesso motivo. Annullare una riga *è*
   modificare la commessa. Resta nel BE e **non** scende nella madre: il gemello
   `fn_aggiungi_onere_commessa` non fa quel lookup, e non si apre qui una
   dipendenza che la porta non ha.

---

## 6. [FE] Azione nel drawer commessa

- Voce **«Annulla riga»** nel kebab delle righe di `CommessaGestioneDrawer`,
  visibile **solo** su righe manuali non emesse (`sorgente_tipo_id === null &&
  stato_emissione === 'NON_EMESSA'`) e con permesso `carica_voce_manuale`
- Dialog di conferma con **motivo obbligatorio** — stesso pattern della
  variazione prezzo eccezionale
- Al successo: refresh della lista righe e dei contatori di testata

✅ **Verificato (2026-07-28)**: la proiezione delle righe
(`CommesseRepository._ATTIVITA_COLS`, alimentata da `fn_list_commessa_attivita`)
espone **già** sia `sorgente_tipo_id` sia `stato_emissione`. Il gate FE è
scrivibile senza toccare la query né la funzione DB — nessuna dipendenza extra.

Precedente utile: la colonna `fatturata` è stata aggiunta a quella stessa
proiezione (`20260724-07`) proprio per far specchiare al FE un guard del BE
(`_assert_non_fatturata`). Qui la simmetria c'è già.

### 6-bis. Due correzioni dalla verifica del 2026-07-28

Anche queste per la sessione `dev/backend-tid`, non per il DB.

1. **G10 — dov'è messa, l'azione non si vedrebbe.** `buildRowActions` fa un
   **early-return `[]`** se manca `canPrezzo` (`prezzo_override_manuale`), se
   manca `can_edit_righe` o se `row.fatturata`. Infilarci «Annulla riga» la
   renderebbe invisibile a chi ha `carica_voce_manuale` ma non il permesso
   prezzo — cioè **esattamente** il destinatario deciso da Tid. La funzione va
   ristrutturata: array unico, gate spostati dal preambolo alle singole voci via
   `visible`.
2. **G8 — la label va disambiguata.** «Annulla riga» finirebbe nel kebab a due
   centimetri da «Annulla commessa» della barra azioni, che fa una cosa
   irreversibile e di tutt'altra portata. Serve un testo che non si possa
   confondere a colpo d'occhio.

✅ **In compenso, il FE è già pronto per lo stato**: `STATO_EMISSIONE_ATTIVITA_MAP`
in `frontend/src/core/utils/severity.js` mappa già `ANNULLATA: 'danger'`, e la
colonna `stato_emissione` è già a video nella tabella righe del drawer. La riga
annullata si vede come tag rosso **senza toccare nulla**.

---

## 7. Cosa NON è in questo brief

- **Righe da push**: restano non annullabili. Il fatto viene dal documento e il
  rimedio sta a monte (sul documento). Ammetterlo qui aprirebbe un secondo
  percorso per disfare ciò che un documento ha dichiarato.
- **Righe già emesse o fatturate**: la risposta corretta è la nota di credito,
  che è un atto fiscale con un suo perimetro.
- **Riapertura di una riga annullata**: nessun «ripristina». Se serve, si
  ricarica l'onere — che è esattamente il libro giornale.
- **Onere di storno negativo**: resta vietato (§2). Questo brief lo rende non
  necessario per il caso «errore di caricamento».

---

## 8. Registro

### 2026-07-28 · Analisi e decisioni

Emerso validando in-app la porta oneri, subito dopo la correzione di un 500
(`AttributeError` su `stato.billing_account_id`, TypedDict letto come oggetto).
Verificate una per una le vie di uscita esistenti (§2) e le quattro porte verso
la fattura (§3).

**Decisioni Tid**: perimetro = righe **manuali non emesse** · permesso =
**riuso** di `carica_voce_manuale` · motivo obbligatorio e tracciato.

**Scoperta che ha cambiato il piano**: si pensava servisse una colonna `attivo`.
Non serve — `stato_emissione = 'ANNULLATA'` esiste già ed è già escluso da tutte
e quattro le porte. Il lavoro DB scende da «colonna + backfill + 4 filtri» a
**una funzione madre**.

### 2026-07-28 · Analisi critica e piano

Verifica del brief contro il codice vivo (doc auto-gen `dbzero`, migrations, BE,
FE). L'impianto regge e §3 era anzi **prudente**: tre porte in più già chiuse
(§3-bis), e i due trigger `BEFORE UPDATE` della tabella non si oppongono
all'UPDATE (§4b). Dieci rilievi, di cui tre sostanziali:

| # | Rilievo | Dove |
|---|---|---|
| G1 | Riannullare cadeva su `GIA_EMESSA` → messaggio **falso**. Quarto codice | §4b, §4d |
| G2 | `RETURNS boolean` non porta informazione → `bigint` | §4a |
| G3 | §5 non implementabile: `get_attivita_pricing` non espone i campi dei guard | §5-bis |
| G4 | Scoping riga↔commessa non citato; la RLS è `NO FORCE` e non copre | §5-bis |
| G5 | Mancava il guard «commessa modificabile» | §5-bis |
| G6 | Contatori di testata ciechi all'annullamento | §3-ter |
| G7 | A7 non testabile come scritta → fault injection | §4e |
| G8 | Nome funzione e label confondibili con l'annullamento **commessa** | §4, §6-bis |
| G9 | §4c raccontava solo il lato buono del criterio sourceless | §4c |
| G10 | L'azione nel kebab sarebbe invisibile al suo destinatario | §6-bis |

**Decisioni Tid**: contatori corretti (G6, changeset D3) · funzione
`fn_annulla_commessa_attivita` (G8) · guard «modificabile» nel BE, non nella
madre (G5).

**Perimetro di questa sessione**: **solo DB** (`dev/db-tid`). §5-bis e §6-bis
sono rilievi consegnati alla sessione `dev/backend-tid`, non lavoro di qui.

---

## 9. [DB] Piano operativo — `dev/db-tid`

> Numerazione: al 2026-07-28 il massimo occupato è `20260728-18` → si parte da
> **`-19`**, sequenza **globale per data** fra tutte le cartelle
> ([[feedback_liquibase_numerazione_globale_per_data]]). **Da riverificare al
> momento della scrittura**: il branch è vivo.

| # | Artefatto | Stato | Contenuto |
|---|---|---|---|
| **D1** | `80_data/sql/config/messaggi_errore.csv` | ✅ applicato | Append ids **564-567**. Nessun loader nuovo — i `runOnChange` esistenti ripescano il CSV |
| **D2** | `20_code/vendite/20260728-19-create-fn-annulla-commessa-attivita-mctit.yaml` | ✅ applicato | La madre di §4a/§4b. `RETURNS bigint`, `SECURITY INVOKER`, `SELECT … FOR UPDATE` sulla riga |
| **D3** | `20_code/vendite/20260728-20-update-fn-get-commessa-stato-esclude-annullate-mctit.yaml` | ✅ applicato | §3-ter. Corpo dalla doc auto-gen, non dallo YAML ([[feedback_docs_first]]) |
| **D4** | `db/pgtap/vendite/test-annulla-commessa-attivita-v1.sql` | ✅ **verde** | `plan(27)`, A1-A9 di §4e |
| **D5** | `docs/it/dbzero/vendite/manual/fn_annulla_commessa_attivita.md` | ✅ scritto | Doc **manuale**. La auto-gen la rigenera Tid dopo il migrate |

> **Il `-20` non può aver regredito nulla.** Cambia la semantica di quattro
> contatori, e quattro pgTAP esistenti li asseriscono
> (`test-commesse-stati-commessa`, `test-guard-uscita-commessa`,
> `test-commesse-core-functions`, `test-emissione-mirata-gruppi-fatturabili`).
> Nessuno di loro crea righe `ANNULLATA` — non poteva, prima che la madre
> esistesse — quindi i nuovi filtri sono **no-op** per le loro fixture.

**Decisioni prese scrivendo, oltre a quelle di §8**

- **`SELECT … FOR UPDATE` sulla riga** (non previsto dal brief). Senza, due
  annullamenti simultanei leggono entrambi `NON_EMESSA` e scrivono **due
  eventi di log** per un solo annullamento; e un'emissione concorrente
  (`fn_emit` fa `UPDATE … SET stato_emissione = 'EMESSA'`) darebbe esito non
  deterministico. Lock su una sola risorsa → nessun deadlock incrociato con
  `fn_emit`, che blocca `attivita_fatturabili`.
- **Guard «non emessa» scritto `<> 'NON_EMESSA'`** e non `= 'EMESSA'`: se
  domani il `CHECK` ammettesse un quarto stato, il default resta il rifiuto.
- **`total_non_approvate` e `total_prezzo_da_riallineare` allineati** in D3,
  non solo i due contatori nominati in §3-ter: una riga annullata rimasta in
  `BOZZA` continuerebbe a chiedere un'approvazione che non serve più, e un
  alert di riallineamento prezzo su una riga fuori dal giro non è azionabile.
- **A7 con `ALTER TABLE … ADD CONSTRAINT … NOT VALID`** invece di un trigger
  temporaneo: nessuna funzione da creare, e `NOT VALID` è necessario perché in
  quel punto della transazione esiste già un evento `RIGA_MANUALE_ANNULLATA`
  (la riga A) che la validazione respingerebbe.

**Restano da fare**

1. **`make db-migrate`** — non eseguito: serve «procedi» esplicito
   (AGENTS.md, Workflow Safety).
2. `scripts/testpgtap.sh db/pgtap/vendite/test-annulla-commessa-attivita-v1.sql`
   → deve diventare verde.
3. `scripts/pgtap-baseline.sh vendite` per distinguere una regressione vera dai
   rossi già noti.
4. Doc auto-gen `dbzero` rigenerata da Tid.
5. Commit — **nessun commit autonomo** ([[feedback_no_commit_autonomo]]).

**Attenzioni specifiche**

- `runOnChange: false` nello stato committato di D2/D3
  ([[feedback_runonchange_false_in_finale]]).
- D3 è un `CREATE OR REPLACE` che **non** cambia la `RETURNS TABLE`: nessun
  `DROP FUNCTION` necessario. Se la si toccasse, servirebbe
  ([[feedback_pg_returns_table_drop_required]]).
- Il corpo di D3 va copiato dalla doc auto-gen di `fn_get_commessa_stato`, mai
  ricostruito dagli YAML: la funzione è stata revisionata il 2026-07-24.
- D4 gira in `BEGIN;` senza commit; il trigger di fault injection di A7 va
  creato **e droppato** dentro la stessa transazione.

**Cosa NON tocca questo piano**: `attivita_fatturabili` (per una riga
`NON_EMESSA` non ne esiste nessuna), i filtri delle cinque porte (già corretti),
lo schema (nessuna colonna nuova), i vocabolari (`evento` non ha CHECK).
