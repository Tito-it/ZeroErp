# Brief BE — rinominare i codici che il backend riconosce dal testo

**Chi scrive:** DB (`dev/db-tid`), 2026-08-05.
**Cosa chiede:** aggiungere i nuovi nomi `E_*` alle liste `known_markers` **prima**
che il DB rinomini — così i lotti non hanno bisogno di un rilascio simultaneo.
**Perimetro:** `apps/pratiche/services/pratiche_service.py` (23 codici su 27) più
tre file con un codice ciascuno.
**Origine:** [brief-db-codice-errore-strutturato](brief-db-codice-errore-strutturato.md) §15.11.

> **Non c'è niente di rotto adesso.** Questo brief serve a **non** romperlo: senza
> il passo qui sotto, i prossimi lotti di rinomina farebbero uscire dall'API un
> codice che il database ha già ritirato, e nessun test protesterebbe.

---

## 1. Dove siamo

I codici di `config.messaggi_errore` che non seguono `E_{MODULO}_{TIPO}` erano
**57** il 5 agosto. Oggi sono **39**: 6 cancellati perché morti, 12 rinominati e
ritirati con `obsoleto_dal`. Il metodo è rodato — tre lotti applicati, guardrail
verde, baseline invariata — e ogni lotto costa un `CREATE OR REPLACE` più due
celle di CSV.

Poi il cantiere ha incontrato un muro che non è tecnico ma di **coordinamento**.

---

## 2. Il muro: `known_markers` riconosce dal testo e restituisce il codice

In `pratiche_service.py` c'è una lista di coppie `(codice, marker)` passata a
`ErrorManager.raise_from_database_error`. Il marker è una **substring stabile del
messaggio** — scelta apposta per essere immune ai `%s`:

```python
("FLUSSI_COMPETENZA_MANCANTE", "non abilitato per il flusso"),
("FLUSSI_PRESA_NON_ELIGIBILE", "non consentita del flusso"),
```

⚠️ **Il problema non è che si rompa: è che non si rompe.** Se il DB rinomina
`FLUSSI_COMPETENZA_MANCANTE` in `E_FLUSSI_COMPETENZA_MANCANTE`:

* il **messaggio** non cambia — la rinomina tocca il codice, non il testo;
* il marker continua quindi a corrispondere;
* il backend restituisce il **vecchio nome**, che nel frattempo il database ha
  dichiarato **ritirato** (`obsoleto_dal`);
* nessun test fallisce, nessun log si accende. Il database dice una cosa, l'API
  ne dice un'altra, e la differenza non si vede da nessuna parte.

È la stessa forma di difetto che questo cantiere insegue dall'inizio: qualcosa
che **funziona per una ragione che nessuno ha progettato**.

---

## 3. Quanto è grande, e dov'è concentrato

Dei 39 codici ancora fuori convenzione, **27 sono nominati dal backend**. La
concentrazione è la buona notizia:

| Codici | File |
|---:|---|
| **23** | `apps/pratiche/services/pratiche_service.py` — la lista `known_markers` |
| 1 | `apps/pratiche/services/definizioni_service.py` |
| 1 | `apps/pratiche/api/views_definizioni.py` |
| 1 | `apps/vendite/services/approvazioni_prezzo_service.py` |
| 1 | `apps/core/services/db_error_fields.py` *(solo docstring, nessuna logica)* |

I restanti **12 sono DB-only** e il DB li rinomina da solo, senza chiedere nulla.

---

## 4. ⭐ La richiesta: rendere l'ordine irrilevante

Si potrebbe fare un rilascio simultaneo per ogni lotto. **Non serve**, e vale la
pena non farlo: la sincronia fra due repository e due server è una cosa che
prima o poi va storta.

La proprietà che ci salva è nel codice che avete appena scritto. In
`raise_from_database_error` il campo strutturato vince, **ma solo se il codice è
fra quelli dichiarati**:

```python
structured = structured_db_error_code(exc)
if structured is not None and any(c == structured for c, _ in known_markers):
    matched_code = structured
```

Quindi basta **dichiarare entrambi i nomi** per un po':

```python
("FLUSSI_COMPETENZA_MANCANTE",   "non abilitato per il flusso"),   # uscira'
("E_FLUSSI_COMPETENZA_MANCANTE", "non abilitato per il flusso"),   # nuovo
```

| Momento | Cosa arriva dal DB | Cosa succede |
|---|---|---|
| **prima** della rinomina | `FLUSSI_COMPETENZA_MANCANTE` (strutturato) | matcha la voce vecchia ✅ |
| **dopo** la rinomina | `E_FLUSSI_COMPETENZA_MANCANTE` (strutturato) | matcha la voce nuova ✅ |

**L'ordine di rilascio diventa indifferente**, e la finestra di disallineamento
sparisce. Il marker della voce nuova non deve nemmeno essere corretto: il campo
strutturato vince prima che il testo venga guardato. Lo si tiene uguale al
vecchio per non far pensare che sia un altro errore.

**In `error_policies.py`** serve la voce col nome nuovo, **stesso status** del
vecchio. ⚠️ Non rimuovete subito la vecchia: finché il DB non ha rinominato, è
quella che scatta.

### Poi, quando il lotto è applicato

Il DB avvisa a ogni lotto. Da quel momento la voce vecchia si può togliere — da
`known_markers` e da `error_policies.py` — e il codice esce definitivamente di
scena. Non c'è fretta: una voce di troppo non fa danno, è solo rumore.

---

## 5. ⚠️ Una cosa da sapere sui marker, per dopo

I marker esistono perché il codice **non arrivava**. Ora arriva (§3 del brief
principale), e per ogni errore sollevato via `script.fn_log_and_raise_error` il
marker è **peso morto**: il campo strutturato vince sempre prima.

Restano utili solo per i codici sollevati da un `RAISE EXCEPTION` diretto — ne
restano **135 in 46 funzioni** nel DB, ed è un cantiere a sé. Finché ci sono, i
marker non si possono togliere in blocco.

Ma quando toccate una di queste voci, **il marker non è più la parte che conta**:
se è sbagliato non se ne accorge nessuno, perché non viene quasi mai raggiunto.
Vale la pena saperlo prima di spendere tempo a raffinarlo.

---

## 6. Cosa fa il DB, e in che ordine

1. **DB**: continua sui 12 lotti DB-only — nessun coordinamento necessario;
2. **BE**: aggiunge i nomi nuovi a `known_markers` e `error_policies.py`
   (§4), quando volete: è retro-compatibile e non cambia nulla di visibile;
3. **DB**: appena il punto 2 è in `Tito-dev`, apre i lotti accoppiati, uno per
   funzione, avvisando a ciascuno;
4. **BE**: quando comodo, toglie le voci vecchie.

L'elenco puntuale dei 27 codici con i rispettivi file è ricavabile in ogni
momento — la fonte viva è il registro:

```sql
SELECT codice FROM dbops.messaggi_errore_codici_legacy ORDER BY 1;   -- 39 righe
```

e per sapere quali sono nominati dal Python basta cercarli in `backend/apps` con
i **confini di parola** — ⚠️ non con una `grep` semplice: cercando
`EMITTENTE_NON_MODIFICABILE` si trova anche `E_EMITTENTE_NON_MODIFICABILE`, ed è
un errore che in questo cantiere è già costato un giro (§7 del brief principale).

```bash
grep -rEl "(^|[^A-Z_])CODICE([^A-Z_]|$)" backend/apps --include='*.py'
```
