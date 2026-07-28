# Brief — Annullamento di una riga manuale di commessa

> **Tipo**: brief misto — **§4 al team DB** (`dev/db-tid`), §5-§6 BE/FE
> (`dev/backend-tid`) · **Data**: 2026-07-28 · **Owner**: Tid ·
> **Stato**: ⬜ **DA FARE** — §4 (madre DB) è **prerequisito** di §5
> ([[feedback_be_fe_attende_prerequisiti_db]]) ·
> **Priorità**: 🟠 MEDIA (buco operativo reale, nessun dato a rischio)
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

> **Conseguenza**: niente colonna nuova, niente migration di schema, nessun
> cambio ai filtri. Manca solo **il modo di impostare quel valore**.

---

## 4. [DB] Cosa serve — funzione madre `fn_annulla_riga_manuale_commessa`

⚠️ **Prerequisito di §5.** Sono **due scritture** (UPDATE dello stato + INSERT
dell'evento di log): la regola di casa preferisce una madre DB a un
`transaction.atomic()` lato Python ([api.md §Atomicità](../api.md)), e il
gemello `fn_aggiungi_onere_commessa` è già costruito così.

### 4a. Firma proposta

```sql
vendite.fn_annulla_riga_manuale_commessa(
    p_commessa_attivita_id bigint,
    p_motivo               text
) RETURNS boolean
```

### 4b. Cosa deve fare

1. **Guard parametri** (AGENTS.md): `p_commessa_attivita_id` NULL o `<= 0` →
   errore parlante; `p_motivo` obbligatorio, non vuoto dopo `btrim`.
2. **Caricare la riga** — inesistente → errore dedicato.
3. **Guard «è manuale»**: `sorgente_tipo_id IS NULL`. Vedi §4c: è il
   discriminante, e non è negoziabile.
4. **Guard «non emessa»**: `stato_emissione = 'NON_EMESSA'`. Una riga già emessa
   ha generato un'AF: annullare la riga di commessa **non la toglierebbe dalla
   catena**, lascerebbe un'AF orfana. Errore distinto dal precedente.
5. `UPDATE … SET stato_emissione = 'ANNULLATA'`.
6. **INSERT in `commesse_attivita_log`** — evento `RIGA_MANUALE_ANNULLATA`,
   `dettaglio` con `motivo`, `stato_precedente`, `prezzo_snapshot`,
   `tipo_movimento`. `tx_id` e audit li mettono i trigger della tabella.

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

Vantaggio pratico: se domani nasce un altro tipo di riga manuale,
l'annullamento la copre **senza toccare nulla**.

> ⚠️ **Cautela onesta**: `fn_upsert_commessa_attivita` ha
> `p_sorgente_tipo_id DEFAULT NULL`, quindi «sourceless» è garantito dalla
> disciplina di chi chiama, non dalla struttura. Nella pratica il push passa
> sempre la sorgente — è così che nascono i `segment_key` `ORD:`/`CTR:`/`DDT:` —
> ma il guard di §4b.3 resta necessario e **non va dato per implicito**.

### 4d. Codici errore (nuovi, da aggiungere al CSV messaggi)

| Codice | Quando |
|---|---|
| `E_RIGA_COMMESSA_NON_MANUALE` | la riga ha una sorgente: nasce da un documento, il rimedio è a monte |
| `E_RIGA_COMMESSA_GIA_EMESSA` | `stato_emissione <> 'NON_EMESSA'`: è entrata nella catena di fatturazione |
| `E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO` | motivo assente o vuoto |

Due errori **distinti** e non uno generico: le due cause portano l'operatore a
due azioni diverse, e un messaggio unico lo lascerebbe a indovinare.

### 4e. Garanzie DB (da coprire con pgTAP)

| # | Deve essere vero |
|---|---|
| A1 | Riga manuale NON_EMESSA → passa a `ANNULLATA` e l'evento è scritto nel log |
| A2 | Riga **con sorgente** → respinta con `E_RIGA_COMMESSA_NON_MANUALE`, stato invariato |
| A3 | Riga **già EMESSA** → respinta con `E_RIGA_COMMESSA_GIA_EMESSA`, stato invariato |
| A4 | Motivo vuoto/assente → respinta, nessuna scrittura |
| A5 | Dopo l'annullamento, `fn_emit_attivita_fatturabili_da_commessa` sulla stessa commessa **non produce AF** per quella riga |
| A6 | Dopo l'annullamento la riga **non compare** in `vw_dash_competenza_attivita` né in `vw_dash_competenza_gruppi` |
| A7 | L'operazione è **atomica**: se l'INSERT del log fallisce, lo stato non cambia |

> A5 e A6 sono i due che contano davvero: verificano l'effetto *voluto* — la
> riga fuori dalla fattura e fuori dal cockpit — non solo che la colonna sia
> cambiata.

---

## 5. [BE] Endpoint

Da fare **dopo** §4.

- `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/annulla/`
- Body: `{ "motivo": "<testo>" }` · `Idempotency-Key` obbligatoria
- `post_permission = "carica_voce_manuale"` — **decisione Tid**: chi può
  caricare una voce manuale può annullarla, nessun permesso dedicato
- Il service **rilegge la riga** e applica i guard di §4b.3/4 prima di chiamare
  la madre: la difesa DB resta l'ultima parola, ma l'errore deve arrivare al
  client come 4xx parlante, non come traduzione di un `RAISE`
- Mapping dei tre codici in `error_policies.py` (409 per stato incoerente, 400
  per motivo mancante)

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
