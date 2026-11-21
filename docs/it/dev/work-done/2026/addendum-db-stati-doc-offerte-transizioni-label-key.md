# Addendum brief DB — label_key seed `stati_doc_offerte_transizioni`

> **Stato**: bug minore UX (i18n) in dev. Da fixare sul branch
> `dev/db-tid`.
> **Data segnalazione**: 2026-05-26 (dopo fix `??` JSONB e smoke utente).
> **Sorgente**: errore visibile nei pulsanti DrawerActionsBar offerta —
> appare il path `offerte.azione_emetti` / `offerte.azione_annulla` invece
> della label tradotta italiana ("Emetti" / "Annulla offerta").

---

## 1. Sintomo

Dopo il fix del bug operatore `??` (addendum precedente), la fn
`script.fn_available_actions_offerta` ora ritorna correttamente
`available_actions[]`. Pero' i pulsanti nella `DrawerActionsBar`
mostrano la chiave i18n grezza invece del testo:

```text
[ offerte.azione_emetti ]   [ offerte.azione_annulla ]
```

invece di:

```text
[ Emetti ]   [ Annulla offerta ]
```

## 2. Causa

Il seed `stati_doc_offerte_transizioni.csv` ha `meta.label_key` valorizzato
**senza il prefix `vendite.`** richiesto dalle chiavi i18n FE. Il FE chiama
`t(action.label_key)` con vue-i18n: se la chiave passata e'
`offerte.azione_emetti` ma in `frontend/src/locales/it.json` la chiave
valida e' `vendite.offerte.azione_emetti`, vue-i18n non trova match e
restituisce la stringa **letterale** (= path key).

Il brief originale `brief-db-fn-available-actions-offerta.md` §2.3
specificava chiaramente il prefix completo:

> **Chiavi `label_key` i18n** (già esistenti in
> `frontend/src/locales/it.json` → `vendite.offerte.*`):
>
> | Azione           | `label_key` |
> |------------------|---|
> | `emetti`         | `vendite.offerte.azione_emetti` |
> | `annulla`        | `vendite.offerte.azione_annulla` |
> | `accetta`        | `vendite.offerte.azione_accetta` |
> | `rifiuta`        | `vendite.offerte.azione_rifiuta` |
> | `crea_revisione` | `vendite.offerte.azione_crea_revisione` |
> | `push_contratto` | `vendite.offerte.azione_push_contratto` |

Il `vendite.` non e' stato riportato nel seed durante l'applicazione.

## 3. Fix richiesto

Aggiornare il seed `stati_doc_offerte_transizioni.csv` (o equivalente
seed dei meta delle transizioni) sostituendo:

| Prima (bug)             | Dopo (corretto)                  |
|-------------------------|----------------------------------|
| `offerte.azione_emetti` | `vendite.offerte.azione_emetti`  |
| `offerte.azione_annulla`| `vendite.offerte.azione_annulla` |
| `offerte.azione_accetta`| `vendite.offerte.azione_accetta` |
| `offerte.azione_rifiuta`| `vendite.offerte.azione_rifiuta` |

(Stesso pattern se nel seed esistono righe per `crea_revisione` /
`push_contratto`, ma quelle sono hardcoded nella fn — vedi brief
originale §2.6 — quindi probabilmente il bug si limita ai 4 cambi-stato
manuali sopra.)

**Anche `label_key` della fn hardcoded**: se la fn `fn_available_actions_offerta`
costruisce le entry "speciali" `crea_revisione` e `push_contratto` con
`label_key` hardcoded come `'offerte.azione_crea_revisione'` e
`'offerte.azione_push_contratto'`, queste **vanno corrette nella fn**
anch'esse (devono diventare `'vendite.offerte.azione_crea_revisione'` e
`'vendite.offerte.azione_push_contratto'`).

Bisogna verificare entrambi i punti (seed CSV e body della fn) e
aggiornare quello che serve.

## 4. Sequenza

1. Aggiornare `stati_doc_offerte_transizioni.csv` (4 righe meta) col
   prefix `vendite.` sulle `label_key`. Il seed e' `runOnChange: true /
   validCheckSums: ANY`, quindi Liquibase lo riapplica al prossimo
   `make db-migrate`.
2. Aggiornare la fn `script.fn_available_actions_offerta` se contiene
   `label_key` hardcoded senza prefix (controllo + eventuale migration
   `runOnChange: true` su nuovo numero progressivo).
3. Aggiungere un test pgTAP che verifica che TUTTE le `label_key` nel
   blob ritornato dalla fn inizino per `vendite.offerte.`:

   ```sql
   PREPARE check_label_key AS
     SELECT bool_and(
       (act->>'label_key') LIKE 'vendite.offerte.%'
     )
     FROM jsonb_array_elements(
       script.fn_available_actions_offerta(<id_bozza_fixture>)
         -> 'available_actions'
     ) AS act;
   SELECT ok(
     (SELECT EXECUTE check_label_key),
     'tutte le label_key hanno prefix vendite.offerte.'
   );
   ```
4. `make db-migrate` locale.
5. Push su `dev/db-tid`.

## 5. Impatto BE / FE

**Nessuna modifica BE/FE necessaria**: il FE chiama gia' correttamente
`t(action.label_key)`; non appena la chiave corretta arriva dal BE
(post-fix DB), vue-i18n risolve la traduzione e i pulsanti mostrano
"Emetti" / "Annulla offerta" / etc. — niente cambio codice applicativo.

## 6. Cosa NON cambiare

- L'`action.key` (es. `'emetti'`, `'annulla'`) resta semantico/stabile
  per il dispatch FE (`onActionDispatch(action.key)` switch). E' una
  chiave macchina, non un path i18n.
- L'`action.target_state` (es. `'EMESSA'`, `'ANNULLATA'`) resta uguale
  per coerenza con `config.stati_doc_offerte.codice_interno`.

---

*Addendum DB — fix prefix `vendite.` su `label_key` seed transizioni.
Tempo stimato: 5 minuti (CSV + eventuale fn). Pronto per applicazione
su `dev/db-tid`.*
