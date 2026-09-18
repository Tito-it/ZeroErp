# Brief DB — magazzino, Lotto 2-bis: ciò che il BE/FE del motore chiede al DB

> **Destinatario:** team DB (`dev/db-tid`). **Chi scrive:** BE/FE, 2026-09-18.
> **Origine:** [piano-be-fe-magazzino-lotto-2-motore.md](piano-be-fe-magazzino-lotto-2-motore.md)
> §7 — scrivendo il piano del drawer e delle righe sono emerse **tre** cose che
> il BE non può fare da sé senza riscrivere una regola del DB, più **due**
> difese opzionali. Nessuna ridiscute il Lotto 2: ogni riga cita la decisione
> da cui discende (D-L2-* del [brief del motore](brief-db-magazzino-lotto-2-motore.md)).
> **Stato:** 🔵 da decidere lato DB. ✅ Le cinque domande del piano (Q-1 … Q-5)
> sono decise da Tid il 2026-09-18: qui non resta niente in sospeso lato BE/FE.
> Bloccano parti **diverse** del piano: R-1 il drawer (Pezzo 3), R-2 le righe
> (Pezzo 2), R-3 il gate di «Registra». Tutto il resto del piano procede senza.
>
> **In una riga.** Il Lotto 2 ha messo la matrice degli stati **dentro il
> guard** e nessuna funzione la espone: il drawer, che deve disegnare i pulsanti
> come in tutti gli altri domini (`fn_available_actions_*`), non ha da dove
> leggerla — e il BE non la copia. Poi un `UNIQUE` senza codice, un'azione di
> processo per il verbo irreversibile, e due lucchetti.

---

## R-1 🔴 — la capability dei documenti interni (D-L2-h; linee-guida-sql §12)

**Il fatto.** `trgfn_documento_interno_guard_transizione` porta la matrice in
un `CASE v_old …` nel corpo. Il frontend monta le azioni di stato **solo** da
`available_actions` (`mapAvailableActionsToDrawerActions`, frontend-standards
§Azioni Drawer: *«niente loop manuale»*, *«un `v-if` su `stato_codice` nel
drawer sarebbe la stessa regola scritta due volte»*), e il backend **trasporta,
non deduce** (api.md §Capability). Senza una funzione, le uscite sono due e
sono entrambe una seconda sede della matrice: un `dict` in Python o un
`v-if` in Vue. Il brief del motore lo aveva previsto: *«se un giorno servirà,
la matrice esce dal guard: cambia dove sta, non chi la fa rispettare»*. Il
giorno è il primo drawer.

**Che cosa si chiede.**

1. **La matrice in una sede sola**, letta dal guard e dalla capability:
   `magazzino.fn_documento_interno_transizioni(p_stato_da text) RETURNS text[]`
   (`IMMUTABLE`, `SECURITY INVOKER`) — `DRAFT → {CONFIRM, CANCEL}`, `CONFIRM →
   {POSTED, CANCEL, DRAFT}`, `POSTED`/`CANCEL → {}`. Il guard fa `v_new = ANY(…)`
   al posto del `CASE`; `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` e la porta
   `POSTED` restano dove sono. ⚠️ Non una tabella seed: gli stati non hanno
   attributi (D-L2-h, «matrice nel guard, non tabella»); una funzione è la sede
   più piccola che due lettori possono condividere.
