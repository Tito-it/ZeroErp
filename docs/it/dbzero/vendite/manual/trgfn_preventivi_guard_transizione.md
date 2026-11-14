## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_guard_transizione()`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> • [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi)
>
Approfondimento funzioni:
> • [vendite.trgfn_preventivi_guard_annullamento](/dbzero/vendite/funzioni/trgfn_preventivi_guard_annullamento)
> • [vendite.fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo)
>
Pattern correlato (domini gemelli):
> • [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)

---
### 🎯 Scopo Principale

**Enforcement DB-first del grafo transizioni del preventivo.** Una transizione
`OLD.stato → NEW.stato` è ammessa solo se presente e **attiva** in
`config.transizioni_stati_preventivi`.

Il grafo non è hardcodato: viene letto dalla matrice, la **stessa** che alimenta
`fn_available_actions_preventivo`. Da qui la proprietà che conta davvero — la UI non può
proporre ciò che il database rifiuta, né il contrario. Un solo dato, due consumatori.

Porta il preventivo in linea con ordine, DDT, commessa, reso, contratto e offerta, che
avevano già il loro guard di transizione.

---

### Aggancio

Trigger `trg_preventivi_a10_guard_transizione_upd` — fase `_a10_`,
`BEFORE UPDATE OF stato_doc_preventivo_id` su `vendite.preventivi`, `FOR EACH ROW`.

Intercetta **ogni** chiamante — la porta `fn_cambia_stato_preventivo`, gli handler
applicativi, un `UPDATE` diretto: nessuna strada può forzare una transizione illegale.

---

### Regole applicate

Ogni regola legge il **significato** della destinazione dal vocabolario
`config.stati_doc_preventivi` (le colonne `emissione` e `accettazione`), mai il codice: i
`codice_interno` dei due stati servono solo al contesto dell'errore.

1. **No-op** se `stato_doc_preventivo_id` non è distinto dal precedente (`UPDATE` su altre
   colonne dello stesso set).
2. **Regola 1** — la coppia `(stato_da, stato_a)` deve esistere in
   `config.transizioni_stati_preventivi` con `attivo IS TRUE`.
3. **Regola 2** — verso lo **stato di emissione** (`script.fn_stato_emissione_id`): almeno una
   riga attiva (conta la presenza: un totale zero si emette), poi il primo motivo di
   [script.fn_check_preventivo_emettibile](/dbzero/script/funzioni/fn_check_preventivo_emettibile):
   la validità finita, una riga con un prezzo senza aliquota, gli indirizzi, i **prezzi non
   autorizzati**.
4. **Regola 3** — verso lo **stato di accettazione** (`script.fn_stato_accettazione_id`): il
   primo motivo di
   [script.fn_check_preventivo_accettabile](/dbzero/script/funzioni/fn_check_preventivo_accettabile)
   con `NEW.validita_al`: la validità finita (senza aspettare il job delle scadenze), poi i
   prezzi non autorizzati. Un preventivo con un prezzo che nessuno ha autorizzato non diventa
   un impegno. La data entra da `NEW` perché il trigger è `BEFORE ROW`.

⭐ Le regole 2 e 3 stanno sulla **destinazione**, non su una coppia cablata: una strada nuova
verso lo stato di emissione o di accettazione nasce già coperta, e spostare la marca nel
vocabolario sposta la regola con lei. La capability
`fn_available_actions_preventivo` legge le **stesse** funzioni, sulla **stessa** marca, per
spegnere «Emetti» e «Accetta»: il pulsante e il guard non possono dissentire. «Annulla» non
le legge: resta sempre acceso.

---

### ⭐ Il trigger del prezzo che non c'è più (ritirato il 2026-09-24)

Fino al 2026-09-24 il prezzo in approvazione lo guardava un trigger suo,
`trg_preventivi_a10_guard_transizione_approvazione_upd`
(`vendite.trgfn_preventivi_guard_transizione_approvazione`, nato con lo Sprint E dei
listini v5, §14.6). È stato **riassorbito dalla Regola 3** (`20260924-24`), perché era una
seconda copia di una regola che ora sta in un posto solo — e una copia diversa:

| | Trigger a10 (ritirato) | Oggi |
| --- | --- | --- |
| Prezzo **rifiutato** | passava | blocca (D-1) |
| Emissione con un prezzo in attesa | passava | blocca (D-2) |
| Righe e componenti **disattivati** | contavano | non contano |
| Codice | `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` (ritirato) | `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO` |

L'idea di fondo non è cambiata: un preventivo accettato è un impegno verso il cliente, e non
si prende con un prezzo che nessuno ha autorizzato. Cambia che vale anche per l'emissione,
anche per il rifiuto, e che la stessa regola vale per tutti i documenti di vendita.

---

### ⚠️ Che cosa **non** fa, per scelta

* **Non valuta l'ammissibilità dell'annullamento.** Quella ha il suo guard dedicato,
  `trgfn_preventivi_guard_annullamento`. Qui si verifica che la strada *esista*, non che sia
  *percorribile*.

---

### ⚠️ Chi parla per primo: l'ordine alfabetico decide l'errore

Su `vendite.preventivi` convivono due guard `BEFORE UPDATE` legati allo stato, e i trigger
`BEFORE ROW` scattano in **ordine alfabetico**:

1. `trg_preventivi_a10_guard_annullamento_upd`
2. `trg_preventivi_a10_guard_transizione_upd` ← **questo, per ultimo**

(Fino al 2026-09-24 in mezzo c'era anche `trg_preventivi_a10_guard_transizione_approvazione_upd`,
ritirato: sopra.)

Conseguenza pratica: se si tenta di annullare un preventivo che ha già figli a valle **e** la
transizione verso lo stato di annullo non fosse in matrice, l'errore che arriva all'utente è quello
dell'**annullabilità**, non `E_PREV_TRANSIZIONE_NON_AMMESSA`. Questo guard non viene neppure
raggiunto.

Da tenere presente scrivendo i pgTAP: un test che si aspetta il codice della transizione va
costruito su un caso che l'altro guard lascia passare.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PREV_TRANSIZIONE_NON_AMMESSA` | Coppia `(stato_da, stato_a)` assente o non attiva in `config.transizioni_stati_preventivi` |
| `E_PREV_NESSUNA_RIGA_ATTIVA` | Regola 2: verso lo stato di emissione, nessuna riga attiva |
| `E_PREV_EMISSIONE_VALIDITA_SCADUTA` | Regola 2: verso lo stato di emissione, la validità è finita |
| `E_PREV_RIGA_IVA_MANCANTE` | Regola 2: una riga con un prezzo senza aliquota |
| `E_PREV_VALIDITA_SCADUTA` | Regola 3: verso lo stato di accettazione, la validità è finita |
| `E_DOC_PREZZO_PENDENTE` | Regole 2 e 3: prezzi in attesa di approvazione |
| `E_DOC_PREZZO_RIFIUTATO` | Regole 2 e 3: prezzi rifiutati dal responsabile |

I motivi della Regola 2 arrivano da `fn_check_preventivo_emettibile`, che compone anche
`script.fn_check_indirizzi_documento_cliente`: l'elenco completo è nella sua pagina.

Sollevato via `script.fn_log_and_raise_error` con `NEW.tx_id` propagato; il context riporta
`preventivo_id`, `numero`, `stato_da` e `stato_a` in codici interni leggibili.

---

{% include-markdown "signature-core.md" %}
