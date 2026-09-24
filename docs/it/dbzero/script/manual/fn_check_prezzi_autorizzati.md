## 📘 Documentazione Concettuale – Funzione `script.fn_check_prezzi_autorizzati()`

> 👀 **Vedi anche**
>
Chi la chiede, documento per documento:
> • [script.fn_check_preventivo_emettibile](/dbzero/script/funzioni/fn_check_preventivo_emettibile) e [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione) — preventivo, verso `EMESSO` e `ACCETTATO`
> • [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato) — contratto, verso `ATTIVO`
> • [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione) — offerta, verso `EMESSA` e `ACCETTATA`
> • [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — ordine, solo `DRAFT → CONFERMATO`
> • [script.fn_check_ddt_emittibile](/dbzero/script/funzioni/fn_check_ddt_emittibile) — DDT, verso `EMESSO`, solo se la causale vende
>
Chi spegne i pulsanti con gli stessi motivi:
> • [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo), [script.fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto), [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta), [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine), [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)
>
Il guard che resta sulla singola riga:
> • [script.trgfn_righe_guard_pending](/dbzero/script/funzioni/trgfn_righe_guard_pending) — una riga in attesa non si modifica

---

### 🎯 Scopo Principale

(nata il 2026-09-24 — `20260924-20`)

Risponde a **una** domanda: *questo documento di vendita contiene un prezzo che nessuno ha
autorizzato?*

Un prezzo fuori listino chiede un'approvazione: la riga (o il componente di un kit) passa
in **attesa** (`PENDING`), e il responsabile lo **approva** (`APPROVED`) o lo **rifiuta**
(`REJECTED`). Finché il prezzo è in attesa, o se è stato rifiutato, nessuno lo ha
autorizzato: il documento **non esce dalla bozza** e **non diventa un impegno accettato**.
L'annullamento invece resta sempre possibile.

Decisioni di Tid del 2026-09-24 (brief `brief-db-preventivi-congelamento-pricing`):

* **D-1** — il rifiutato blocca come l'in attesa: sono entrambi prezzi non autorizzati;
* **D-2** — blocca l'uscita dalla bozza e l'accettazione, **mai** l'annullamento;
* **D-5** — la regola sta **qui, una volta**, per tutti i documenti;
* **D-6** — ordini e DDT inclusi.

---

### ⛔ Perché esiste: cinque sedi che non dicevano la stessa cosa

Lo stato di approvazione vive su otto tabelle, e fino a questa funzione la domanda era
scritta in cinque posti, ognuno con un pezzo diverso:

| Documento | Cosa controllava prima |
| --- | --- |
| Preventivo | righe e componenti in attesa, **solo** entrando in `ACCETTATO` (trigger a10, ritirato) |
| Contratto | **solo i componenti** in attesa: una riga in attesa passava |
| Offerta | niente |
| Ordine | niente |
| DDT | componenti in attesa, solo se la causale vende |

E il backend spegneva i pulsanti del preventivo con una regola sua, diversa da tutte.
⚠️ **Il rifiutato non lo guardava nessuno**: un prezzo che il responsabile aveva rifiutato
usciva col documento.

---

### ⭐ Il predicato sta qui, la politica nel documento

La funzione dice **cosa** c'è di non autorizzato. **Quando** chiederlo lo decide ciascun
documento, dal suo guard o dalla sua `fn_check_*`:

* il **DDT** lo chiede solo se la causale **vende**: un conto visione non produce valore, e
  un prezzo in attesa non ha niente da dire;
* l'**ordine** lo chiede solo **dalla bozza**: la matrice lo fa rientrare in `CONFERMATO` da
  `EVASO` in automatico quando l'evasione torna indietro, e quel rientro non conferma niente
  di nuovo — bloccarlo fermerebbe un annullamento a valle;
* l'**offerta** non lo chiede sul **rientro da `SUPERATA`** (il padre che torna vivo quando si
  annulla la revisione), per la stessa ragione.

⭐ In ogni documento il guard che solleva e la funzione che spegne il pulsante leggono
**questa** funzione: il pulsante e il database non possono dissentire.

---

### ⚠️ Solo righe e componenti **attivi**

Le righe si cancellano davvero; i componenti si **spengono** (`attivo = false`). Un
componente rifiutato e poi tolto dal documento resta `REJECTED` per sempre: contarlo
bloccherebbe il documento **senza rimedio**. Un componente conta solo se è attivo lui **e**
la sua riga.

⚠️ Il vecchio trigger del preventivo contava anche le righe disattivate: è una differenza
voluta.

---

### Come si indica il documento

Con la sua **tabella di testata**, come `regclass`:

| Testata | Dove sta lo stato del prezzo |
| --- | --- |
| `vendite.preventivi` | righe e componenti |
| `vendite.contratti` | righe e componenti |
| `vendite.offerte_commerciali` | eccezioni e loro componenti |
| `vendite.ordini` | solo componenti |
| `vendite.ddt` | solo componenti |

⭐ Un nome sbagliato fallisce alla conversione a `regclass`, e non serve un vocabolario dei
tipi documento (`config.tipi_entita` non ha offerte né DDT). Una testata che la funzione
non conosce è un **errore** (`E_PARAMETRO_INVALIDO`), non un «niente da dire»: un `[]` farebbe
passare tutto in silenzio.

---

### Cosa restituisce

`[]` se non c'è niente da autorizzare; altrimenti un array **ordinato** di motivi nella forma
di casa `{codice, reason, reason_key, dettaglio, valori}` — prima l'in attesa, poi il
rifiutato:

| Codice | `reason` | `reason_key` |
| --- | --- | --- |
| `E_DOC_PREZZO_PENDENTE` | `PREZZO_PENDENTE` | `common.azione_reason.prezzo_pendente` |
| `E_DOC_PREZZO_RIFIUTATO` | `PREZZO_RIFIUTATO` | `common.azione_reason.prezzo_rifiutato` |

Entrambi `CONFLITTO_STATO` (409): non c'è un campo della richiesta da correggere, quindi nel
contesto non va la chiave `campo`.

* **`valori`** porta il **conteggio**, che è ciò che la frase mostra: *«Il documento non può
  avanzare: ci sono prezzi ancora in attesa di approvazione (2).»*;
* **`dettaglio`** porta `n_prezzi` e la **prima** riga (e componente) a video, per chi
  diagnostica. ⚠️ Nella frase non va una riga: `preventivi_righe` e le eccezioni d'offerta
  non hanno un numero di riga da mostrare.

⚠️ Codici e `reason_key` sono scritti **letterali**, un motivo per blocco, e non in un
`CASE`: `dbops.vw_funzioni_check_codici` e `scripts/check_i18n_keys.py` li riconoscono solo
in quella forma. Scritti in un `CASE`, una chiave assente dai locales passerebbe in silenzio.

---

### 📌 Debito verso il frontend

Le due `reason_key` vanno nei locales (`it.json`/`en.json`): senza, i pulsanti spenti hanno
il tooltip vuoto e `check_i18n_keys.py` fallisce.

---

{% include-markdown "signature-core.md" %}
