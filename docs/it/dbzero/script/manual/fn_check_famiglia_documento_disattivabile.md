## 📘 Documentazione Concettuale – Funzione `script.fn_check_famiglia_documento_disattivabile`

> **Ultimo aggiornamento**: 10 novembre 2026
>
> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [vendite.trgfn_famiglie_documento_guard_disattivazione](/dbzero/vendite/manual/trgfn_famiglie_documento_guard_disattivazione) — il guard, che la **chiama** e solleva il primo motivo
> • [vendite.vw_famiglie_documento_lista](/dbzero/vendite/manual/vw_famiglie_documento_lista) — l'elenco, che spegne il cestino e dice **perché**
>
> **Sorgente:**
>
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • le tabelle dei documenti, che **non sono elencate qui**: si leggono dalla famiglia stessa
>
> **Gemelle:**
>
> • [script.fn_check_famiglia_documento_struttura_modificabile](/dbzero/script/manual/fn_check_famiglia_documento_struttura_modificabile) — l'altro divieto sulla stessa riga
> • [anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba) — conta gli stessi documenti, per il presidio che questa funzione difende

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — funzione nata il 2026-09-01)*

**Dice se una famiglia di documento si può spegnere, e quando non si può dice
perché.** Ritorna `[]` se si può, altrimenti l'array **ordinato** dei motivi:
`[{codice, reason, reason_key, dettaglio}, …]`.

---

### ⛔ Che cosa si sta difendendo: non un catalogo, un PRESIDIO

Spegnere una famiglia sembra nascondere una voce da un elenco. Non è così.

Il controllo che risponde *«questo cliente ha già documenti numerati?»* —
`anagrafiche.fn_ba_ha_storia_emittente` e la sua gemella — scorre le famiglie
**attive**. Una famiglia spenta **esce dal giro**, e da quel momento i suoi
documenti smettono di trattenere il cliente presso l'emittente che li ha
numerati.

⚠️ **Nessun errore, nessuna riga di diario**: il controllo guarda semplicemente
in un posto in meno. È il difetto peggiore, perché non si vede.

⭐ Finora non era un rischio: in quella tabella scriveva solo un seed. Dal CRUD
è un clic.

---

### ⭐ Due motivi, e l'ordine non è estetico

| Ordine | `reason` | Predicato | Si può rimediare? |
| --- | --- | --- | --- |
| 1 | `HA_REGISTRI_ATTIVI` | esiste un registro **acceso** su questa famiglia | **sì** — si spengono |
| 2 | `HA_DOCUMENTI_NUMERATI` | esiste un documento che **porta un numero** | **no** — quei numeri sono usciti |

Il guard solleva il **primo** motivo. Va per primo quello su cui l'operatore può
fare qualcosa: dirgli per primo ciò che non può cambiare è una porta chiusa senza
maniglia.

⚠️ Il primo motivo guarda `attivo` e non l'esistenza: un registro spento non
numera più niente, e tenerlo in conto vieterebbe per sempre lo spegnimento di una
famiglia già ritirata.

---

### ⭐ Nessun elenco di tabelle, e il perché

Le tabelle dei documenti **non sono scritte dentro la funzione**: si leggono
dalla famiglia stessa (`schema_tabella`, `nome_tabella`, `colonna_numero`) e si
compongono in SQL dinamico.

⇒ Una famiglia nuova entra nel controllo **il giorno in cui nasce**, senza che
nessuno debba ricordarsi di aggiungerla. È lo stesso principio per cui esiste il
catalogo delle famiglie.

⚠️ Si usa `to_regclass` e non un cast: una famiglia ritirata può nominare una
tabella che non c'è più — è storia — e la verifica deve **rispondere**, non
esplodere.

---

### ⚠️ `SECURITY DEFINER`, e qui è obbligatorio

Le cinque tabelle dei documenti — fatture, ddt, ordini, commesse, resi — hanno la
**RLS attiva** (verificato il 2026-09-01). Un conteggio `SECURITY INVOKER`
tornerebbe **zero** all'operatore che non vede quei documenti, e zero qui
significa *«si può spegnere»*.

⛔ Sarebbe un **fail-open che non fallisce mai**: uno zero sotto RLS non è un
dato, è una risposta troncata. È la stessa scelta già fatta da
`anagrafiche.fn_get_storia_emittente_ba`, che conta gli stessi documenti per lo
stesso genere di presidio.

⭐ La gemella sulla struttura è invece `SECURITY INVOKER`, e non è
un'incoerenza: legge solo due tabelle **senza** RLS. Un privilegio si chiede
quando serve, non per simmetria.

---

### 📤 Cosa torna

| Chiave | Contenuto |
| --- | --- |
| `codice` | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` (registri) / `E_ATTIVO_BLOCK_CHILDREN_EXIST` (documenti) — ⭐ **riusati**, non coniati: sono i codici del guard generico di disattivazione, con la stessa frase |
| `reason` | `HA_REGISTRI_ATTIVI` / `HA_DOCUMENTI_NUMERATI`. ⛔ Senza prefisso `E_`, riservato ai codici a catalogo |
| `reason_key` | `amministrazione.famiglie_documento.disattiva_blocco.*` |
| `dettaglio` | `famiglia_id`, `codice_interno`, il conteggio, e per i documenti anche la tabella |

Non c'è una chiave `valori`: le frasi dei due codici non hanno segnaposti, e non nominano tabelle.
La tabella dei documenti sta nel `dettaglio`, che il guard porta nel contesto del registro errori.

⚠️ La `reason_key` è un **debito verso il frontend**: va nei file di lingua nello
stesso giro del lavoro sulla maschera.

---

### ⚠️ Note operative

* **Famiglia inesistente**: si **solleva** `E_VENDITE_CHIAMATA_NON_VALIDA` invece
  di rispondere `[]` — «si può spegnere» su una riga che non esiste è una frase
  senza senso. Stesso ramo delle gemelle sui registri.
* **`STABLE`**: non scrive niente e non solleva errori di dominio. Il rifiuto è
  del guard, non suo.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.4.*
