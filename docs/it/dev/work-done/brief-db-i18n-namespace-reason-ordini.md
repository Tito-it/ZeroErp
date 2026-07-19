# Brief DB — Reason ordini emesse in un namespace i18n inesistente

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Priorità**: 🟡 MEDIA (difetto isolato, 5 stringhe; blocca
> però un banner FE già scritto e pronto)
> **Stato**: ✅ REALIZZATO (2026-07-19) — changeset `20260719-12` applicato su dev,
> pgTAP `test-fn-available-actions-ordine-v2.sql` **9/9 verde**.
> Residuo: rigenerazione doc auto-gen (§5) e commit.
> **Origine**: emerso chiudendo lato FE il
> [brief push commessa «già inviato»](brief-db-push-commessa-gia-inviato.md) §10a.
> Scritte le prime traduzioni per le reason del push ordini, si è scoperto che la
> chiave i18n emessa dal DB non è risolvibile nel FE.

## 1. Cosa serve (NON come)

`script.fn_available_actions_ordine` espone `can_push_commessa_reason_key` con
chiavi nel namespace **`ordini.*`**. Quel namespace **nel frontend non esiste**:
l'i18n degli ordini vive interamente sotto **`vendite.ordini.*`**.

Serve che le **5 reason_key del push commessa ordini siano emesse nel namespace
`vendite.ordini.*`**, coerentemente con il resto del dominio:

| `reason` (codice, **da NON cambiare**) | namespace della `reason_key` |
| --- | --- |
| `ORDINE_NON_CONFERMATO` | `ordini.*` → **`vendite.ordini.*`** |
| `ORDINE_FATTURA_DA_DDT` | `ordini.*` → **`vendite.ordini.*`** |
| `ORDINE_GIA_INVIATO` | `ordini.*` → **`vendite.ordini.*`** |
| `ORDINE_GIA_FATTURATO` | `ordini.*` → **`vendite.ordini.*`** |
| `ORDINE_NESSUNA_RIGA_PUSHABILE` | `ordini.*` → **`vendite.ordini.*`** |

La parte finale della chiave (`push_commessa_reason.<suffisso>`) resta identica:
cambia **solo il prefisso di namespace**.

### Perché è un difetto e non una convenzione alternativa

Non è una scelta di stile su cui allinearsi a valle: è **incoerente con la
funzione stessa**. Nello stesso corpo, l'azione push espone
`label_key = 'vendite.ordini.azione_push_commessa'` — namespace giusto — mentre
le reason poche righe sopra usano `ordini.`. Fuori dalla funzione, la coerenza è
totale dall'altra parte: tutti i `label_key` di
`config.transizioni_stati_{ordini,ddt}` usano `vendite.*`, e le reason del DDT
sono già corrette (`vendite.ddt.push_commessa_reason.*`). L'ordine è l'unico
outlier.

### Vincoli sul risultato

- **I codici `reason` non devono cambiare**: non sono chiavi i18n, e cambiarli
  romperebbe una superficie diversa da quella che stiamo sistemando.
- **Le revisioni recenti della funzione non devono regredire**: il corpo attuale
  include il classificatore condiviso `fn_get_stato_push_segment` e la
  capability `requires_righe`, entrambi applicati il 2026-07-16/19.
  ⚠️ È il rischio principale di questo intervento — vedi §2.

## 2. Nota sull'origine (serve a valutare il rischio, non a dire come fare)

Il difetto **nasce con la funzione** (`20260605-09`) e si è propagato **per
ereditarietà** a tutte le revisioni successive — `20260608-47`, `20260710-02`,
`20260711-10`, `20260716-02`, `20260719-10` — perché ogni revisione riparte dal
corpo della precedente. È rimasto invisibile per un mese e mezzo solo perché
nessun consumatore FE leggeva quelle chiavi.

Due implicazioni per chi interviene:

1. la stessa catena di ereditarietà che ha propagato l'errore può **riportare
   indietro** le revisioni recenti se il punto di partenza non è quello vivo;
2. il valore va corretto **in tutti e 5 i rami**, non solo in quelli nuovi
   (`gia_inviato`/`gia_fatturato`): gli altri tre sono sbagliati da giugno e
   nessuno se ne è accorto.

## 3. Fuori perimetro

- Reason e capability **DDT**: già corrette, non toccare.
- Reason **preventivi** (`preventivi.push_commessa_reason.*`): namespace
  top-level legacy, **ma funzionante** — il FE ha `preventivi` come radice.
  Nessuna azione: non è rotto, e uniformarlo sarebbe un refactor i18n a sé.
