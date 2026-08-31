# API titoli_iva_soggetto (Django)

## Scopo

Esporre via HTTP il **registro dei titoli IVA di un soggetto** — le condizioni
documentate che cambiano il trattamento fiscale delle sue righe (dichiarazioni
d'intento, esportatore abituale, split payment, reverse charge) — con i loro
**ambiti** di applicazione e il **registro dei movimenti** che consuma il
plafond.

## Contesto

Famiglia di endpoint di area `anagrafiche`, permesso `titoli_iva`.
Il modello è quello della Fase 2 del cantiere IVA:

```text
anagrafiche.soggetti_titoli_iva              il titolo (validità, plafond, iva_id, ambito)
  └─ ..._ambiti                              su cosa si applica, quando l'ambito non è TUTTO
  └─ ..._movimenti                           il registro che consuma il plafond
```

⭐ **`imponibile_utilizzato` è un accumulatore**: non lo scrive nessuno a mano —
è la somma del registro, riportata da un trigger. È la ragione per cui l'annullo
di un movimento è un **contro-movimento** e non una cancellazione (vedi sotto).

⚠️ **Tutte queste tabelle hanno la RLS.** Senza il contesto operatore un
conteggio torna **zero** e sembra un dato: «non c'è niente» e «non vedo niente»
non si distinguono. Gli endpoint girano sempre sotto JWT, quindi il contesto c'è.

## Le rotte

| Metodo | Path (sotto `/api/v1/anagrafiche/`) | Cosa |
|---|---|---|
| `GET`/`POST` | `soggetti/{soggetto_id}/titoli-iva/` | elenco e creazione |
| `GET`/`PATCH`/`DELETE` | `soggetti/{soggetto_id}/titoli-iva/{titolo_id}/` | dettaglio, modifica, disattivazione |
| `GET`/`POST` | `.../{titolo_id}/ambiti/` | gli ambiti del titolo |
| `GET`/`PATCH`/`DELETE` | `.../{titolo_id}/ambiti/{ambito_id}/` | dettaglio ambito |
| `GET`/`POST` | `.../{titolo_id}/movimenti/` | il registro, e la **forzatura** |
| `POST` | `.../{titolo_id}/movimenti/{movimento_id}/annulla/` | ⭐ l'**annullo** di una forzatura |
| `GET` | `titoli-iva/sfondati/` | presidio cross-soggetto: i titoli oltre il tetto |

⚠️ **`titoli-iva/sfondati/` sta PRIMA delle rotte con `{soggetto_id}`** nel
`urlpatterns`: con l'ordine invertito `sfondati` verrebbe letto come un
`soggetto_id`.

## ⭐ `POST .../movimenti/{movimento_id}/annulla/`

Annulla una **forzatura** del registro scrivendo un **contro-movimento**.

- Body: `motivo` (string) — **obbligatorio**
- `200`: il movimento di annullo creato
- `409`: annullo non ammesso (`E_TITOLO_IVA_ANNULLO_NON_AMMESSO`)

⛔ **`annulla` come ultimo segmento e NON un `DELETE`**, perché l'azione **non
cancella niente**: aggiunge una riga. Il verbo nomina ciò che è, ed è la
grammatica URL delle azioni di dominio (`API.md`).

⭐ **E il contro-movimento non è una scelta stilistica**: `imponibile_utilizzato`
è la `SUM` di tutto il registro, quindi la riga opposta **riporta
l'accumulatore da sola**. Un flag `annullato` avrebbe richiesto a ogni lettore
di ricordarsi di filtrarlo — e il primo che se ne dimentica ottiene un plafond
sbagliato senza nessun errore. Inoltre resta **traccia**: la riga originale non
sparisce.

### La capability, e perché le precondizioni non sono qui

Le righe di `GET .../movimenti/` arrivano da
`anagrafiche.vw_stiva_movimenti_dettaglio` e portano:

| Campo | Cosa |
|---|---|
| `is_annullo` | questa riga **è** l'annullo di un'altra |
| `is_annullato` | questa riga **è stata** annullata |
| `annulla_movimento_id` | il legame, nei due versi |
| `annullo_blocco_codice` | ⭐ il motivo per cui l'annullo **non** è ammesso, o `NULL` se lo è |
| `annullo_blocco_reason_key` | la chiave i18n del motivo (`anagrafiche.titoli_iva.annullo_blocco.*`) |

⛔ **Le cinque precondizioni NON sono ricopiate nel backend**, ed è deliberato:
vivono in `script.fn_check_annullo_movimento_titolo_iva`, la **stessa** funzione
da cui la vista prende il motivo per spegnere il pulsante e da cui la madre
prende il codice per rifiutare. Riscriverle qui vorrebbe dire che il tooltip e
il rifiuto possono divergere — e divergerebbero in silenzio.

| # | Codice | Significato |
|---|---|---|
| 1 | `MOVIMENTO_NON_TROVATO` | il movimento non esiste |
| 2 | `NON_FORZATURA` | è il riflesso di un documento: si corregge **dal documento**, con una nota di credito |
| 3 | `RIGA_DI_ANNULLO` | è esso stesso l'annullo di un'altra riga |
| 4 | `GIA_ANNULLATO` | esiste già una riga che lo annulla |
| 5 | `PLAFOND_NEGATIVO` | annullarlo porterebbe l'usato **sotto zero** |

⚠️ **L'ordine è il contratto**: la superficie mostra il **primo** motivo e la
madre solleva il **primo** codice. Se divergessero, il tooltip direbbe una cosa
e l'errore un'altra.

📌 Il terzo si chiamava `E_UN_ANNULLO` fino al 2026-08-31: non nasceva come
«E\_ di errore» ma come «è un annullo», e quel prefisso lo faceva leggere come un
**codice errore** dal cancello che cerca i letterali `E_*`. Il `reason_key`
**non** è cambiato — è un indirizzo i18n, e il testo a video è lo stesso.

## Regole comuni alla famiglia

- Area `anagrafiche`, permesso `titoli_iva`; v1, JWT obbligatorio.
- **Ownership a due livelli** su tutte le rotte annidate: il titolo deve
  appartenere al `soggetto_id` del path, e il movimento/ambito al `titolo_id`.
  ⚠️ Senza il secondo livello, un id di un altro soggetto passerebbe il primo
  controllo e agirebbe su un registro che non è il suo.
- Le scritture passano dalle **madri DB**, che tengono lock e invarianti; il
  service fa ownership, normalizzazione e traduzione errori.
- ⛔ **`emittente_fiscale_id` è la PK** di `anagrafiche.emittenti_fiscali`, non
  il `soggetto_ruolo_id`. Il ponte
  `anagrafiche.emittenti_fiscali_billing_account` lega invece il
  **soggetto-ruolo**: sbagliare fra i due qui non dà zero righe per caso — dà un
  errore di colonna, ma su una JOIN sintatticamente valida darebbe **zero righe
  in silenzio**.
- Disattivazione: **figli prima del padre** (i trigger DB lo impongono).

## Dipendenze DB

- `anagrafiche.soggetti_titoli_iva`, `..._ambiti`, `..._movimenti` (tutte RLS)
- `anagrafiche.vw_stiva_movimenti_dettaglio` (lettura del registro + capability)
- `anagrafiche.fn_annulla_movimento_titolo_iva` (madre dell'annullo)
- `script.fn_check_annullo_movimento_titolo_iva` (`STABLE`, pura — le cinque
  precondizioni, lette **sia** dalla vista **sia** dalla madre)
- `anagrafiche.fn_consuma_plafond_titolo_iva` (il consumo sotto lock, chiamato
  dalla fatturazione — non da questi endpoint)
- `config.tipi_titolo_iva` (`ha_plafond`), `config.iva`

## Note di migrazione

- Fase 2 del cantiere IVA:
  [brief-be-fe-titoli-iva-soggetto.md](../../../dev/work-done/brief-be-fe-titoli-iva-soggetto.md).
  L'annullo (`T3-b`) è del 2026-08-31.
- ⚠️ Al 2026-08-31 `anagrafiche.soggetti_titoli_iva` è **vuota**: nessun titolo
  è ancora stato registrato. Uno smoke che *cercasse* il caso passerebbe a
  vuoto — quello in repo
  (`backend/scripts/tests/smoke-titoli-iva-annullo-movimento.py`) lo
  **costruisce**.
- ✅ **Dal 2026-08-31 il consumo del plafond dalla fatturazione è in
  esercizio**: il task `consuma_plafond_lotto` gira in testa allo step
  DEFINITIVA, prima della numerazione — cioè mentre la fattura è ancora
  `EMESSA` e il guard di congelamento lascia scrivere. ⇒ Il registro non si
  popola più solo con le **forzature** manuali: ci arrivano i movimenti delle
  fatture, e quando il plafond copre solo una quota la riga **si spezza in due**
  (`vendite.fatture_righe.riga_capofila_id`).
  Smoke: `backend/scripts/tests/smoke-consuma-plafond-lotto.py`.
