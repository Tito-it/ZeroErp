# Brief DB — Attivazione RLS scope Emittente Fiscale (operatori)

> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: brief di **logica e requisiti**, NON specifica implementativa. Qui c'è *cosa* serve e *perché*; la **strada implementativa (firme, linguaggio, struttura changeset, nomi) la sceglie il team DB**.
> **Origine**: [analisi-attivazione-rls-operatori.md](analisi-attivazione-rls-operatori.md) (analisi completa, decisioni §11, rischi §6, verifiche §3). Le sigle `C#`/`R#`/`§#` rimandano lì.
> **Vincolo**: ZeroErp NON in produzione → breaking change ammessi, ma ogni `ENABLE` deve avere il suo kill-switch pronto. Convenzione: `[VERIFICATO]` su codice attuale; `[DA VERIFICARE SU DB]` = introspezione runtime non disponibile dall'analisi.

---

## 0. Obiettivo in una frase

Portare lo scope "un operatore vede solo gli emittenti fiscali a cui è abilitato" dal livello applicativo (oggi a macchia di leopardo + trigger in scrittura) a **Row Level Security nativa**, così l'enforcement in lettura è uniforme e a prova di endpoint dimenticato. Si attiva **prima del portale**: il consumatore (backend interno come OPERATORE) e i GUC esistono già.

---

## 1. Cuore logico: UNA regola di scope EF, canonica

Oggi la stessa regola vive in tre implementazioni che divergono (C7/R3): write-guard, RLS-read (senza bypass SUPER_ADMIN), wrapper Python. **Serve una sola sede della regola.** La logica canonica, dati un *attore* (utente) e un *emittente target*, risponde "visibile? sì/no":

