# Brief DB — Esito configurabile sugli step di flusso (`template_flussi`)

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟢 normale — prerequisito per il lavoro BE/FE (che attende le colonne).
> **Data**: 2026-06-17 · **Stato**: 🟡 da applicare.
>
> **Design autorevole**: [brief-design-esito-configurabile-flussi.md](brief-design-esito-configurabile-flussi.md)
> (modello, razionale invarianti, piano BE/FE). Questo brief contiene **solo** ciò che
> serve a DB: DDL, CHECK, guard, pgTAP, seed di test.

---

## 1. Contesto

Lo step di flusso (`pratiche.flussi`) ha `stato_id` ed `esito` separati; l'esito è
obbligatorio al COMPLETATO via trigger `pratiche.trgfn_flussi_guard_esito_completato`
(errore `FLUSSI_ESITO_OBBLIGATORIO`). Oggi non esiste alcuna configurazione che permetta
allo step di auto-risolvere l'esito o di registrarlo contestualmente all'avvio. Si
aggiunge una configurazione **sul template** (`pratiche.template_flussi`) per governarlo.

## 2. Modifiche schema — `pratiche.template_flussi`

Aggiungere **due colonne** (nuova migration `00_schema/pratiche/`):

| Colonna | Tipo | Null | Default | Vincolo |
|---|---|---|---|---|
| `modalita_esito` | `varchar(20)` | NOT NULL | `'MANUALE'` | CHECK ∈ (`MANUALE`,`AUTOMATICO`,`CONTESTUALE`) |
| `esito_default` | `varchar(20)` | NULL | NULL | CHECK ∈ (`POSITIVO`,`NEGATIVO`,`PARZIALE`,`NON_APPLICABILE`) — stesso dominio di `flussi.esito` |

NOT NULL con default `'MANUALE'` → backfill implicito di tutti gli step esistenti a
comportamento odierno (nessuna regressione).

### CHECK di coerenza (tabella `template_flussi`)

```sql
-- Invariante 1: un automatismo deve sapere quale esito scrivere.
ALTER TABLE pratiche.template_flussi
  ADD CONSTRAINT chk_template_flussi_esito_default_required
  CHECK (modalita_esito = 'MANUALE' OR esito_default IS NOT NULL);

-- Invariante 2: solo gli step a direzione INTERNA possono auto-risolversi senza
-- intervento umano (AUTOMATICO). CONTESTUALE è libero da vincolo di direzione.
ALTER TABLE pratiche.template_flussi
  ADD CONSTRAINT chk_template_flussi_automatico_solo_interna
  CHECK (modalita_esito <> 'AUTOMATICO' OR direzione = 'INTERNA');
```

> Nota: i CHECK vivono su `template_flussi` (dati di configurazione, scritti raramente),
> non sui flussi runtime → fail-fast al disegno del template, costo zero a runtime.
> Valutare se l'errore deve essere "parlante" via messaggio dedicato (vedi §4).

## 3. Trigger guard esito al COMPLETATO — adattamento

`pratiche.trgfn_flussi_guard_esito_completato` oggi solleva `FLUSSI_ESITO_OBBLIGATORIO`
se `esito IS NULL` al passaggio a COMPLETATO. **Va lasciato così**: BE e CONTESTUALE/
AUTOMATICO valorizzano sempre `esito` prima/contestualmente al COMPLETATO (il service
passa `esito_default` o l'esito confermato dall'operatore). Il guard resta la rete di
sicurezza fail-closed. **Nessuna modifica necessaria** salvo verifica che la
valorizzazione automatica lato BE arrivi nello stesso UPDATE (lo fa: `update_stato_flusso`
scrive `esito` e `stato_id` insieme).

→ Da confermare lato DB: il guard non deve assumere il passaggio da IN_CORSO. Le nuove
modalità completano sempre dopo essere passate da IN_CORSO nella stessa transazione
(la matrice `config.transizioni_stati_flussi_pratiche` **non** ha la transizione diretta
DA_ESEGUIRE→COMPLETATO e **non** va aggiunta: il percorso resta 1→2→3).

## 4. Codice errore parlante (opzionale ma consigliato)

Per i due CHECK di §2, valutare un messaggio dedicato in `config.messaggi_errore` +
mapping BE, così il drawer di amministrazione template mostra un errore chiaro invece
del violation grezzo del CHECK. Proposta codici:

- `TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO` — invariante 1.
- `TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA` — invariante 2.

(Allineato al pattern dei guard parlanti dei flussi, es. id 493
`PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE`.) Se preferite tenere il CHECK grezzo in
prima battuta, va bene: il BE può comunque pre-validare. Confermare la scelta.

## 5. Proiezioni lette dal BE

Il BE leggerà `modalita_esito`, `esito_default` (e `direzione`) dalle join già esistenti
su `template_flussi` nelle query `list_flussi`/`get_flusso`/`get_percorso_pratica`
(lato Python, nessuna vista DB da toccare). Nessuna view/funzione DB aggiuntiva
richiesta per esporre questi campi.

## 6. Seed di test — template preventivi (changeset separato, attivabile)

`runOnChange` upsert su `pratiche.template_flussi` per i 4 step preventivi
(tipo_prestazione 9002/9003), come da [design §3](brief-design-esito-configurabile-flussi.md):

| Step | direzione | `modalita_esito` | `esito_default` |
|---|---|---|---|
| `RICHIESTA_CLIENTE` | ENTRATA | `CONTESTUALE` | `POSITIVO` |
| `PREVENTIVAZIONE` | INTERNA | `MANUALE` | NULL |
| `APPROVAZIONE_CLIENTE` | ENTRATA | `MANUALE` (o `CONTESTUALE` se si vuole secondo test) | NULL / `POSITIVO` |
| `CONFERMA` | INTERNA | `AUTOMATICO` | `POSITIVO` |

Tenere il seed in un changeset **distinto** dal DDL: la feature è generale, la
configurazione preventivi è solo un banco di prova.

## 7. pgTAP

- `template_flussi`: insert AUTOMATICO + esito_default NULL → viola `chk_..._esito_default_required`.
- `template_flussi`: insert AUTOMATICO + direzione ENTRATA → viola `chk_..._automatico_solo_interna`.
- `template_flussi`: insert CONTESTUALE + direzione ENTRATA + esito_default valorizzato → OK.
- `template_flussi`: insert MANUALE + esito_default NULL → OK (default odierno).
- Regressione: `trgfn_flussi_guard_esito_completato` continua a bloccare COMPLETATO con
  esito NULL.

## 8. Criterio di accettazione DB

- Colonne presenti con default/CHECK; step esistenti restano `MANUALE`/NULL.
- I due CHECK rifiutano le combinazioni incoerenti; (se scelto) errori parlanti mappati.
- Matrice transizioni invariata; guard esito invariato e verde a pgTAP.
- Seed preventivi §6 applicabile e coerente coi CHECK.
