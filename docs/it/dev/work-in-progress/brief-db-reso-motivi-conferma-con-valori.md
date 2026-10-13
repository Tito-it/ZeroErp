# Brief DB — i motivi della «Conferma» del reso arrivano senza i numeri

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: il team DB** (`dev/db-tid`): un changeSet su `script.fn_available_actions_reso` (§3).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | `reasons` con i `valori` sull'azione CONFERMATO, come la bolla | §3 | — |
| 2 | team DB | pgTAP: il motivo porta i `valori` della check | §4 | 1 |
| 3 | Tid | apply e corsa pgTAP | — | 2 |
| 4 | Tid | collaudo a video (blocco B del piano BE/FE): il tooltip della «Conferma» porta i numeri | — | 3 |
| 5 | sessione BE | archiviare in `work-done/` | — | 4 |

**Decisioni aperte di Tid:** nessuna.
**Da committare:** niente (il brief e' in git dal 2026-10-13).

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