1. **Attore nullo (job batch/sistema)** → visibile (nessun filtro).
2. **SUPER_ADMIN** → visibile (bypass totale). *(Oggi MANCA nella RLS-read: è il bug C7 da chiudere.)*
3. **Nessuna identità OPERATORE attiva** per l'attore (revocata / fuori finestra `valido_dal..valido_al` / disabilitata) → **non visibile** (fail-closed).
4. **Whitelist EF vuota** (`config.user_emittenti_fiscali` senza righe per l'utente) → visibile (accesso globale).
5. **Whitelist popolata** → visibile **solo se** l'emittente target è in lista.

Requisiti su questa canonica:
- **Chiave attore = `auth_user_id`** (decisione §5.4.3): è la chiave della whitelist, del write-guard e del Python. Le policy passeranno il GUC `app.current_user_id`. *(Niente `identita_id` nella regola.)*
- Deve poter essere **valutata efficientemente per riga** dalle policy (la performance conta: è un predicato `USING`). Preferibile una forma **inlineable** dal planner; oggi la RLS-read lo è (sql STABLE), il write-guard no (plpgsql). Scelta del linguaggio/forma: team DB, con l'obiettivo di non degradare le list-view operatore oltre soglia (§/benchmark).
- Riusa gli helper già esistenti e verificati: `script.fn_is_super_admin`, `script.fn_has_identita_attiva(auth_user_id, 'OPERATORE')`.

> **Da verificare**: `script.fn_is_super_admin` accetta `auth_user_id` (integer) come input? È l'unico identificativo disponibile nelle policy via GUC (`app.current_user_id`). `[DA VERIFICARE SU DB]`

## 2. Due convenzioni di colonna emittente → adattatori sottili

Le tabelle target portano l'emittente in due modi (asimmetria di modello esistente):
- **SR** = `emittente_soggetto_ruolo_id` (es. `vendite.fatture`, `fatturazione_lotti`).
- **PK** = `emittente_fiscale_id` (es. `preventivi`, `contratti`, `offerte_commerciali`, `documenti_generati`, `pratiche`).

Serve che la **stessa regola canonica** sia raggiungibile da entrambe, più due casi derivati:
- **adattatore SR** (risolve il `soggetto_ruolo` emittente → emittente, poi applica la regola);
- **adattatore PK** (applica la regola direttamente);
- **via fattura** (per `vendite.fatture_scadenze`, che non ha colonna emittente propria: risolve l'emittente attraverso la fattura collegata — speculare all'esistente `fn_scope_ba_ownership_via_fattura`);
- **via efba** (per `anagrafiche.billing_account`: vedi §4).

Importante: che siano funzioni-adapter separate o un'unica funzione con normalizzazione, **la regola deve essere scritta una volta sola** (gli adapter sono sottili). Creare la variante PK **adesso**, non rinviarla (simmetria piena).

## 3. Bug da chiudere e duplicati da rimuovere

- **C7 — bypass SUPER_ADMIN nella RLS-read**: una volta che le policy delegano alla canonica, il bypass entra ovunque per costruzione. Verificare che nessuna policy EF resti senza.
- **Duplicati legacy** (fonte di divergenza): esistono copie `config.fn_check_user_emittente_scope` (modello `ruolo_sistema=ADMIN` vecchio) e `config.fn_get_emittenti_scope*`. Da **dismettere** previa verifica zero-caller `[DA VERIFICARE SU DB]`.
- **B5 — funzione legacy senza guard**: `script.fn_get_emittenti_scope` (legacy, senza guard OPERATORE/super_admin) è ancora usata da alcuni path. Va dismessa; i lettori vanno portati sulla famiglia guarded. *(Il ricablaggio dei chiamanti Python è nel brief BE/FE.)*

## 4. Scope per famiglia di tabelle (cosa filtra cosa)

| Tabella | Come si ricava l'emittente | Note |
|---|---|---|
| `vendite.fatture` | colonna SR | policy EF già esistente (dry-run) da far delegare alla canonica |
| `vendite.fatture_scadenze` | via fattura collegata | nuova logica "via_fattura" speculare a quella BA |
| `vendite.fatturazione_lotti` | colonna SR | stessa famiglia di join delle fatture |
| `vendite.preventivi` / `contratti` / `offerte_commerciali` | colonna PK | adapter PK |
| `documenti.documenti_generati` | colonna PK | adapter PK |
| `pratiche.pratiche` | colonna PK | adapter PK + indice (manca, §6) |
| `vendite.ordini` | **colonna PK da AGGIUNGERE** | vedi §5 |
| `anagrafiche.billing_account` | **via mappatura efba** | non ha colonna emittente: la visibilità si ricava da `emittenti_fiscali_billing_account` (specifico-o-default). **Esiste già** `fn_check_ba_visible_for_emittenti(ba, emittenti_sr[])` (3 livelli: mapping specifico → fallback `is_default` → non visibile). La policy OPERATORE va costruita su quella, intersecata con la whitelist dell'operatore. Allinea la RLS al filtro già attivo lato ricerca (`fn_search_soggetti_universale`). |

**Fuori dal primo lotto**: `acquisti.*` (rientrerà a sviluppo del dominio); config (`listini`, `template_documenti`, arrotondamenti) → lotto config dedicato (pricing/config sono cross-EF per design).

**Semantica NULL — non-problema** (§11.5, `[VERIFICATO]`): sui documenti l'emittente è **materializzato NOT NULL** (default incluso, via `trgfn_emittenti_fiscali_default_bootstrap`). Non esistono righe con emittente NULL → niente special-casing NULL nelle policy. Residuo: **confermare NOT NULL** su ogni tabella prima dell'`ENABLE` (in particolare `vendite.fatture` `[DA VERIFICARE SU DB]`).

## 5. `vendite.ordini`: aggiunta colonna emittente (decisione §11.4)

`vendite.ordini` oggi non ha emittente → va denormalizzato uno **snapshot** `emittente_fiscale_id` (convenzione PK, coerente con preventivi/contratti/offerte). Serve:
- nuova colonna `emittente_fiscale_id` (FK a `anagrafiche.emittenti_fiscali`);
- **backfill** con la stessa risoluzione usata altrove (**specifico-o-default** via efba / catena user-derived) — `[DA VERIFICARE SU DB]` la sorgente più corretta del valore per ordini (testata documento / contratto / cliente);
- `SET NOT NULL` a regime (post-backfill, fase end);
- indice sulla colonna (per i filtri/perf);
- trigger guard di scrittura (vedi §7).

## 6. Indici (perf, §7 analisi)

Lo scope-predicate è opaco al planner: l'indice serve ai **filtri applicativi** e alle list-view, con la RLS come Filter residuo. Inventario e gap:
- **Gap certo**: `pratiche.pratiche.emittente_fiscale_id` non ha indice e `pratiche` non è in `dbops.automation_scope` (no auto-gen). Da creare esplicitamente prima di includerla.
- **Da non dare per scontati** (colonne emittente recenti): `contratti`, `offerte_commerciali`, `documenti_generati` — verificare l'esistenza dell'indice EF, crearlo esplicito se assente. `[DA VERIFICARE SU DB]`
- `fatturazione_lotti`: verificare FK+indice prima di includerla in Ondata 1.
- Presenti e OK: `fatture`, `fatture_scadenze` (via fattura_id), `preventivi`.

## 7. Lettura vs scrittura: RLS `FOR SELECT` + trigger in scrittura (decisione §5.1)

**Decisione presa**: la RLS copre la **lettura** (`FOR SELECT`); la **scrittura** resta governata dai trigger guard esistenti, da **estendere** alle nuove tabelle. NON usare `FOR ALL`/`WITH CHECK`. Motivi: i batch scrivono senza GUC d'identità (una WITH CHECK li bloccherebbe), errore strutturato parlante vs errore RLS opaco, niente logica WITH CHECK duplicata per le due convenzioni.

Conseguenza per il team DB:
- estendere il trigger guard di scrittura per gestire **anche la convenzione PK** (oggi gestisce SR via fattura/soggetto_ruolo) e attaccarlo a: `contratti`, `offerte_commerciali`, `preventivi`, `documenti_generati`, `pratiche`, `ordini`; per `fatture_scadenze` riusare la via-fattura.
- **Senza questo, quelle tabelle restano scrivibili cross-EF dall'operatore anche dopo l'attivazione RLS in lettura** — l'asimmetria lettura/scrittura è prioritaria.

## 8. Viste: `security_invoker` (BLOCKER, R1/C2)

**Bloccante.** Le viste di dominio (`vw_*`) sono in larga parte *definer*: eseguono col contesto dell'owner (superuser BYPASSRLS) → **la RLS della tabella base verrebbe bypassata** (RLS cosmetica). Prima di qualsiasi `ENABLE`:
- introspezione `reloptions`/owner/`pg_depend` di tutte le viste/matview che insistono sulle tabelle del lotto `[DA VERIFICARE SU DB]`;
- portare a `security_invoker=on` le viste lette dagli operatori coinvolte;
- le **matview** non supportano `security_invoker` → decisione esplicita (smaterializzare o filtrare a monte).

## 9. `ENABLE` (no `FORCE`), per ondate, con kill-switch

- **`ENABLE ROW LEVEL SECURITY`** è sufficiente (owner e ruoli BYPASSRLS restano esenti → migrazioni/job owner non bloccati). **NON** usare `FORCE` in questa fase.
- Attivare **per famiglia di join atomica**, non per tabella isolata (R9: fatture sì + scadenze no = join incoerente).
- Per ogni tabella attivata, consegnare il **changeset kill-switch gemello** (`DISABLE ROW LEVEL SECURITY`): rollback immediato senza distruggere le policy. NON usare `DROP POLICY` come rollback.
- **Ondate**:
  - **Ondata 1** (convenzione SR): `vendite.fatture` + `fatture_scadenze` (via fattura) + `fatturazione_lotti`.
  - **Ondata 2** (convenzione PK): `preventivi`, `contratti`, `offerte_commerciali`, `documenti_generati`, `pratiche`, `ordini` (dopo aggiunta colonna), `billing_account` (via efba).

## 10. Ruoli (verifiche, §11.8 / C4 / C6)

- **Runtime app = `zeroerp_app`** (NOBYPASSRLS atteso, evidenza committata favorevole). `[DA VERIFICARE SU DB]` l'attributo runtime effettivo: se per qualunque motivo fosse BYPASSRLS, ogni `ENABLE` è inerte → `ALTER ROLE ... NOBYPASSRLS`.
- **Migrazioni = `titodb`** (via `liquibase5.sh`), non `postgres`. `[DA VERIFICARE SU DB]` che sia superuser/BYPASSRLS (atteso) → migrazioni esenti dalla RLS. *(`db/liquibase-mirror.properties` con `postgres` è un env di test obsoleto: valutarne la rimozione.)*
- **Job batch (pgAgent)**: girano **senza GUC** → sotto RLS vedrebbero 0 righe (R4). Le funzioni batch che scrivono/leggono tabelle del lotto (es. chiusura scadenze) vanno rese `SECURITY DEFINER` owner-bypass, oppure il job gira come ruolo BYPASSRLS. `[DA VERIFICARE SU DB]` quali job toccano le tabelle del lotto.
- **Ruoli di test pgTAP**: serve un ruolo NOBYPASSRLS e uno BYPASSRLS dedicati ai test funzionali (§11).

## 11. Test pgTAP (cosa verificare, non come)

I test strutturali esistenti non esercitano il runtime (serve ruolo non-BYPASSRLS). Servono test **funzionali** che, dentro transazione con `ENABLE` locale + ruolo non-BYPASSRLS + GUC simulati, verifichino almeno:
- operatore con whitelist → vede solo i propri EF; zero righe degli altri;
- operatore con whitelist vuota → vede tutto (globale);
- **connessione senza GUC → 0 righe** (fail-closed, comportamento voluto §11.6);
- identità presente ma non attiva / fuori finestra → 0 righe;
- ruolo BYPASSRLS → vede tutto (asserzione di consapevolezza);
- SUPER_ADMIN → vede tutto (verifica del fix C7);
- **anti-regressione viste**: una vista `vw_*` su tabella RLS, se *definer*, deve far fallire il test finché non è `security_invoker` (trasforma C2 in cancello CI);
- guard negativo: tabelle senza branch OPERATORE attivato → 0 righe per OPERATORE (documenta il danno dell'attivazione big-bang).

## 12. Benchmark (gate pre-`ENABLE`)

`EXPLAIN (ANALYZE, BUFFERS)` prima/dopo `ENABLE`, con ruolo NOBYPASSRLS + GUC operatore+whitelist, su: lista fatture, lista contratti/offerte/preventivi, coda pratiche, write-path con trigger. **Soglia**: regressione latenza ≤ 10% sulle list-view operatore; nessuna transizione index→seq-scan indotta dalla RLS. Oltre soglia → indice EF obbligatorio prima dell'attivazione.

## 13. Prerequisito esterno al DB (da BE)

Le policy assumono i GUC popolati **e isolati per richiesta**. Esiste un rischio di leak cross-request (GUC session-scoped + `CONN_MAX_AGE`) che si manifesta solo a RLS attiva (R-GUC, §11.1). La sua risoluzione è **lato backend** (reset GUC all'inizio di ogni richiesta, fail-closed) ed è descritta nel brief BE/FE. **L'`ENABLE` in produzione-interna non va fatto prima che quel fix sia in piedi e testato sotto pool concorrente.**

## 14. Sequenza consigliata

1. Verifiche `[DA VERIFICARE SU DB]` (ruoli, viste, indici, NOT NULL, firma `fn_is_super_admin`, caller duplicati legacy).
2. Canonica + adapter (SR/PK/via_fattura/via_efba) + fix C7 + dismissione duplicati.
3. Estensione trigger di scrittura (PK) sulle tabelle del lotto.
4. `security_invoker` sulle viste del lotto + decisione matview.
5. `ordini`: colonna + backfill + NOT NULL + indice.
6. Indici mancanti (pratiche, ecc.).
7. Ruoli test pgTAP + test funzionali + anti-regressione viste.
8. **(prerequisito BE: fix R-GUC in piedi)** → `ENABLE` Ondata 1 + kill-switch + benchmark.
9. Ondata 2 (PK + billing_account), una famiglia per volta.

> Tutte le decisioni di dominio sono già chiuse in [analisi-attivazione-rls-operatori.md §11](analisi-attivazione-rls-operatori.md). Questo brief è la loro proiezione operativa lato DB. Per ogni voce `[DA VERIFICARE SU DB]` il team DB ha l'ultima parola sulla strada migliore.