- Logica del push, classificatore, predicati di esclusione: invariati.

## 4. Cosa comunicare indietro a BE/FE

Solo la conferma dell'avvenuto rename. **Nessun adeguamento BE/FE atteso**: le
traduzioni it/en sono già in repo sotto il nome nuovo
(`vendite.ordini.push_commessa_reason.*`, 5 chiavi) e il banner in
`OrdiniDrawer.vue` è già scritto — è guardato da `te(key)`, quindi oggi resta
semplicemente invisibile e si accenderà da solo appena la chiave sarà
risolvibile.

Se per qualsiasi ragione si scegliesse un nome diverso da
`vendite.ordini.push_commessa_reason.<suffisso>`, **comunicarlo**: in quel caso
le 5 chiavi i18n vanno rinominate lato FE.

## 5. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | Reason_key del push ordini emesse sotto `vendite.ordini.*` (5 rami) — changeset `20260719-12` | ✅ |
| 2 | Verifica: `can_push_commessa_reason_key` di un ordine già pushato e di uno in DRAFT | ✅ automatizzata (pgTAP 9/9, §5a) |
| 3 | Apply dev | ✅ 2026-07-19 |
| 4 | Rigenerazione doc auto-gen `fn_available_actions_ordine.md` | ✅ 5/5 chiavi `vendite.ordini.*`, nessuna residua |
| 5 | Conferma a BE/FE (§4) | ☐ nessun intervento atteso da loro |
| 6 | Commit | ☐ |

### 5a. Nota sulla verifica — perché non è manuale

Lo step 2 era formulato come controllo a vista su due ordini. Non basta: la
causa del difetto è l'**ereditarietà** fra revisioni (§2), e un controllo
manuale non impedisce alla settima revisione di reintrodurlo come hanno fatto
le sei precedenti. È stato quindi tradotto in test automatico:

- `db/pgtap/script/test-fn-available-actions-ordine-v2.sql` — `plan(8)` → `plan(9)`
  - **test 6 adattato**: asseriva la chiave vecchia (`ordini.push_commessa_reason.gia_fatturato`),
    quindi la correzione lo avrebbe fatto fallire. ⚠️ Era l'unico consumatore
    vivo della chiave vecchia oltre alla funzione;
  - **test 9 nuovo**: guard di namespace, verifica che *ogni* `reason_key`
    emessa stia sotto `vendite.ordini.push_commessa_reason.*` (copre 3 rami su
    5 — gli altri due condividono lo stesso prefisso nello stesso blocco `IF`).

Gli altri riscontri della chiave vecchia sono changelog storici
(`20260605-09`, `20260608-47`, `20260710-02`, `20260711-10`, `20260716-02`,
`20260719-10`): **non si toccano**, sono la storia applicata.

Corpo del changeset preso dalla doc auto-gen e confrontato riga per riga con il
vivo: le uniche differenze sono le 5 chiavi, due blocchi di commento e
l'estensione del `COMMENT`. Nessuna regressione su `fn_get_stato_push_segment`
né su `requires_righe`, che era il rischio principale segnalato in §1.

## 6. Riferimenti

> **Companion (2026-07-19)**: [brief-db-ddt-reason-push-catch-all.md](brief-db-ddt-reason-push-catch-all.md)
> — stessa famiglia (reason del push commessa), **difetto opposto e
> complementare**: lì le reason DDT hanno il namespace giusto e il messaggio si
> vede, ma il ramo catch-all ne racconta una falsa (un DDT consegnato di ordine
> a trigger `CONFERMATO` si sente dire «dev'essere spedito o consegnato»).
> Rilievo collegato: manca `DDT_FATTURA_DA_ORDINE`, **speculare esatto** di
> `ORDINE_FATTURA_DA_DDT` che questo brief elenca fra le 5 reason ordini — metà
> della regola XOR è spiegata all'utente, l'altra metà no. Se i due interventi
> finiscono nello stesso giro, conviene rileggerli insieme: toccano entrambi il
> vocabolario delle reason di push.

- Brief d'origine: [brief-db-push-commessa-gia-inviato.md](brief-db-push-commessa-gia-inviato.md) §10a
- Definizione viva: `docs/it/dbzero/script/funzioni/fn_available_actions_ordine.md`
- Gemella già corretta: `docs/it/dbzero/script/funzioni/fn_available_actions_ddt.md`
- Consumatore FE: `frontend/src/vendite/ordini/components/OrdiniDrawer.vue`
  (banner reason) + `frontend/src/locales/{it,en}.json`
