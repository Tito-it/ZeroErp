## 📘 Documentazione Concettuale – Funzione `script.fn_check_accredito_annullabile`
### 🎯 Scopo Principale
(latest review 25-08-2026)

Elenca i **motivi che impediscono di annullare l'accredito di una riga di reso**.
Funzione **pura** (`fn_check_*`): non solleva errori di dominio e non scrive.
Ritorna `[]` quando l'accredito si può annullare.

**Sede unica della regola.** La legge `vendite.fn_annulla_accredito_riga_reso`,
che solleva il codice del **primo** motivo; e la legge il **read-side** —
`vendite.vw_resi_da_accreditare` e le righe del reso — per spegnere il pulsante
e dire perché, invece di far scoprire il vincolo sbagliando.

> 👀 **Vedi anche**
>
> [vendite.fn_annulla_accredito_riga_reso](/dbzero/vendite/funzioni/fn_annulla_accredito_riga_reso)
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare)
> [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti)
> [script.fn_check_fattura_eliminabile_da_lotto](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto) — il gemello per forma

---

### Perché esiste

Richiesta del team BE, 2026-08-25:

> *Il pulsante «Annulla l'accredito» è acceso anche quando l'annullo non è più
> possibile: l'operatore apre la dialog, scrive il motivo obbligatorio,
> conferma, e solo lì riceve `E_ACCREDITO_ANNULLO_NON_AMMESSO`.*

`linee-guida-sql` §12.1: **«Permesso ⇒ nascondi. Stato ⇒ disabilita col
motivo.»** Avere una rettifica già emessa è uno **stato**, quindi il pulsante non
va nascosto e non va lasciato acceso: va disabilitato, e deve dire perché.

Finché il predicato viveva solo dentro la funzione di mutazione, il frontend
poteva solo proporre l'azione e sperare.

---

### I tre motivi, nell'ordine

| # | `reason` | Codice | Quando |
| --- | --- | --- | --- |
| 1 | `NESSUN_ACCREDITO` | `E_ACCREDITO_NON_TROVATO` | non c'è nessuna riga di ponte per quella riga di reso |
| 2 | `FUORI_PERIMETRO` | `E_ACCREDITO_ANNULLO_INCOMPLETO` | le rettifiche non sono tutte visibili sotto RLS |
| 3 | `RETTIFICA_EMESSA` | `E_ACCREDITO_ANNULLO_NON_AMMESSO` | almeno una rettifica è uscita dalla finestra |

⛔ **Nessun codice errore nuovo**: sono i tre che la funzione di mutazione
solleva già. Questa non li solleva — li **nomina**.

⚠️ **L'ordine è il contratto**, perché la mutazione solleva il primo. Se qui
divergesse, il tooltip direbbe una cosa e l'errore un'altra: cioè il difetto di
partenza, spostato di un passo.

I motivi 2 e 3 **escono subito** invece di accumularsi: leggono l'insieme delle
rettifiche, e senza insieme (motivo 1) direbbero il falso; su un insieme non
visibile per intero (motivo 2) il conteggio del 3 uscirebbe più basso del vero.

---

### La forma del motivo

```json
{ "codice":     "E_ACCREDITO_ANNULLO_NON_AMMESSO",
  "reason":     "RETTIFICA_EMESSA",
  "reason_key": "vendite.resi.annullo_blocco.rettifica_emessa",
  "dettaglio":  { "bloccate": 3, "totali": 3 },
  "valori":     ["24", "3", "3"] }
```

`codice` / `reason` / `reason_key` / `dettaglio` sono i quattro campi della
famiglia. **`valori` è il quinto e non è decorativo**: è il `VARIADIC` che la
funzione di mutazione passa a `script.fn_log_and_raise_error`, cioè i pezzi che
compongono **la frase che l'operatore legge**. Sta qui perché quella frase non si
ricomponga in due posti diversi.

---

### ⛔ Il motivo 3 ha tre condizioni, e si tengono tutte e tre

```sql
ca.stato_emissione <> 'NON_EMESSA'
OR EXISTS (SELECT 1 FROM vendite.attivita_fatturabili af
            WHERE af.commessa_attivita_id = ca.id
              AND (COALESCE(af.lock_in_fatturazione, false)
                   OR af.fattura_riga_id IS NOT NULL))
```

Sembrerebbe più prudente scrivere *«esiste una riga in `attivita_fatturabili` →
bloccato»*. **Sarebbe sbagliato**: dopo un reset di lotto quella riga
**sopravvive** — `fn_cleanup_fatture_by_ids` la sblocca e le azzera
`fattura_riga_id`, non la cancella. La scorciatoia vieterebbe **per sempre**
l'annullo dopo un reset legittimo.

