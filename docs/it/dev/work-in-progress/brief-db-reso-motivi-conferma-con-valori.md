# Brief DB — i motivi della «Conferma» del reso arrivano senza i numeri

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: il team DB** (`dev/db-tid`): un changeSet su `script.fn_available_actions_reso` (§3).
Analisi DB fatta il 2026-10-13 (§5); codice non iniziato, su indicazione di Tid: si parte quando lo dice lui.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | `reasons` con i `valori` sull'azione CONFERMATO, come la bolla | §3, §5 | via di Tid |
| 2 | team DB | pgTAP: il motivo porta i `valori` della check | §4 | 1 |
| 3 | Tid | apply e corsa pgTAP | — | 2 |
| 4 | Tid | collaudo a video: il tooltip della «Conferma» porta i numeri | [collaudo bolla e reso](collaudo-in-app-magazzino-bolla-e-reso.md) §5.3, §5.7 | 3 |
| 5 | sessione BE | archiviare in `work-done/` | — | 4 |

**Decisioni aperte di Tid:** nessuna.
**Da committare:** il §5 di questo brief (analisi DB del 2026-10-13).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-13, dal giro B2 del
> [piano BE/FE del Lotto 3](piano-be-fe-magazzino-lotto-3.md) (3-bis R-1c). **A chi:** team DB.
> Nessuna ricaduta su BE e FE: leggono gia' la forma richiesta.

---

## 1. Il difetto

`script.fn_available_actions_reso` disabilita la transizione a `CONFERMATO` col primo motivo di
`script.fn_check_reso_merce` (3-bis P-6), ma ne porta solo `reason` e `reason_key`
(doc auto-gen di `fn_available_actions_reso`, i due `CASE` su `v_motivo_merce`). I **`valori`** del
motivo, che la check costruisce, si perdono.

Due delle frasi hanno segnaposti:

* `vendite.reso.azione_reason.rientri_incompleti` — «Riga {0} del reso: indicati {1} pezzi su {2}…»;
* `vendite.reso.azione_reason.rientro_oltre_uscito` — «Riga {0} del reso: rientrerebbero {1} pezzi…
  da cui ne erano usciti {2}…».

A video il tooltip della «Conferma» esce con `{0}`, `{1}`, `{2}` al posto dei numeri: l'operatore legge
che una riga e' incompleta senza sapere quale ne' di quanto.

## 2. La forma che esiste gia': la bolla

`script.fn_available_actions_ddt` sull'azione `EMESSO` porta, oltre a `reason`/`reason_key` del primo
motivo, l'elenco intero **`reasons`** (gli oggetti della check, coi loro `valori`), quando ce n'e'
almeno uno. Il frontend lo legge gia' per tutti i documenti (`core/composables/useDrawerActions.js`,
`testoMotivi`: `reasons` se c'e', altrimenti l'azione stessa; `valori` → segnaposti `{0}`, `{1}`).

## 3. La richiesta

Sull'azione `CONFERMATO` del reso, la chiave **`reasons`** con il risultato di
`script.fn_check_reso_merce(v_reso)` quando non e' vuoto, come fa la bolla con `v_motivi`. Oggi la
funzione ne legge solo l'elemento `-> 0` (`v_motivo_merce`): basta tenere l'array intero e derivare da
lui il primo motivo, cosi' le due letture non si separano.

⚠️ La precedenza fra motivi resta quella dichiarata (accrediti, poi righe, poi merce): `reasons` porta i
soli motivi della merce, e solo quando sono loro a spegnere l'azione (se parla prima un accredito o
l'assenza di righe, `reasons` non va messo, o il tooltip mostrerebbe il motivo sbagliato).

## 4. Prova

Un pgTAP che costruisce un reso con rientri incompleti (una riga di reso con due prelievi d'origine e un
solo rientro parziale) e verifica che l'azione `CONFERMATO` porti `reasons -> 0 -> 'valori'` con numero
di riga, indicati e attesi. Il caso si **costruisce**: nessun reso di dbdev lo garantisce.

## 5. Analisi del team DB (2026-10-13)

> Scritta prima del codice, su indicazione di Tid. Il corpo vivo e' quello della doc auto-generata
> ([fn_available_actions_reso](../../dbzero/script/funzioni/fn_available_actions_reso.md)), che
> corrisponde all'ultimo changeSet `20261010-76`.

### 5.1 Lo stato di oggi

* `fn_available_actions_reso`, solo in `DRAFT`: `v_motivo_merce := script.fn_check_reso_merce(v_reso) -> 0`.
  Dal motivo prende `reason` e `reason_key` nei due `CASE` dell'azione; `valori` e l'array si perdono.