2. **Due capability con lo stampo di `fn_available_actions_ordine`**, in
   `script`, `STABLE SECURITY INVOKER` (sotto RLS: fuori perimetro `{}`, il 404
   lo dà il BE sulla testata): `script.fn_available_actions_inventario(p_id)`
   e `script.fn_available_actions_rettifica(p_id)`. ⭐ Se il corpo è uno
   (`_documento_interno(p_tabella, p_col_stato, p_id)`) le due sono involucri:
   scelta vostra. Il blob:

   | Chiave | Che cosa |
   | --- | --- |
   | `stato_codice` | lo stato |
   | `available_actions[]` | una voce per **transizione richiedibile** dalla matrice (mai `POSTED`, che si chiede con `registra`): `key` (`conferma` / `annulla` / `riapri`), `target_state`, `label_key`, `icon`, `severity`, `requires_confirm` (`true` su `CANCEL`), `enabled`, `reason`, `reason_key`, `manuale = true` |
   | `can_edit_testata`, `can_edit_righe` | `stato = 'DRAFT'` — **lo stesso predicato** del guard delle righe (§12.2: «il predicato è lo STESSO del guard») |
   | `can_delete` | `stato = 'DRAFT'` (C3) |
   | `can_registra`, `can_registra_reason`, `can_registra_reason_key` | la terna di **`registra`** (famiglia 1 di api.md §Capability, come `can_push_commessa`): `enabled` sse `stato = 'CONFIRM'` **e** almeno una riga **e** (solo inventario) nessuna riga `NON_POSTABILE` nel piano — sono le tre condizioni con cui `fn_posta_*` rifiuta (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`, `E_MAG_DOCUMENTO_SENZA_RIGHE`, il primo motivo di `fn_check_riga_magazzino`). Precedenza: stato > righe > postabilità. ⭐ Se preferite che `fn_posta_*` chiami una `script.fn_check_documento_interno_registrabile` e la capability la stessa (§12.5.2, «la madre chiama la check»), è la forma di casa — decidete voi |
   | `stato_info_key` | `POSTED` → `magazzino.documenti_interni.stato_info.posted` («Registrato: i movimenti sono sul registro. Per correggere, una rettifica»); `CANCEL` → `….cancel`; `NULL` altrove (il campo è sempre presente, brief vie d'uscita R3) |

3. **Le chiavi i18n**, da dichiarare qui perché il FE le semini **nello stesso
   giro** (`check_i18n_keys.py` controllo 4 le cerca nella doc auto-gen):
   `label_key` `magazzino.documenti_interni.azione.{conferma, annulla, riapri}`;
   `reason_key` `magazzino.documenti_interni.registra_reason.{non_confermato,
   senza_righe, righe_non_postabili}`; le due `stato_info_key` sopra.

**pgTAP** (stampo dei test delle otto capability): la matrice della funzione
coincide con ciò che il guard ammette e rifiuta (**costruendo** le sei
transizioni, non leggendo dati); `can_registra` spento con la `reason` giusta
nei tre casi e acceso sul caso buono; fuori perimetro `{}`.

---

## R-2 🟠 — `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA` (C14)

`uq_mag_inventari_righe_posizione` (UNIQUE NULLS NOT DISTINCT su
`(inventario, articolo, ubicazione, lotto, asset)`) rifiuta con un `23505` —
e un `23505` il BE lo traduce con `map_integrity_error` in un codice **che
deve essere a catalogo** (guardrail dei codici; oggi nessun `E_MAG_*` lo
nomina). Chi rimedia è chi compila la riga ⇒ `DATO_ERRATO`, `campo =
articolo_id`. Messaggio proposto: *«L'articolo %s è già contato in questa
posizione dell'inventario (%s).»* (codice articolo, posizione: ubicazione ·
lotto · seriale, «—» dove vuota); soluzione: *«Modifica la riga esistente
invece di aggiungerne una seconda.»* ⚠️ Lo solleva **solo il BE** (nessuna
funzione lo nomina): il rubinetto B-7 non lo vede, il registro del terzo lato
lo trova a catalogo con la sua classe. Le rettifiche non lo prendono (C14: due
delta dati non sono due letture).

---

## R-3 🟠 — l'azione di processo `registra_magazzino`

Una riga in `config/azioni_processo.csv`: area **6** (`magazzino`),
`permission_codename = registra_magazzino`, *«Registra inventario o rettifica
di magazzino (crea i movimenti: irreversibile)»*, `pericolosa = t`, `attivo = t`
— lo stampo è `registra_distinta` (id 32). Un'azione per la famiglia, non due:
il verbo è lo stesso e la matrice è la stessa. Il BE la dichiara su
`POST inventari/<id>/registra/` e `rettifiche/<id>/registra/`
(`post_permission`), fail-closed finché un profilo non la porta.

---

## R-4 🟡 (opzionale) — `magazzino_id` si sceglie alla nascita

Il documento è ancorato a **un** magazzino (RLS, ubicazioni delle righe,
`qta_sistema` del piano). Il BE lo esclude dal `PATCH`; la difesa a DB è
`script.trgfn_lock_columns('magazzino_id', …)` su `inventari` e `rettifiche`
(stampo `trg_articoli_a10_protect_uom_id_upd`). Senza, un `UPDATE` diretto
sposta un conteggio su un altro magazzino con le ubicazioni di quello vecchio
— e la primitiva se ne accorgerebbe **solo** al posting
(`E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`). Un lucchetto piccolo che dice la
regola dove sta.

⚠️ **Nota, dalla Q-2 del piano (decisa il 18-09):** il guard di famiglia
copre righe e stato, **non** `data`/`descrizione` della testata, e il BE **non
aggiunge** una regola che il DB non ha (a video il form è readonly fuori da
`DRAFT`; via API un `PATCH` di `data` su un `POSTED` passa). `data` decide
`data_mov` al posting: dopo, una `data` cambiata e i `data_mov` a registro
dicono due cose. Se per voi è un difetto del modello, il congelamento della
testata fuori da `DRAFT`/`CONFIRM` è un lucchetto vostro, nello stesso giro di
R-4; se no, resta com'è.

## R-5 🟡 (opzionale) — `fn_lookup_articoli`: filtro `p_gestito_a_magazzino`

Il picker della riga di inventario propone oggi **tutti** gli articoli; uno non
gestito diventa `NON_POSTABILE` al piano. Un filtro `boolean DEFAULT NULL`
(`NULL` = nessun filtro, come `is_solo_componente`) lascia al FE la scelta di
proporre solo i gestiti. Non blocca niente: senza, l'anteprima dei motivi nel
form (`fn_check_riga_magazzino`) lo dice comunque.

---

## R-6 🟡 (opzionale, 18-09 notte) — `E_MAGAZZINO_VALIDATION`

Il codice di validazione del payload del dominio (`DATO_ERRATO`), gemello di
`E_PAGAMENTI_VALIDATION`: oggi il BE usa il generico `E_VALIDATION_INPUT`, ed è
**una riga** da cambiare (`magazzino_service.E_VALIDAZIONE`). Il BE non conia.

## R-7 🟡 (opzionale, 18-09 notte) — `E_MAG_DOCUMENTO_RIGA_NON_TROVATA`

La coppia (documento, riga) è la risorsa dell'URL
(`inventari/<id>/righe/<rid>/`): una riga di un altro documento «non c'è», e
oggi risponde `E_MAG_DOCUMENTO_NON_TROVATO` con la frase del BE («Riga non
trovata nel documento»). Un codice suo (`NON_TROVATO`) dice *quale* delle due
manca; è un candidato allo split, non un difetto.

---

## Ai team, per chiudere

- 🔵 DB: R-1 (con le chiavi i18n dichiarate), R-2, R-3; R-4/R-5/R-6/R-7 a discrezione.
  In `_dominio-magazzino.md` §«Che cosa manca» la riga di `requires_lotto`
  esce quando il Pezzo 0 del piano è mergiato.
- 🔵 BE/FE: le chiavi di R-1 nei locales **prima** che la doc auto-gen delle
  capability entri nel repo; `genera_error_policies` + ripiego per R-2.
