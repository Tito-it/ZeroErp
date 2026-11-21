# Refactor v3 — Riallineamento al Modello Concentrico

**Data**: Marzo 2026
**Stato**: COMPLETATO (18/03/2026)

---

## Contesto

L'audit del 17/03/2026 ha evidenziato che il codebase rispetta il modello concentrico
al ~75%. Il DB è un centro solido (funzioni, trigger, viste). Le view API sono sottili.
Ma c'erano zone dove la logica di dominio era scivolata fuori dal centro.

---

## 1. Service Layer — `_create_indirizzo` → dispatch a metodi dedicati — COMPLETATO

`SoggettiService._create_indirizzo()` conteneva 3 branch in ~70 righe.

**Refactor applicato** in `soggetti_service.py`:

```python
def _create_indirizzo(self, soggetto_id, payload):
    """Dispatch — il payload determina il path."""
    if optional_str(payload, "indirizzo_libero"):
        return self._create_indirizzo_libero(...)
    det_id = self._resolve_indirizzo_dettaglio(payload)
    ...

def _create_indirizzo_libero(...)     # Indirizzo estero / libera forma
def _resolve_indirizzo_dettaglio(...) # Risolve dettaglio (esistente o nuovo)
def _create_stradario_da_generale(...)# Via nuova da stradario_generale
```

Ogni metodo ha una sola responsabilità. Se arriva un 4° tipo,
è un nuovo metodo + una riga nel dispatch.

---

## 2. Validazione CF — perché Python è il livello giusto — CONFERMATO

```
DB (Centro)         → fn_valida_codice_fiscale() check digit + Luhn
                      Trigger su INSERT/UPDATE soggetti
                      Valida: formato, lunghezza, caratteri, checksum

Python (Anello 1)   → cf_validator_it.py
                      valida_cf_congruenza_it(): data/sesso/comune ↔ CF
                      genera_cf_it(): encoding cognome/nome + check digit

Frontend (Anello 3) → Zero logica CF, chiama API
```

Questa separazione **è concentrica**: il DB valida la forma (immutabile),
Python valida la semantica (flessibile). Nessun refactor necessario.

---

## 3. Check Duplicato Indirizzo → `fn_check_indirizzo_duplicato` — COMPLETATO

**Prima**: LIKE prefix in Python + exact_match calcolato in Python.

**Dopo**: funzione DB `script.fn_check_indirizzo_duplicato()`:
- Costruisce stringa normalizzata via `fn_build_indirizzo_normalizzato` (unica source of truth)
- Cerca match prefix su `vw_indirizzi_dettaglio`
- Ritorna `exact_match boolean` calcolato dal DB
- RETURNS TABLE con `%TYPE` per compatibilità tipi vista
- Ritorna fino a 5 match ordinati per exact_match DESC
- Guard: stradario_id NULL → RETURN vuoto

**Python ora è passante**:

```python
# indirizzi_repository.py
def find_duplicato(self, ...):
    sql = "SELECT ... FROM script.fn_check_indirizzo_duplicato(%s, %s, ...)"
    # Chiama la funzione DB, ritorna il risultato

# geo_service.py
def check_indirizzo_duplicato(self, payload):
    existing = self._ind.find_duplicato(...)
    # Formatta il risultato per il frontend
```

**Test verificati**: match esatto 4/A ✓, prefix 4 ✓, nessun match 99 ✓,
senza civico ✓, NULL guard ✓.

---

## 4. CAP Auto-Resolve → `fn_resolve_codice_postale` — COMPLETATO

**Prima**: logica nel watcher Vue, non riusabile.

**Dopo**: funzione DB `script.fn_resolve_codice_postale()`:
- Priorità 1: CAP dallo stradario (via specifica)
- Priorità 2: CAP unico del comune (fallback)
- STABLE, PARALLEL SAFE

Il frontend mantiene il watcher per la UX reattiva. La funzione DB è
disponibile per import batch e altri service.

**Test verificati**: da stradario ✓, da comune singolo CAP ✓,
NULL ✓, priorità stradario su comune ✓.

---

## 5. `useIndirizzoSoggettoForm` → scomposizione responsabilità — COMPLETATO