⛔ **Ed è tutto-o-niente**: basta **una** rettifica bloccata per rifiutare
l'intero accredito. Un annullo parziale lascerebbe la coda a chiedere un residuo
che nessuno può più soddisfare — la malattia per cui il cantiere esiste.

---

### ⚠️ Il motivo 2 è l'unico che dipende da chi guarda

`vendite.commesse_attivita` ha la RLS, la tabella di ponte no. Una rettifica
fuori perimetro emittente si legge come «non c'è», e zero non è un dato: è
**fail-closed**.

Ne discende che due operatori possono vedere lo stesso reso con il pulsante in
stati diversi. È **coerente** con la mutazione, che rifiuterebbe comunque — ma va
saputo, perché è l'unico motivo che non parla dello stato del documento.

Per la stessa ragione la funzione è **`SECURITY INVOKER`**: con `DEFINER`
risponderebbe sempre «si può», e il pulsante resterebbe acceso su un annullo che
verrà rifiutato.

---

### ⚠️ «Mai accreditato» e «già annullato» sono lo stesso motivo

Il motivo 1 li copre insieme, e non è un difetto: l'annullo **cancella** le righe
di ponte, quindi lo stato osservabile è identico.

Distinguerli richiederebbe un soft-delete, e il soft-delete romperebbe altre due
cose — è il **vincolo C-3**, su tre posti che si cambiano insieme:

1. questa funzione (motivo 1);
2. `script.fn_check_rinuncia_reversibile`;
3. la guardia `E_RESO_ANNULLO_CON_ACCREDITO` di `vendite.fn_annulla_reso`.

Gli ultimi due tornano permissivi **solo perché la riga sparisce davvero**.

---

### 🔴 Non è una capability per riga

`linee-guida-sql` §12.4: *«le capability stanno solo sul DETTAGLIO, mai per riga
di lista; le liste fanno il gate sui codici che hanno già in riga»*.

Questa funzione è uno **scalare**, che è proprio la forma ammessa: la coda
accrediti la chiama una volta per riga e proietta il risultato in
`annullo_blocco_codice`, esattamente come già fa con
`fn_resi_riga_accreditato_partita` e `fn_resi_riga_residuo_riconsegna`.

⛔ E la colonna è **nuova**, non un allargamento di `blocco_codice`: quella
risponde a «perché non posso **accreditare**» e il suo unico valore,
`GIA_ACCREDITATO`, è esattamente la condizione che **abilita** l'annullo.

---

### Esempio d'uso

```sql
-- Si può annullare?
SELECT jsonb_array_length(script.fn_check_accredito_annullabile(24)) = 0 AS ammesso;

-- Perché no?
SELECT script.fn_check_accredito_annullabile(24) -> 0 ->> 'reason';
-- → RETTIFICA_EMESSA

-- Come lo legge una lista (il primo motivo, NULL se ammesso)
SELECT resi_riga_id, annullo_blocco_codice
  FROM vendite.vw_resi_da_accreditare;
```

---

### Note operative

* **`STABLE`**: è una lettura, non un verbo. Se un domani scrivesse, la vista che
  la chiama per riga diventerebbe una scrittura per riga di lista.
* **Guard di parametro**: `p_resi_riga_id` obbligatorio e `> 0`, altrimenti
  `E_PARAMETRO_INVALIDO` — un id assente non esce da nessuna interfaccia, lo
  produce un chiamante rotto.
* ⚠️ **La riga di reso inesistente non è un motivo**: la funzione risponde
  `NESSUN_ACCREDITO`, perché legge il ponte e non la riga. È la funzione di
  mutazione a distinguere il caso, col suo `FOR UPDATE`.
* 🔴 Le tre `reason_key` vanno presenti nei locales: `check_i18n_keys.py`
  (controllo 4) fallisce se manca anche una sola, e un tooltip vuoto è peggio del
  pulsante acceso.
* Test: `db/pgtap/vendite/test-annulla-accredito-riga-reso-v1.sql` (19..23). ⭐ Il
  **22** è il presidio della richiesta del BE, ed è **strutturale**: asserisce che
  la funzione di mutazione *chiama* questa e *non contiene più* il predicato. Un
  test comportamentale proverebbe che oggi coincidono; questo prova che **non
  possono divergere**.
* Cantiere: `brief-design-note-credito-resi.md` §45.

---

{% include-markdown "signature-core.md" %}
