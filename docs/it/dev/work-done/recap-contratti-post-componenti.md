# Recap Contratti — Rivalutazione post refactor componenti BoM

> **Data**: 2026-05-15
> **Scope**: analisi dello stato corrente del dominio contratti dopo l'atterraggio
> del modello unificato componenti BoM (Fase G-contratti BE+FE done 2026-05-14).
> Identifica i bug logici emersi e propone il piano di chiusura.
>
> **Riferimenti**:
>
> - Modello componenti: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md) §9.5
> - Piano operativo refactor: [`refactor-componenti.md`](refactor-componenti.md)
> - API contratti: [`api_contratti.md`](../../backend/vendite/manual/api_contratti.md)

---

## 1. Le 3 modalità contratto v5 — definizione canonica

Da [`api_contratti.md`](../../backend/vendite/manual/api_contratti.md) §"Scopo":

| Modalità | `listino_id` | `tipo_variazione_globale` | `contratti_righe` |
|---|---|---|---|
| **A** — listino + variazione globale | NOT NULL | NOT NULL | vuote o override mirati |
| **B** — listino con override | NOT NULL | NULL | righe con `prezzo_unitario` per articoli specifici |
| **C** — interamente negoziato | NULL | NULL | tutte le righe con `prezzo_unitario` NOT NULL |

**Chiave**: la modalità è definita dalla **testata** (`listino_id` + `tipo_variazione_globale`),
non dalla presenza di righe.

## 2. Cosa è cambiato col modello componenti BoM (2026-05-13)

Il refactor componenti ha introdotto il pattern "BoM contratto immutabile per documento"
(modello §9.3): un articolo `is_composito=TRUE` inserito in un contratto richiede sempre:

1. Una **riga padre** in `contratti_righe` con `prezzo_unitario` = SUM(figli × coeff)
2. N **righe figlie** in `contratti_righe_componenti` (auto-init via
   `fn_contratto_riga_componenti_init`, tutte `attivo=TRUE`)

Conseguenza non documentata altrove: **i compositi non possono restare puramente DA_LISTINO**.
Esistono sempre come record `contratti_righe` (con eventuale override sui prezzi figlio).
La denormalizzazione `is_composito` (Fase G done 2026-05-14, working tree) la espone in
`/righe/` per il driver FE di detection.

## 3. Bug logici identificati

### 3.1 BE deriva modalità dai dati invece che dalla testata — BUG PRIORITÀ MASSIMA