**Prima**: god composable ~200 righe con troppe responsabilità.

**Dopo**: 3 composable + 1 helper statico:

```
useIndirizzoBase.js              — form geografico, CAP, check duplicato, validate
├── buildIndirizzoPayload()      — helper statico per payload (zero duplicazione)
├── useIndirizzoMultiTipo.js     — snapshot/restore per tipo, barra tag, auto-clone
└── useIndirizzoSoggettoForm.js  — compone base + multiTipo + libera + payload
```

### Eliminazione duplicazione payload

`buildIndirizzoPayload(data)` è un helper statico esportato da `useIndirizzoBase.js`.
Accetta un oggetto plain (form reattivo o snapshot). Usato da:
- `useIndirizzoBase.buildPayload()` — dal form reattivo
- `useIndirizzoSoggettoForm._buildPayload()` — dallo snapshot
- `IndirizzoDrawer.vue` — via `addr.buildPayload()`

### `useIndirizzoMultiTipo.js` (~100 righe)

Responsabilità isolata: snapshot/restore per tipo, barra tag, auto-clone.
Riceve `{ baseSnapshot, baseRestore, baseReset, form }` dal consumer.

### `useIndirizzoSoggettoForm.js` (~140 righe, era ~200)

Compone: `useIndirizzoBase` + `useIndirizzoMultiTipo` + modalità libera + payload.
Ogni responsabilità è in un composable dedicato.

---

## 6. Fix aggiuntivi emersi durante il refactor

### Pre-popolamento campi in modalità replace

`onStartReplace` in `IndirizziSoggettoDrawer.vue` ora pre-popola **tutti** i campi
civico dall'indirizzo esistente (civico, estensione, palazzina, scala, piano, interno).
La query `get_soggetto_indirizzi` è stata estesa con i campi mancanti.

### Unificazione `via_obj`

`stradario_obj` + `stradario_generale_obj` sono stati unificati in un unico `via_obj`.
Il checkbox "crea nuovo" cambia solo l'autocomplete, non la variabile.
`buildPayload` usa `stradario_id` se presente, altrimenti `toponomastica_id`.

### CAP sempre visibile

Il campo CAP è visibile in entrambe le modalità (stradario e via_nuova).
Auto-set da `via_obj.codice_postale_id`, fallback su lista CAP del comune.
Il form è identico in entrambe le modalità.

### Blocco `addressNotFound`

In tutte le modalità (new + replace): se via selezionata + civico inserito
+ nessun match esatto → messaggio + save bloccato. L'utente deve spuntare
"Indirizzo non presente, crea nuovo" per procedere.

---

## 7. Riepilogo finale

| # | Intervento | Stato | File principali |
|---|-----------|-------|-----------------|
| 1 | `_create_indirizzo` → extract method | COMPLETATO | `soggetti_service.py` |
| 2 | Validazione CF | CONFERMATO (già corretto) | — |
| 3 | Check duplicato → `fn_check_indirizzo_duplicato` | COMPLETATO | funzione DB + `indirizzi_repository.py` + `geo_service.py` |
| 4 | CAP resolve → `fn_resolve_codice_postale` | COMPLETATO | funzione DB |
| 5 | Scomposizione composable | COMPLETATO | `useIndirizzoBase.js` + `useIndirizzoMultiTipo.js` + `useIndirizzoSoggettoForm.js` |
| 6 | Duplicazione payload → helper condiviso | COMPLETATO | `buildIndirizzoPayload()` in `useIndirizzoBase.js` |
| 7 | Pre-popolamento replace | COMPLETATO | `IndirizziSoggettoDrawer.vue` + `soggetti_repository.py` |

**Build**: 486 modules OK | **Test backend**: 686 OK | **Funzioni DB**: testate

---

## Principio guida

> Quando appare il primo `if` che cambia comportamento in base a un flag:
> **sottoclasse** (backend) o **composable specializzato** (frontend).
>
> Il branching **semantico** (PF vs PG, libero vs normalizzato) è legittimo
> se guidato dai dati, non da flag di configurazione. Ma il metodo che lo
> contiene non deve superare le ~30 righe. Se lo fa: extract.
