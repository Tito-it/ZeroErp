# Brief DB — Emittente DDT legato allo user + etichetta emittente dal soggetto

> **Stato: ✅ CHIUSO (2026-07-13)** — realizzato dal team DB su `dev/db-tid` e
> verificato sul DB di sviluppo: trigger `default_emittente` su DDT (soft:
> niente raise, fallback-da-BA preservato; skip evasione) + `guard_emittente_ba`
> su DDT (fase z10, post-normalize) e guard esteso anche a preventivi/offerte;
> `emittente_fiscale_descrizione` esposta dalle 5 viste lista; 5 seed colonna
> "Emittente" ribinati a `campo_sorgente=emittente_fiscale_descrizione`
> (codice colonna invariato: nessun impatto preset/preferenze). Recepito lato
> BE (stesso giorno): JOIN ridondanti rimossi dai detail DDT/ordini; codici
> `E_{ORDINE,CONTRATTO,DDT,PREV,OFFERTA}_EMITTENTE_BA_INCOERENTE` registrati
> in `error_policies.py` (409, highlight campi — ordini/contratti erano un
> gap preesistente). Il fix dati suggerito al §4 NON è stato applicato
> (decisione DB team: le viste mostrano comunque la ragione sociale).
>
> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-13 · **Owner**: Tid
> **Contesto**: decisione Tid 2026-07-13 — l'emittente fiscale è SEMPRE legato
> allo user (modello 1-a-1 operatore→emittente), su tutti i domini documento;
> e l'etichetta dell'emittente mostrata all'operatore è SEMPRE la ragione
> sociale del SOGGETTO emittente, mai il codice tecnico del record
> `emittenti_fiscali` (caso emerso: gestore default di sviluppo con codice
> auto-generato `PGTAP-EF-20260126172242554`).
>
> Lato BE/FE (già fatto su `dev/backend-tid`, stessa data): il create DDT ora
> accetta `emittente_fiscale_id` nel payload con prefill FE dal profilo
> operatore (mirror ordini); i detail DDT/ordini denormalizzano
> `emittente_fiscale_descrizione` = `COALESCE(s_ef.ragione_sociale_completa,
> ef.descrizione)` (convenzione già usata da preventivi/offerte/contratti).

## 1. Simmetria trigger emittente su `vendite.ddt`

Oggi il DDT è l'unico dominio documento SENZA i due trigger emittente che
ordini/contratti (e in parte preventivi) hanno:

| Trigger | Ordini | Contratti | Preventivi | DDT |
| --- | --- | --- | --- | --- |
| `trgfn_*_default_emittente` (payload NULL → GUC `app.current_user_id` → `fn_resolve_emittente_for_user`) | ✅ | ✅ | ✅ | ❌ |
| `trgfn_*_guard_emittente_ba` (coerenza `emittente_fiscale_id` = `fn_get_emittente_fiscale_pk(billing_account_id)`) | ✅ | ✅ | ❌ | ❌ |

Richiesta:

1. **`trgfn_ddt_default_emittente`** mirror ordini, con UNA differenza:
   deve **saltare i DDT da evasione** (NEW.sorgente_tipo_id/sorgente_uid
   valorizzati): lì l'emittente si eredita dall'ordine sorgente in
   `trgfn_ddt_normalize` (ereditarietà da preservare). Inoltre, a differenza
   di ordini, se la GUC non risolve (admin globale) NON sollevare: lasciare
   NULL e far agire il fallback-da-BA già presente in `trgfn_ddt_normalize`
   (comportamento attuale per lo standalone senza payload, da conservare).
   Ordine di firing: prima del ramo fallback-BA del normalize.
2. **`trgfn_ddt_guard_emittente_ba`** mirror esatto di
   `trgfn_ordini_guard_emittente_ba` (skip se BA NULL, errore
   `E_DDT_EMITTENTE_BA_INCOERENTE`). Chiude il buco: col payload ora aperto
   lato BE, senza guard un emittente divergente dal BA verrebbe memorizzato
   (su ordini verrebbe rifiutato).
3. (Ricognizione, non bloccante) valutare il guard `_emittente_ba` anche su
   **preventivi** e **offerte** per simmetria piena.

## 2. Viste lista: esporre `emittente_fiscale_descrizione`

Le 5 viste `vw_preventivi_lista` / `vw_offerte_lista` / `vw_contratti_lista` /
`vw_ordini_lista` / `vw_ddt_lista` espongono oggi solo
`ef.codice AS emittente_fiscale_codice` (JOIN a `emittenti_fiscali` già
presente). Aggiungere a TUTTE e 5:

```sql
COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)
    AS emittente_fiscale_descrizione
-- con: LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
--      LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
```

Nota: i detail BE di DDT e ordini calcolano oggi lo stesso campo con JOIN
proprio sopra la vista (`SELECT v.*, COALESCE(...)`). Quando le viste lo
esporranno, quei JOIN BE diventano ridondanti e verranno ritirati (ce ne
occupiamo noi lato BE, nessuna azione DB).

## 3. Seed `ui.lista_colonna`: colonna "Emittente" → descrizione

Le 5 colonne "Emittente" (contratti/preventivi/offerte/ordini id 122/DDT
id 147) bindano `emittente_fiscale_codice` → l'operatore vede
`PGTAP-EF-20260126172242554` invece di "Gestore Test pgTAP". Aggiornare le 5
righe seed:

| Campo | Nuovo valore |
| --- | --- |
| codice / campo_sorgente | `emittente_fiscale_descrizione` |
| etichetta_estesa | "Ragione sociale dell'emittente fiscale" |
| resto | invariato (opt-in, mai nei preset, string, filtrabile/ordinabile/esportabile) |

Prerequisito: punto 2 (il campo deve esistere nelle viste).

## 4. Nota dati di sviluppo (non è una richiesta di migration)

Il gestore default del DB di sviluppo è un residuo pgTAP del 2026-01-26:
`emittenti_fiscali` id 32 → `codice='PGTAP-EF-20260126172242554'`,
`descrizione='Emittente fiscale test 1'` (il soggetto collegato è corretto:
"Gestore Test pgTAP"). Il codice compare tra parentesi nelle label
"ragione sociale (codice)". Suggerito fix manuale dei dati (decisione Tid):

```sql
UPDATE anagrafiche.emittenti_fiscali
   SET codice = 'GESTORE-TEST', descrizione = 'Gestore Test pgTAP'
 WHERE id = 32;
```