[`contratti_service.list_righe_preview`](../../../../backend/apps/vendite/services/contratti_service.py#L780-L788):

```python
listino_id = contratto.get("listino_id")
preview_rows = self._repo.list_righe_preview(contratto_id) if listino_id else []
if listino_id is None:
    modalita = "C"
else:
    has_overrides = any(r.get("origine") == "OVERRIDE" for r in preview_rows)
    modalita = "B" if has_overrides else "A"
```

**Bug**: la modalità A vs B è dedotta dalla **presenza di OVERRIDE** nelle righe,
non da `tipo_variazione_globale`. Era già sbagliato pre-componenti (ignorava la testata),
ma post-componenti diventa **sistematicamente errato** perché ogni articolo composito nel
listino genera necessariamente un OVERRIDE nel contratto → la modalità A "collassa" in B
appena entra in gioco un composito.

**Sintomo riportato da Tid** ("ho selezionato A ma vedo B nella gestione righe"):
il banner contesto del `ContrattoRigheDrawer` mostra `previewMeta.modalita = 'B'` ricevuto
dal BE, sovrascrivendo `props.contrattoModalita = 'A'` derivato correttamente dalla testata
in `ContrattoDrawer.deriveModalita` ([`ContrattoDrawer.vue:199-202`](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L199-L202)).

**Fix**: derivare la modalità in `list_righe_preview` come fa il FE, leggendo
`contratto.tipo_variazione_globale`:

```python
if listino_id is None:
    modalita = "C"
elif contratto.get("tipo_variazione_globale"):
    modalita = "A"
else:
    modalita = "B"
```

Drop completo del check sui dati: si elimina anche la query di conteggio override.

### 3.2 FE: row actions "modifica/elimina" visibili solo su composito — SINTOMO 3.1

[`ContrattoRigheDrawer.vue:484-500`](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L484-L500) (`buildRigaActions`)
e [:319-371](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L319-L371) (`onRowSelect`):

Entrambi gatecheckano su `data.origine === 'DA_LISTINO' → return []/return` (read-only).
**Per design coerente**: le righe DA_LISTINO sono preview pure (no record contratti_righe
dietro), non si possono UPDATE/DELETE.

Sintomo apparente "elimina solo su composito": ovvio col bug 3.1.
I compositi sono OVERRIDE (per auto-init), quindi hanno azioni. I non-compositi restano
DA_LISTINO finché nessuno crea un override.

**Decisione di dominio aperta** (vedi §4.1): in modalità A/B, l'operatore deve poter
"forzare" un override su un articolo del listino dal drawer righe? Oggi può solo
"aggiungere riga nuova" (che diventa OVERRIDE) — non c'è UX per "modifica questo
listino in override".

### 3.3 FE: default prop `contrattoModalita: 'B'` mascherante

[`ContrattoRigheDrawer.vue:52`](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L52):

```js
contrattoModalita: { type: String, default: 'B' },
```

Se per qualunque motivo il parent non passa la prop, il drawer assume B silentemente.
Non è la causa del bug riportato (`ContrattoDrawer` passa correttamente `:contratto-modalita="form.modalita"`),
ma è una time-bomb. Meglio `default: null` e fallback esplicito dopo fetch preview.

### 3.4 FE: `rowClass` blocca DA_LISTINO anche post-fix 3.1

[`ContrattoRigheDrawer.vue:134-138`](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L134-L138):

```js
function rowClass(data) {
  if (isReadonly.value) return 'app-row-readonly'
  if (data?.origine === 'DA_LISTINO') return 'app-row-readonly'
  return null
}
```

Classe CSS che marca readonly. Allineato con `buildRigaActions` + `onRowSelect`. Se cambia la
decisione di dominio sull'editabilità delle DA_LISTINO, va aggiornato qui.

## 4. Domande di dominio aperte

### 4.1 Editabilità delle righe DA_LISTINO

Oggi: read-only assoluto. UX per "creare override su questa riga listino" non esiste —
l'operatore deve aggiungere riga nuova con stesso articolo (e il BE la classifica OVERRIDE).

Tre opzioni:

- **(a)** Mantenere read-only assoluto, ma esplicito: tooltip "questa riga viene dal listino,
  per personalizzarla usa il pulsante 'Crea override' nella row action".
  Aggiungere row action `crea_override` che pre-popola il form in CREATE con i valori della
  riga listino.
- **(b)** Click su riga DA_LISTINO apre il form in EDIT pre-popolato (semantica: crea override).
  Al save crea una contratti_righe OVERRIDE per quell'articolo. Comportamento implicito.
- **(c)** "Elimina" su DA_LISTINO crea un OVERRIDE inattivo (esclusione esplicita).
  Richiede un campo `escluso` o l'uso di `attivo=false` su contratti_righe come marker
  "esclusione dal listino". Modello DB da estendere.

Inclinazione: **(a) + (c) combinato** evita ambiguità semantica e simmetria col preventivo.
Da decidere prima di toccare il FE.

### 4.2 Modalità A vs B in presenza di compositi

In modalità A, ogni composito nel listino genera un OVERRIDE automatico. Il contratto resta
intent-A, ma c'è una contratti_righe per ogni padre composito. È OK? Sì, ma è una sfumatura
da documentare in `modello-componenti-bom.md` §9.5.

Da chiarire: in A, il `prezzo_unitario` del padre composito è SUM(figli con prezzo override)
o SUM(figli con prezzo bundle da listino)? Oggi: bundle dal listino via `STADIO 0` resolver.
Se il bundle non esiste in `listini_righe_componenti`, fallback a STADIO 1 standalone su
ogni figlio. Funziona, ma il listino bundle dovrebbe esistere per design.

### 4.3 Default modalità form CREATE contratto

Oggi `paramString(p.VENDITE_CONTRATTO_DEFAULT_MODALITA, 'A')`. Da verificare se il parameter
è seedato. Se NULL → default 'A' hard-coded. Coerente con la UX più comune (listino + sconto)?
Sì.

## 5. Piano proposto

| # | Cosa | Effort | Dipendenza |
|---|---|---|---|
| 1 | **Fix BE 3.1** — `list_righe_preview.modalita` da `tipo_variazione_globale` | 30 min + test | nessuna |
| 2 | **Fix FE 3.3** — `contrattoModalita: default null` + fallback esplicito | 10 min | 1 |
| 3 | **Decisione di dominio §4.1** — UX editabilità DA_LISTINO (a/b/c) | sessione Tid | — |
| 4 | **Refactor FE row actions** secondo decisione §4.1 | 1h + smoke | 3 |
| 5 | **Doc** — aggiornare `modello-componenti-bom.md` §9.5 con la sfumatura "composito in modalità A genera OVERRIDE implicito" | 15 min | — |
| 6 | **Smoke UI** — verificare A/B/C con e senza compositi, override manuali, attivazione | 1 sessione | 1+2+4 |

Ordine consigliato: **1 → 2 → 5** subito (fix tecnici senza decisioni di dominio); **3 → 4 → 6**
in una sessione successiva quando Tid ha tempo per la decisione UX.

## 6. Test attuali da rivedere

`backend/apps/vendite/tests/services/test_contratti_service.py` ha test su `list_righe_preview`
che dovrebbero verificare:

- `listino_id=NULL → modalita='C'` (OK già)
- `listino_id=X + tipo_variazione_globale='PERCENTUALE' → modalita='A'` (**MANCANTE: oggi
  test passa solo se preview non ha OVERRIDE — falso positivo**)
- `listino_id=X + tipo_variazione_globale=NULL → modalita='B'` (**MANCANTE: oggi test passa
  solo se preview ha OVERRIDE — falso positivo**)
- Composito in modalità A produce 1 OVERRIDE ma `modalita` resta 'A' (**MANCANTE: regression
  guard sul bug 3.1**)

Da estendere col fix #1.

## 7. Non in scope di questo recap

- Modalità C "puro contratto": funziona stabilmente, non toccata dal refactor componenti
  (i compositi in C seguono lo stesso pattern padre+figli, prezzi tutti manuali).
- Stato cessazione data-driven: già done 2026-04-26, non impattato.
- Documenti contratto (PDF generation): orthogonale.
- Pricing approvazioni L3: orthogonale.

---

**Prossimo passo concreto**: applico fix #1 + #2 + #5 (tecnici, no decisioni dominio).
Per #3 attendo input Tid sulla UX preferita.
