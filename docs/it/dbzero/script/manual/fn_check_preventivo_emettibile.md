## 📘 Documentazione Concettuale – Funzione `script.fn_check_preventivo_emettibile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> • [vendite.preventivi_riepiloghi_iva](/dbzero/vendite/tabelle/preventivi_riepiloghi_iva)
>
Approfondimento funzioni:
> • [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile) — la gemella, stessa forma
> • [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — il building block del MOTIVO 2, i prezzi non autorizzati (dal 2026-09-24)
> • [script.fn_check_ordine_confermabile](/dbzero/script/funzioni/fn_check_ordine_confermabile) — lo stesso cancello sull'ordine
> • [vendite.fn_ricalcola_riepilogo_iva_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_preventivo) — il **consumatore** da cui è copiato il perimetro
> • [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione) — chi solleva
> • [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) — chi spegne il bottone

---

### 🎯 Scopo Principale

(rev 2026-10-31 — MOTIVO 4, la validità già finita; rev 2026-09-24 — MOTIVO 2, i prezzi
non autorizzati; funzione nata il 2026-08-29)

Elenca i motivi che impediscono di **emettere** un preventivo. Oggi ne ha quattro, in
quest'ordine:

1. una riga attiva, con quantità e prezzo, che non porta l'aliquota;
2. un prezzo che nessuno ha autorizzato — in attesa di approvazione o rifiutato — su una
   riga o un componente BoM attivi (rev 2026-09-24, vedi la sezione in fondo);
3. un indirizzo d'anagrafica che non è del cliente del preventivo (rev 2026-10-11);
4. la validità già finita: «Valido al» è prima di oggi (rev 2026-10-31,
   `E_PREV_EMISSIONE_VALIDITA_SCADUTA`, col campo `validita_al`). Un preventivo emesso così
   arriverebbe al cliente scaduto: non potrebbe accettarlo, e il job delle scadenze lo
   chiuderebbe la notte dopo. In bozza la data si corregge. Lo stesso confronto
   dell'accettazione e del job: «Valido al» è l'ultimo giorno valido, e senza data il
   preventivo non scade. Brief `brief-db-scadenza-preventivi` (E-4 di Tid).

Terzo gemello del cancello «una riga valorizzata porta l'aliquota», dopo il DDT
(2026-08-28) e l'ordine (2026-08-29).

---

### ⭐ Il perimetro è **copiato dal consumatore**, non inventato

`vendite.fn_ricalcola_riepilogo_iva_preventivo` aggrega le righe con
`attivo IS TRUE AND quantita > 0` e calcola l'imposta con
`COALESCE(config.fn_get_aliquota_iva(iva_id, stato), 0)`: una riga senza aliquota finisce in
`vendite.preventivi_riepiloghi_iva` con **imponibile pieno e imposta zero**.

Questa funzione usa lo **stesso identico predicato**, più `iva_id IS NULL`.

⚠️ È la lezione del gate DDT: *il vincolo deve avere lo stesso perimetro del consumatore che
protegge* — né più largo, che bloccherebbe documenti sani, né più stretto, che lascerebbe
passare il difetto.

---

### 🔴 Sul preventivo il difetto **non era silenzioso** — e questa è la storia da conoscere

Fino al 2026-08-29 una riga di preventivo senza aliquota **non si riusciva nemmeno a
salvare**: il trigger `AFTER` `trg_preventivi_righe_z90_ricalcola_totali` chiama il
ricalcolo, che chiamava `config.fn_get_aliquota_iva(NULL, …)` — e quella funzione **solleva**
invece di ritornare `NULL`. L'`INSERT` moriva con *«Parametro non valido: p_iva_id
obbligatorio e > 0»*.

⚠️ **Il `COALESCE` che sembrava una guardia non lo era**: per proteggere avrebbe dovuto
ricevere un `NULL`, e il `NULL` non arrivava mai perché la funzione solleva prima.

⛔ **E non era una decisione di dominio: era una svista.** Le viste gemelle la guardia ce
l'hanno — `vw_ordini_righe_iva_base` scrive
`CASE WHEN r.iva_id IS NOT NULL THEN config.fn_get_aliquota_iva(…)` — solo quel ricalcolo no.
Il comportamento divergeva da DDT e ordini su tre punti, tutti contrari a come il progetto ha
deciso di funzionare: il vincolo scattava **in bozza al salvataggio**, il messaggio **nominava
un parametro PL/pgSQL** a un operatore, e l'errore arrivava da una funzione di catalogo **tre
livelli sotto** l'azione.

⭐ La guardia (`20260829-12`) e questo cancello (`20260829-10`) sono **una slice sola**: la
guardia da sola aprirebbe la strada a una riga senza aliquota, che finirebbe nel riepilogo
con imposta zero. Questo è la rete.

⚠️ **La gemella sulle FATTURE ha lo stesso `COALESCE` senza guardia e NON è stata toccata**:
lì non esiste ancora un cancello IVA all'emissione, e togliere il raise scambierebbe un
errore rumoroso con un numero sbagliato silenzioso. Va fatto insieme a `I4`.

---

### ⚠️ Tre differenze con la gemella sull'ordine — **non è una copia**

Copiare la funzione degli ordini avrebbe prodotto un guard sbagliato. I due documenti
divergono su tre punti **strutturali**:

| | `vendite.ordini_righe` | `vendite.preventivi_righe` |
|---|---|---|
| numero di riga | `riga_nr` | ⛔ **non esiste**; c'è `ordine smallint DEFAULT 0`, che è una chiave di ordinamento |
| `quantita` | `NOT NULL` + `CHECK (quantita > 0)` | **nullable, senza CHECK** |
| `attivo` | `NOT NULL` | **nullable** (default `true`) |

Ne discende che:

* ⛔ **nel messaggio va la DESCRIZIONE, non un numero.** Se `ordine` non lo valorizza
  nessuno vale `0` su tutte le righe, e un messaggio che dicesse «la riga 0» non aiuterebbe
  nessuno. L'id resta nel contesto, per chi diagnostica;
* ⚠️ **`quantita > 0` qui serve davvero.** Sugli ordini sarebbe ridondante (lo garantisce
  `chk_ordini_v_r_qta_pos`); qui, senza, si **bloccherebbe un preventivo sano** per una riga
  che nel riepilogo non entra mai;
* ⚠️ **`attivo IS TRUE` e non `attivo`**: la colonna è nullable, e il `NULL` va escluso
  esattamente come lo esclude il consumatore.

⭐ È il caso da tenere a mente quando due documenti «fanno la stessa cosa»: la simmetria si
verifica sulla struttura, non si deduce dal nome.

---

### ⚠️ Il perimetro è **qualunque** ingresso in `EMESSO`

Il guard chiama questa funzione su `v_codice_a = 'EMESSO'`, non sulla coppia
`DRAFT → EMESSO`. Al 2026-08-29 la matrice ne ammette una sola, ma è una lettura del **seed**:
il predicato sta sulla destinazione, così una strada nuova verso `EMESSO` nasce già coperta.

---

### ⭐ Nel trigger, e non nella porta

Il commento del corpo di `trgfn_preventivi_guard_transizione` dichiara che la regola
«documento senza righe» vive nella porta `vendite.fn_cambia_stato_preventivo` e che **un
`UPDATE` diretto la aggira** — *«un'asimmetria dichiarata, non una dimenticanza»*.

⚠️ Quella è la descrizione di una **debolezza**, non un modello da imitare: una regola che
protegge un numero fiscale non può dipendere da quale porta ha usato il chiamante. Il DDT e
l'ordine la mettono nel trigger, e qui si fa lo stesso.

⛔ **Non è un `NOT NULL` di colonna**: `preventivi_righe.iva_id` è nullable e la bozza deve
restare libera.

---

### Codici errore

| Codice | Motivo |
|--------|--------|
| `E_PREV_RIGA_IVA_MANCANTE` | Una riga attiva con quantità e prezzo non porta l'aliquota (`CONFLITTO_STATO`, 409) |
| `E_DOC_PREZZO_PENDENTE` | Una riga o un componente attivi hanno il prezzo in attesa di approvazione (`CONFLITTO_STATO`, 409) — dal building block, rev 2026-09-24 |
| `E_DOC_PREZZO_RIFIUTATO` | Una riga o un componente attivi hanno il prezzo rifiutato (`CONFLITTO_STATO`, 409) — dal building block, rev 2026-09-24 |
| `E_PARAMETRO_INVALIDO` | `preventivo_id` nullo o non positivo |

⚠️ Nel contesto **non** va la chiave `campo`: la richiesta è «porta il preventivo a
`EMESSO`», e non c'è un campo di *quella* richiesta da accendere.

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}`; chi solleva prende il **primo**.

⭐ **Sorgente unica** per il guard (che solleva) e per `fn_available_actions_preventivo` (che
spegne il bottone «Emetti» ed espone la `reason`): senza il secondo l'operatore vedrebbe un
pulsante acceso e prenderebbe un errore al click.

⚠️ **Preventivo inesistente ⇒ `[]`**: la funzione non distingue «emettibile» da «non esiste»,
la decisione è del chiamante.

---

### 📌 Debito verso il frontend

La `reason_key` `vendite.preventivi.azione_reason.iva_mancante` **non è ancora nei locales**.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, I9.

Per il MOTIVO 2 valgono le `reason_key` `common.azione_reason.prezzo_pendente` e
`common.azione_reason.prezzo_rifiutato`, già in debito verso i locales nella pagina del
building block.

---

### Rev 2026-09-24 — MOTIVO 2, i prezzi non autorizzati

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*. Un
preventivo con una riga o un componente BoM **attivi** in attesa di approvazione (`PENDING`)
o **rifiutati** (`REJECTED`) non si emette.

La funzione non scrive da sé la domanda: somma ai propri i motivi del building block
[`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati),
la sede unica della regola per tutti i documenti di vendita. Prima l'attesa, poi il rifiuto.

⭐ **Nessun consumatore cambia**: il guard di transizione (Regola 2) e la capability leggono
già questa funzione, quindi bottone «Emetti» e database vedono il motivo nuovo insieme.

Verso `ACCETTATO` gli stessi motivi li chiede direttamente
[`vendite.trgfn_preventivi_guard_transizione`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)
(Regola 3): non esiste una `fn_check_preventivo_accettabile`, e non se ne crea una con un solo
motivo. L'annullamento resta sempre possibile.

(changeSet `20260924-21`, brief `brief-db-preventivi-congelamento-pricing`, D-1 e D-2.)

---

{% include-markdown "signature-core.md" %}
