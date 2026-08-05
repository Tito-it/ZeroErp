# v2 — modifiche da riportare in `brief-db-codice-errore-strutturato.md`

> File temporaneo: il brief principale è aperto sul branch BE e modificarlo ora
> darebbe conflitto. Qui ci sono **solo** le sei modifiche fatte dopo la chiusura
> della slice DB, ognuna col punto in cui va. A ricompattazione avvenuta questo
> file sparisce.
>
> **Origine:** `20260805-11` (registro 57 → 53) e la rilettura di
> `error_policies.py` fatta sul blocco proposto dal BE.

---

## 1 · Testata «Stato: slice DB CHIUSA» — ultimo capoverso

**Sostituire:**

> 🔴 **Resta il lato BE, e l'ordine non è indifferente:** prima i 57 codici in
> `error_policies.py` (§7), **poi** i tre innesti con il guard `P0001` (§5).
> Invertirli porta 77 call site da 400 a 500.

**con:**

> 🔴 **Resta il lato BE, e l'ordine non è indifferente:** prima i **30** codici
> scoperti in `error_policies.py`, **poi** i tre innesti con il guard `P0001`
> (§5). Invertirli porta **48** call site da 400 a 500; gli altri 29 invece
> migliorano il giorno stesso.
>
> ⚠️ **Non sono 57** (§7): il registro è sceso a **53** con `20260805-11`, e di
> quei 53 **23 hanno già una policy**. Registrare di nuovo un codice che c'è già
> non dà errore in Python — **sovrascrive in silenzio**.

---

## 2 · §2 — dopo la tabella del censimento A/B/C

**Aggiungere:**

> **Ricensimento DB del 2026-08-05:** **978** call site — A **886** (identico),
> B **77**, C **9** (identico). Differenze di conteggio, non di sostanza.
> ⚠️ Attenzione se lo si rifà: contare gli argomenti significa spezzare sulle
> virgole di primo livello, e un apostrofo dentro un commento SQL
> (`-- la funzione e' VARIADIC`) apre una stringa che non si chiude più. Vanno
> tolti i commenti **prima** di contare — vedi §8.

---

## 3 · §7 — sostituire la tabella «Oggi / Dopo l'adozione BE»

**Sostituire:**

> | | Cosa arriva al translator | Policy | HTTP |
> |---|---|---|---|
> | **Oggi** | la regex non trova il codice → ripiego `E_DATABASE` | **registrata** | **400** |
> | **Dopo l'adozione BE** | arriva `PRATICHE_TRANSIZIONE_NON_AMMESSA` | non registrata … | **500** |

**con:**

Oggi la regex non trova quei codici e il translator ripiega su `E_DATABASE`, che
è registrato → **400** con messaggio generico. Domani il codice **arriva**, e da
lì in poi dipende da una cosa sola: se è registrato o no.

> ⚠️ **Correzione alla correzione.** Il brief BE dice che quei codici «non sono
> registrati in `error_policies.py`». **Non è vero per tutti: 23 su 57 lo sono
> già.** Le chiavi vere di `_POLICIES` sono 430, e fra queste ci sono
> `PRATICHE_TRANSIZIONE_NON_AMMESSA`, `FLUSSI_TRANSIZIONE_NON_AMMESSA`, tutta la
> famiglia `DEFINIZIONE_*`. Qualcuno le ha registrate col nome storto, e ha fatto
> la cosa giusta.

Il gruppo B si spacca in due metà con destini **opposti**:

| | Codici | Call site | Oggi | Dopo l'adozione BE |
|---|---:|---:|---|---|
| **Già registrati** | **23** | **29** | `E_DATABASE` → 400 generico | ✅ la **loro** policy: status e messaggio giusti. **Migliorano il giorno stesso** |
| **Non registrati** | **30** | **48** (in 26 funzioni) | `E_DATABASE` → 400 generico | 🔴 `resolve()` ha la scorciatoia solo per `E_` → `E_GENERICO` → **500** |

E nel capoverso che segue, «la registrazione dei **57**» diventa «la
registrazione dei **30**», «57 righe» diventa «**30 righe in un file solo**».

---

## 4 · §7 — dopo la nota sulla riga con l'apostrofo

**Aggiungere:**

