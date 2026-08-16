# Template Preventivo — dagli indirizzi in lista agli slot (lato DB)

> **Cos'è.** La sede DB della richiesta che il BE ha mandato il **2026-08-16**: il
> context builder del Preventivo espone `indirizzi` come **dict di slot** e il
> template v3, che lo itera come lista, non renderizza più.
>
> **Chi ha chiesto.** BE (`dev/backend-tid`), brief «il template Preventivo passa
> dalla lista agli slot (l'ultimo dei sei)».
>
> ⚠️ **Quando il BE pubblicherà il suo file nel repo, i due vanno fusi in uno**:
> la regola già pagata su questo progetto è che *un brief separato si giustifica
> quando cambia il **soggetto**, non quando cambia il **lato** che lavora*.
>
> **Origine del cantiere**: §11.3 di
> [brief-db-indirizzi-su-ordini-contratti-offerte.md](../work-done/brief-db-indirizzi-su-ordini-contratti-offerte.md)
> e [brief-db-template-preventivo-indirizzi.md](../work-done/brief-db-template-preventivo-indirizzi.md).

---

## 1. Lo stato in una riga

✅ **Scritto**: due changeSet, `20260816-01` (bozza) e `20260816-02`
(pubblicazione). ⚠️ **Da applicare** — ed è il `migrate` che **riaccende la
stampa del preventivo**, ferma dal merge del BE (la «finestra rotta» del loro §4).

---

## 2. La decisione: si stampa **un solo slot**

*«La stampa è identica agli altri documenti»* (Tid, 2026-08-16). È anche la
risposta alla domanda del §7 del brief BE — le quattro etichette proposte
(«Luogo di consegna», «Indirizzo di fatturazione», «Punto di fornitura»,
«Residenza») **non** vanno tutte sul PDF.

Il Preventivo prende **lo stesso identico blocco** che `ord-ven`, `contratto`,
`off-comm` e `ddt-ven` hanno già pubblicato, **nella stessa posizione**: dentro
il riquadro «Cliente», non in una sezione a sé.

✅ **E il dato dice la stessa cosa** (misurato il 2026-08-16, su tutti i domini):

```text
46 snapshot indirizzo di documento in TUTTO il database
46 su 46 di tipo CON  ·  i 12 dei preventivi: 12 su 12 CON
zero righe FATT, FORNITURA, RES — mai scritte, da nessun dominio
```

Il contesto continua a esporre i quattro slot (segue la whitelist dell'ambito,
§11.1 del brief BE): è il **template** a scegliere cosa stampare. Tre aree che
nessun documento reale popola sarebbero codice che nessuno può verificare — e
che invecchia senza che nessuno se ne accorga.

---

## 3. Cosa fanno i due changeSet

| | File | Cosa |
| --- | --- | --- |
| **1** | `80_data/changelog/20260816-01-template-bozza-preventivo-slot-indirizzi` | crea la **BOZZA v4** dalla v3 pubblicata |
| **2** | `80_data/changelog/20260816-02-pubblica-template-preventivo-slot-indirizzi` | la **pubblica** (`valido_dal = current_date`); la v3 passa a `OBSOLETA` e resta ri-renderizzabile |

Due modifiche, non una:

1. **entra** il blocco `indirizzi.consegna` dentro il riquadro «Cliente»;
2. **esce** la sezione «Indirizzi documento» — la forma v1, lista + `.get()`.

⚠️ **Il punto 2 non è un extra.** Lasciarla non solo pianterebbe il render (è
proprio lei a iterare il dict), ma se anche la si convertisse a slot
stamperebbe **l'indirizzo due volte**: una nel riquadro Cliente e una nella
sezione. Il brief BE chiede di sostituire quel blocco; sul Preventivo la
sostituzione giusta è **spostarlo**, perché la posizione degli altri cinque
template è un'altra.

### ⚠️ Ancore verificate, non sperate

Entrambe le sostituzioni sono ancorate a testo che deve comparire **esattamente
una volta**, e il risultato deve differire dall'originale. Se qualcuno ha
ritoccato il template, il `migrate` **si ferma** invece di pubblicare una
versione identica alla vecchia — che sarebbe il fallimento silenzioso: registro
«fatto», PDF invariato. È la stessa forma usata ad agosto per gli altri tre.

---

## 4. Verificato, non solo scritto

**Diff v3 → v4**: `+20` righe (il blocco) e `−20` (la sezione), nient'altro.
Provato in transazione annullata: bozza creata, pubblicazione eseguita, v3 →
`OBSOLETA`, v4 `PUBBLICATA dal 2026-08-16`.

**Il blocco è stato renderizzato** con Jinja e `StrictUndefined`, su sei casi
scelti sui valori reali dei 12 snapshot dei preventivi:

| Caso | Esito |
| --- | --- |
| completo | `Luogo di consegna: · Azienda PG Test Natura · PIAZZA PRIMO MAGGIO 77 · 75025 POLICORO (MT) · IT` |
| senza intestazione (3 su 12) | nessuna riga vuota |
| senza `cap`/`citta`/`prov` (5 su 12) | riga geografica non stampata |
| solo `display` | ramo `elif` esercitato |
| `cap` mancante e `citta` presente | `ROMA (RM)` — **non** `None ROMA` |
| nessun indirizzo | sezione non stampata |

⭐ **Perché la guardia è per campo e non per slot**: sui 12 snapshot dei
preventivi `intestazione` è valorizzata su **9**, `cap`/`citta`/`prov` su **7**,
`via` e `stato` su 12. Il BE garantisce le **chiavi**, non i **valori** (§9.2):
con la sola guardia sullo slot, 3 preventivi stamperebbero una riga vuota e 5
una riga tronca.

---

## 5. 📮 Due cose per il BE

**1. 🔴 «Il Preventivo è l'ultimo template a leggere con `.get()`» non è vero.**
Lo è per il **blocco indirizzi**, che è ciò che il §2 del cantiere di agosto
chiedeva di chiudere — e quello si chiude qui. Ma il `.get()` resta ovunque
sulle righe e sull'IVA, in **tutti** i template (misurato il 2026-08-16):

```text
off-comm 37   ·   ord-ven 29   ·   contratto 21   ·   ddt-ven 11
preventivo: 13 sul solo blocco indirizzi (spariscono), ~20 su righe/iva (restano)
```

Non è una critica al lavoro: è che la frase, letta fra un anno, farebbe credere
chiusa una cosa aperta. Se il `.get()` sulle righe va tolto, è un cantiere suo —
con la sua misura, perché lì un nome sbagliato stampa una riga d'ordine vuota.

**2. La prima stesura del changeSet aveva un guard troppo largo** — «nessun
`.get()` nell'HTML risultante» — e ha fatto fallire il proprio dry-run sul
`r.get("ordine")` delle righe, che è fuori perimetro (§5 del brief BE: gli altri
blocchi non si toccano). Sostituito con due asserzioni precise: la forma nuova
c'è, la vecchia non c'è più. ⭐ *Un presidio che verifica più di quanto il
cantiere promette non è più sicuro: è solo più fragile.*

---

## 6. Definizione di «fatto» (checklist del BE)

- [x] template Preventivo **v4** con il blocco a slot, v3 → `OBSOLETA` e ancora
      ri-renderizzabile — ⚠️ *scritto, si avvera col `migrate`*;
- [x] **accesso diretto** su ogni campo, guardia **per campo**;
- [x] un preventivo **senza** indirizzi non stampa la sezione (guardia esterna);
- [ ] un preventivo **con** indirizzo di consegna, rigenerato, lo mostra sul PDF
      — è la verifica che tocca fare **dopo** l'apply, sul PDF vero.

## 7. Cosa NON è stato fatto, come da richiesta

Nessun tocco agli altri cinque template, nessuna modifica agli snapshot o alle
`fn_snapshot_indirizzo*`, nessuna rinomina di `codice_interno` (`test` resta
`test`), nessuna bonifica dei PDF già generati, nessun `btrim` difensivo.

---

## 8. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-16 | ⭐ **Scritti i due changeSet** su richiesta del BE, con la decisione di Tid «stampa identica agli altri documenti» → **un solo slot**, confermata dal dato (46 snapshot su 46 di tipo CON). Diff v3→v4 di sole 40 righe (+20 il blocco, −20 la sezione), blocco **renderizzato** con `StrictUndefined` su sei casi. 🔴 Trovato che la frase «il Preventivo è l'ultimo template a leggere con `.get()`» vale per il solo blocco indirizzi: gli altri quattro template ne hanno fra 11 e 37 su righe e IVA. ⚠️ **Da applicare**: fino al `migrate` la stampa del preventivo resta ferma |