* `fn_check_reso_merce` restituisce `[]` oppure un array con **un solo** motivo (si esce al primo):
  `{codice, reason, reason_key, dettaglio, valori}`. `reasons` sara' quindi sempre lungo uno: e' la
  forma della bolla, non una lista da paginare.
* La bolla (`fn_available_actions_ddt`): `v_motivi := script.fn_check_ddt_emittibile(v_ddt)`, il primo
  motivo derivato da `v_motivi -> 0`, e sull'azione `EMESSO`
  `'reasons', CASE WHEN … AND jsonb_array_length(v_motivi) > 0 THEN v_motivi END` (la chiave c'e'
  sempre, `null` quando non serve). Il frontend legge gia' questa forma.

### 5.2 Il cambio

1. Una variabile per l'array intero (`v_motivi_merce jsonb := '[]'`), riempita in `DRAFT`;
   `v_motivo_merce` diventa `v_motivi_merce -> 0`, cosi' le due letture non si separano (§3).
2. Sull'oggetto azione la chiave `reasons`, con la stessa forma della bolla:
   `v_motivi_merce` quando l'azione e' `CONFERMATO`, c'e' un motivo della merce **e** a spegnere
   l'azione non e' un motivo che lo precede; altrimenti `null`.

⚠️ **La precedenza va scritta nella condizione di `reasons`, non lasciata al caso.** Sulla
transizione a `CONFERMATO` l'unico motivo che puo' precedere la merce e' «documento senza righe»
(`requires_righe`, dichiarato dalla transizione `conferma` nel seed di `config.transizioni_stati_reso`, e nessuna riga attiva); quello degli accrediti
riguarda solo `ANNULLATO`. Fatto di struttura (2026-10-13): **oggi i due non si incontrano**, perche'
`fn_check_reso_merce` esce con `[]` quando il reso non muove merce (`vendite.fn_reso_muove_merce`:
serve una riga attiva con prelievi d'origine), e lo dice gia' il commento del corpo («con zero righe
non ci sono voci»). Ma e' un incastro fra due funzioni, non una regola: se un giorno la check
guardasse il magazzino prima delle righe, `reasons` porterebbe un motivo accanto a
`reason` = `DOCUMENTO_SENZA_RIGHE`, e il tooltip mostrerebbe quello sbagliato. Condizione:

```text
CONFERMATO  AND  v_motivo_merce IS NOT NULL
            AND  NOT (requires_righe AND NOT v_ha_righe)
```

⭐ E' la stessa condizione che decide `reason` (il ramo merce del `CASE` arriva solo dopo quello
delle righe): conviene scriverla una volta sola nel corpo e leggerla in `enabled`, `reason`,
`reason_key` e `reasons`, cosi' i quattro campi non possono dissentire.

3. Il `COMMENT ON FUNCTION` riscritto con la revisione, e la pagina `manual/` se c'e'.

Niente codici d'errore nuovi, niente chiavi i18n nuove (le frasi coi segnaposti esistono gia');
nessuna ricaduta su BE e FE (lo dice gia' la nota «Chi scrive» in cima).

### 5.3 La prova

[`magazzino/test-reso-carico-v1.sql`](../../../../db/pgtap/magazzino/test-reso-carico-v1.sql) costruisce
gia' il caso: al passo 3 la riga a lotti ha due prelievi e nessun rientro
(`E_RESO_RIENTRI_INCOMPLETI`), al passo 4 legge la capability. Lo si estende li', accanto al 4:

* `reasons -> 0 ->> 'reason'` = `RIENTRI_INCOMPLETI`, e `reasons -> 0 -> 'valori'` porta numero di
  riga, pezzi indicati e pezzi attesi (i valori della fixture, non quelli di un reso di dbdev);
* dopo i rientri completi (passo 6): `reasons` e' `null` e l'azione e' abilitata;
* un caso **costruito**: reso senza righe e senza magazzino. `reason` = `DOCUMENTO_SENZA_RIGHE`
  e `reasons` `null`. ⚠️ Dichiarato come **presidio**:
  oggi e' verde anche senza la condizione del §5.2, perche' la check della merce con zero righe non
  parla; diventa rosso il giorno in cui l'incastro si rompe, che e' quello che deve sorvegliare.

⚠️ Il caso «rientro oltre l'uscito» ha anche lui i segnaposti, ma la forma e' la stessa: il primo
caso prova il trasporto dei `valori`, non serve ripeterlo per ogni motivo.