> ✅ **Il registro è già sceso a 53** (`20260805-11`). Incrociando i 57 codici coi
> call site veri, **otto** non sono sollevati da nessuna funzione: due li usa il
> backend (`EMITTENTE_NON_MODIFICABILE`, `PREV_STATO_NON_MODIFICABILE`), due sono
> **solo loggati** e non arriveranno mai a un client (`MESSAGGIO_NON_DEFINITO`,
> `W_TXID_NOT_REGISTERED`), **quattro non hanno consumatori da nessuna parte** —
> né DB, né Python, né FE — e sono usciti dal seed.
>
> ⚠️ Prima di cancellarli è servita la distinzione che conta: **superati** o
> **non ancora agganciati**? Un codice a seed senza chiamanti può essere un
> residuo o un pezzo della slice di qualcun altro che il call site non ha ancora
> raggiunto. Per tutti e quattro l'ha detto il DB stesso:
>
> | Codice | id | Prova |
> |---|---:|---|
> | `PREV_TOTALE_NON_POSITIVO` | 353 | il corpo vivo di `fn_cambia_stato_preventivo`: *«rev 2026-07-16: rimossi il guard PREV_TOTALE_NON_POSITIVO e il filtro quantita > 0»* |
> | `PREV_ANNULLAMENTO_COMMESSA_ATTIVA` | 356 | stesso corpo, nota di `20260804-74`: *«con l'assorbimento esce di scena anche il codice …, privo del prefisso `E_`»*. Rimpiazzato da `E_PREV_ANNULLA_COMMESSA_EMESSA` |
> | `PRATICHE_ISTANZA_SENZA_RUOLO` | 304 | `trgfn_pratiche_guard_contesto` oggi solleva `..._ISTANZA_SENZA_SOGGETTO` e `..._RUOLO_SENZA_SOGGETTO`: la variante «senza ruolo» non c'è più |
> | `CATASTO_SOURCE_NOT_FOUND` | 115 | `fn_clone_catasto_from_parent_by_istanza` oggi solleva `ERRORE_PARAMETRI` |
>
> ⚠️ **Controllo che avrebbe fatto fallire il migrate se saltato:**
> `dbops.error_log` ha una FK verso `config.messaggi_errore(id)`. Verificato
> **0 riferimenti** per tutte e quattro; con anche uno solo il `DELETE` sarebbe
> morto sulla FK.
>
> Due mosse per il catalogo (righe dal CSV **+** `DELETE`, perché il loader è un
> upsert), **una sola per il registro**: il suo seed è `DELETE` + `loadData`,
> cioè un mirror — bastano le righe tolte dal CSV. È esattamente il motivo per
> cui era stato scritto come mirror invece che come upsert.
>
> Simulazione dello stato post-migrate in transazione annullata: guardrail verde,
> *«nessuna voce di troppo nel registro (53 registrate)»*.

---

## 5 · §9 — riepilogo

**Riga 6, sostituire:**

| 6 | Registrare i 57 codici senza prefisso in `error_policies.py` | BE | 🔴 **prerequisito del #3** (§7) |

**con:**

| 6 | Registrare i **30** codici senza prefisso **e senza policy** in `error_policies.py` (dei 53 rimasti, 23 ci sono già) | BE | 🔴 **prerequisito del #3** (§7) |

**Aggiungere in coda alla tabella:**

| 9 | 4 codici superati fuori dal seed: registro **57 → 53** | DB | ✅ **fatto** — `20260805-11` (§7) |

**Nella tabella «Cosa trova il BE già pronto», sostituire l'ultima riga:**

| I codici da registrare | elenco vivo: `SELECT codice FROM dbops.messaggi_errore_codici_legacy ORDER BY 1` — **53 righe, e 23 hanno già la policy**: da fare sono le **30** che non compaiono fra le chiavi di `_POLICIES` |
| ⚠️ Chiave duplicata = sovrascrittura muta | in un dict literal Python l'ultima vince **senza errore né warning**, e nel progetto non ci sono `ruff`/`flake8` che lo intercettino. Registrare un codice già presente **sostituisce** la policy esistente: le 23 vecchie voci vanno **rimosse esplicitamente**, non coperte |

---

## 6 · §11 — tabella dei file consegnati

**Aggiungere dopo la riga di `20260805-08`:**

| `80_data/changelog/20260805-11-delete-messaggi-errore-codici-superati` + 4 righe dai **due** CSV | i 4 codici superati: registro **57 → 53** (§7) |

---

## Appendice — i due controlli, per non rifarli a mano

**Chiavi duplicate** (deve stampare due numeri uguali e lista vuota):

```bash
python - <<'EOF'
import re, collections
src = open('backend/apps/core/services/error_policies.py').read()
k = re.findall(r'^\s*"([A-Z][A-Z0-9_]*)":\s*ErrorPolicy\(', src, re.M)
print("voci:", len(k), "| distinte:", len(set(k)),
      "| duplicate:", [x for x, c in collections.Counter(k).items() if c > 1])
EOF
```

**I 5 codici il cui HTTP status cambierebbe** col blocco proposto dal BE — non
sono codici nuovi, funzionano già oggi, quindi è un cambio di contratto:

| Codice | Oggi | Proposto | |
|---|---|---|---|
| `FLUSSI_COMPETENZA_MANCANTE` | 409 | **403** | ✅ autorizzazione, non conflitto |
| `FLUSSI_PRESA_NON_ELIGIBILE` | 409 | **403** | ✅ idem |
| `FLUSSI_ESITO_OBBLIGATORIO` | 409 | **400** | ✅ input mancante |
| `DEFINIZIONE_NON_PUBBLICABILE` | 422 | **409** | ✅ era l'unico 422 in una famiglia tutta 409 |
| `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` | 409 | **400** | ⚠️ il meno netto |

Tutti e cinque hanno consumatori: quattro hanno test Django in
`apps/pratiche/tests/services/` da rilanciare; due hanno anche un pgTAP
(`test-assegnazione-flusso-eligibilita.sql`) che però asserisce il *codice*, non
lo status, e quindi non si rompe.
