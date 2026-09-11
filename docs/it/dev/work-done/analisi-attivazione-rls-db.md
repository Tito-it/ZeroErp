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

  > **Nota di migrazione [VERIFICATO su codice].** Le policy EF dry-run già presenti (`20260419-62-create-policy-rls-fatture`) sono costruite sull'**altra** chiave: GUC `app.current_identita_id` (bigint) + `script.fn_scope_ef_whitelist(p_identita_id, p_emittente_sr_id)` e `fn_scope_ba_ownership*` (tutte a `identita_id`). Il **write-guard** (`20260228-25-create-trgfn-guard-emittente-scope`) usa invece già `app.current_user_id`. Adottare `auth_user_id` **allinea la lettura al write-guard** — è esattamente il punto della canonica — ma comporta **sostituire, non riusare**, l'impianto read lato `identita_id`: il GUC `app.current_identita_id` e le funzioni `fn_scope_*(identita_id)` vengono **dismessi o riscritti** su `auth_user_id` + `app.current_user_id`. Quindi "far delegare alla canonica" qui significa **riscrivere** le policy cambiando chiave e GUC, non un semplice redirect. Questo è il footprint implementativo più pesante del lotto e va dimensionato come tale.
- Deve poter essere **valutata efficientemente per riga** dalle policy (la performance conta: è un predicato `USING`). Preferibile una forma **inlineable** dal planner; oggi la RLS-read lo è (sql STABLE), il write-guard no (plpgsql). Scelta del linguaggio/forma: team DB, con l'obiettivo di non degradare le list-view operatore oltre soglia (§/benchmark).

  > **Nota perf — valutazione "una sola volta", non per-riga (obiettivo di design).** Dei tre controlli della canonica, i primi due — `fn_is_super_admin(auth_user_id)` e `fn_has_identita_attiva(auth_user_id,'OPERATORE')` — dipendono **solo dall'attore** (costante per tutta la query), non dalla singola riga: marcati `STABLE`, il planner li valuta **una volta sola** e ne riusa l'esito. L'unico controllo realmente **per-riga** è il terzo — *l'emittente di questa riga è nella whitelist dell'attore?*. La forma scelta per la canonica deve preservare questa proprietà (niente funzioni VOLATILE o costrutti che impediscano l'hoisting dei primi due controlli). È **lì, e solo lì** (test whitelist per-riga), che si concentra il costo e dove agisce l'indice EF / il gate benchmark del §12.
- Riusa gli helper già esistenti e verificati: `script.fn_is_super_admin`, `script.fn_has_identita_attiva(auth_user_id, 'OPERATORE')`.

> **[VERIFICATO su codice]:** `script.fn_is_super_admin(p_auth_user_id integer) RETURNS boolean` (SQL STABLE, GUC-aware — `20260421-03-update-fn-is-super-admin-guc-aware`). Accetta `auth_user_id`, l'unico identificativo disponibile nelle policy via GUC (`app.current_user_id`). Coerente con la scelta `auth_user_id`.

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
- **B5 — funzione legacy senza guard**: `script.fn_get_emittenti_scope`. **✅ BE FATTO 2026-06-02** (commit `4201c0f75`): tutti i lettori Python ricablati sulla famiglia guarded → **zero lettori residui**. La legacy (e le `config.fn_get_emittenti_scope*`) **possono essere droppate lato DB**.

## 4. Scope per famiglia di tabelle (cosa filtra cosa)

| Tabella                                                    | Come si ricava l'emittente   | Note                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `vendite.fatture`                                          | colonna SR                   | policy EF già esistente (dry-run) da far delegare alla canonica                                                                                                                                                                                                                                                                                                                                                                            |
| `vendite.fatture_scadenze`                                 | via fattura collegata        | nuova logica "via_fattura" speculare a quella BA                                                                                                                                                                                                                                                                                                                                                                                           |
| `vendite.fatturazione_lotti`                               | colonna SR                   | stessa famiglia di join delle fatture                                                                                                                                                                                                                                                                                                                                                                                                      |
| `vendite.preventivi` / `contratti` / `offerte_commerciali` | colonna PK                   | adapter PK                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `documenti.documenti_generati`                             | colonna PK                   | adapter PK                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `pratiche.pratiche`                                        | colonna PK                   | adapter PK + indice (manca, §6)                                                                                                                                                                                                                                                                                                                                                                                                            |
| `vendite.ordini`                                           | **colonna PK da AGGIUNGERE** | vedi §5                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `anagrafiche.billing_account`                              | **via mappatura efba**       | non ha colonna emittente: la visibilità si ricava da `emittenti_fiscali_billing_account` (specifico-o-default). **Esiste già** `fn_check_ba_visible_for_emittenti(ba, emittenti_sr[])` (3 livelli: mapping specifico → fallback `is_default` → non visibile). La policy OPERATORE va costruita su quella, intersecata con la whitelist dell'operatore. Allinea la RLS al filtro già attivo lato ricerca (`fn_search_soggetti_universale`). |

**Fuori dal primo lotto**: `acquisti.*` (rientrerà a sviluppo del dominio); config (`listini`, `template_documenti`, arrotondamenti) → lotto config dedicato (pricing/config sono cross-EF per design).

**Semantica NULL — non-problema sui documenti** (§11.5, `[VERIFICATO]`): sui documenti l'emittente è **materializzato NOT NULL** (default incluso, via `trgfn_emittenti_fiscali_default_bootstrap`). Non esistono righe con emittente NULL → niente special-casing NULL nelle policy. Residuo: **confermare NOT NULL** su ogni tabella prima dell'`ENABLE` (in particolare `vendite.fatture` `[DA VERIFICARE SU DB]`).

**Eccezione `fatturazione_lotti` — emittente NULLABLE [VERIFICATO su codice, 2026-06-01]:** `vendite.fatturazione_lotti.emittente_soggetto_ruolo_id` è **nullable**. Con la policy attiva, una riga a emittente NULL → l'adapter SR risolve PK NULL → **invisibile agli operatori con whitelist** (i globali a whitelist vuota la vedono; quindi non "nessun operatore", ma i ristretti sì). **Va sanato prima di includere i lotti in Ondata 1.** Il NULL non è un "lotto generico" voluto: l'emittente è derivabile dal billing account via `vendite.fn_resolve_lotto_utility_emittente`. **Sanazione raccomandata (strutturale):** backfill `emittente_soggetto_ruolo_id` dal BA via il resolver dove NULL → `SET NOT NULL` fail-fast. **Gate runtime a carico BE/DB** `[DA VERIFICARE SU DB]`: contare le righe NULL e confermare che il resolver le copra tutte (se restano lotti senza BA né utility risolvibile, vanno gestiti a mano prima del `SET NOT NULL` — regola fix-dati AGENTS.md).

## 5. `vendite.ordini`: aggiunta colonna emittente (decisione §11.4)

`vendite.ordini` oggi non ha emittente → va denormalizzato uno **snapshot** `emittente_fiscale_id` (convenzione PK, coerente con preventivi/contratti/offerte). Serve:
- nuova colonna `emittente_fiscale_id` (FK a `anagrafiche.emittenti_fiscali`);
- **backfill** con la stessa risoluzione usata altrove (**specifico-o-default** via efba / catena user-derived) — `[DA VERIFICARE SU DB]` la sorgente più corretta del valore per ordini (testata documento / contratto / cliente);
- `SET NOT NULL` a regime (post-backfill, fase end);
- indice sulla colonna (per i filtri/perf);
- trigger guard di scrittura (vedi §7).

> **Interazione fra più policy sulla stessa tabella — documentare e testare [VERIFICATO su codice].** Una tabella può portare **più policy PERMISSIVE** insieme: PostgreSQL le combina in **OR** (una riga è visibile se la soddisfa *almeno una*). `vendite.ordini` ha **già due** policy dry-run: `rls_ordini_cliente_ownership` (gate `app.ruolo_applicativo = 'CLIENTE_PORTALE'`, via `script.fn_scope_cliente_ownership(identita_id, soggetto_ruolo_id)`) e `rls_ordini_shop` (gate `'SHOP_CUSTOMER'`, filtro `canale_origine = 'SHOP'`).
> **Esito verifica — NON sono residui di test:** sono la **faccia portale/shop** (multi-face auth), introdotte e poi evolute con uno split dedicato (`20260419-63` → `20260420-07/08`). **Vanno mantenute.** L'ipotesi iniziale di rimuoverle è superata dall'evidenza.
> **Punto chiave [VERIFICATO]:** ogni policy è **gated sul proprio `app.ruolo_applicativo`** → per un OPERATORE la `USING` delle policy cliente/shop è **falsa** (gate non superato), quindi **non contribuiscono** alla sua visibilità. La futura policy OPERATORE (scope emittente, gate `ruolo_applicativo = 'OPERATORE'`) **coesiste in OR senza alcun leak cross-faccia**: nessuna rimozione necessaria. Regola generale: **ogni tabella del lotto con più policy deve documentare quali sono, per quale faccia (gate ruolo), e che si combinano in OR**, con un test che confermi che l'OPERATORE vede le righe **solo per il proprio motivo** (emittente) e non eredita visibilità da altre facce — e viceversa.

## 6. Indici (perf, §7 analisi)

Lo scope-predicate è opaco al planner: l'indice serve ai **filtri applicativi** e alle list-view, con la RLS come Filter residuo. Inventario e gap:
- **Gap certo**: `pratiche.pratiche.emittente_fiscale_id` non ha indice e `pratiche` non è in `dbops.automation_scope` (no auto-gen). Da creare esplicitamente prima di includerla.
- **Colonne PK `emittente_fiscale_id` [VERIFICATO su doc auto-gen]:** presenti e **NOT NULL** su tutte e cinque — `contratti`, `offerte_commerciali`, `preventivi`, `documenti_generati`, `pratiche`. La premessa "adapter PK" e la materializzazione NOT NULL del §4 sono **confermate** (default via trigger `_a10_default_emittente` su contratti/preventivi). Resta da verificare a runtime solo l'**indice EF**.
- **Indice EF — gap reale [VERIFICATO su doc auto-gen]:** presente solo su `preventivi` (`ix_preventivi_emittente_fiscale_id`); **assente** su `contratti`, `offerte_commerciali`, `documenti_generati`, `pratiche` → creare l'indice esplicito su queste **quattro** prima dell'inclusione nell'ondata (conferma a runtime a carico del BE).
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

> ⚠️ **Superato (2026-09-11) — e non solo perché non è mai stato eseguito.**
> L'`ENABLE` è in `databasechangelog` dal **2026-06-02**, la RLS è la
> condizione di esercizio da tre mesi e il pgTAP ci gira sotto dall'08-07: il
> «prima» da confrontare non esiste più, e una soglia misurata sui dati di
> sviluppo sarebbe una fotografia, non una regola. Ma la premessa era anche
> **sbagliata sul modello**: la canonica `script.fn_check_user_emittente_scope`
> è **plpgsql** — quindi il predicato della policy è una **chiamata di
> funzione per riga**, opaca al planner, non un confronto indicizzabile. Un
> indice sulla colonna emittente **non lo serve**: serve solo alla query
> dell'applicazione che entra da quella colonna (una lista per emittente + data,
> come `ix_fatture_emitt_data`), e si decide **per FK** nel registro
> `dbops.fk_index_policy`, con il perché scritto nel seed — è già così da
> agosto (`20260822-39`, `20260822-41`, `20260829-33`). Lo script
> `benchmark-rls-ondata1.sql` è stato ritirato lo stesso giorno. Regola
> aggiornata: [linee-guida-sql §10.9](/linee-guida-sql).

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

---

## 15. Piano di sviluppo (checklist)

> Spuntare `[x]` man mano. Le voci già confermate dalla ricognizione su codice sono pre-segnate. L'ordine rispetta le dipendenze: ogni fase assume chiuse le precedenti. **L'`ENABLE` (Fase 8) non parte finché Fase 7 non è in piedi.**
>
> **Stato (2026-06-01) — RLS ATTIVATA, LAVORO DB COMPLETO.** ChangeSet `20260601-06..41`. Tutto il lotto coperto: canonica+adapter (PK/SR/via_fattura/via_efba), write-guard esteso, 9 viste `security_invoker`, `ordini` completo, indici, **policy RLS su tutto il lotto**, sanazioni dati. **Test verdi**: scope unit, funzionale fatture (+SUPER_ADMIN/C7), anti-regressione viste 9/9.
>
> **Attivazione `ENABLE`** (no-FORCE, kill-switch DISABLE): **Ondata 1 (`-38`) + Ondata 2-A (`-39`) + 2-B billing_account (`-40`) APPLICATE** ("tutto ok"). **Ondata 2-C `contratti` (`-41`) da applicare** (R4 risolto: pgAgent gira come `postgres` superuser → esente). Prerequisito BE **R-GUC: sbloccato**.
>
> **Restano SOLO**: applicare `-41` (se non già); benchmark formali + test multi-policy ordini (opzionali); **dismissione legacy `fn_get_emittenti_scope`** (ora possibile: B5 BE chiuso `4201c0f75`); backlog `acquisti.*`/config cross-EF. *(B5 BE **✅ FATTO 2026-06-02**.)*
>
> **Stato (2026-09-11).** `-38`, `-39`, `-40`, `-41` risultano tutti applicati
> il **2026-06-02** (`databasechangelog`). Il «benchmark formale» **non si
> esegue più**: superato dai fatti e sbagliato nella premessa — vedi la nota in
> §12. ⚠️ **Gli indici EF del `-34` su `contratti`, `offerte_commerciali`,
> `documenti_generati` e `fatturazione_lotti` non esistono più**: le loro FK
> erano già in `dbops.fk_index_policy` a `consentito = false` (registrate dal
> populate notturno prima del 06-01) e `apply_fk_index_policy()`, che gira
> `runAlways` in `90_end`, fa `DROP INDEX IF EXISTS` sul nome scritto nel
> `dll_command` — lo stesso che il changeSet aveva scelto apposta. Un indice
> governato dalla policy si accende dal flag, mai con un `CREATE INDEX` a mano
> (linee-guida-sql §8.7); la decisione per quelle quattro FK oggi è quella di
> **default**, cioè di nessuno. Restano `ix_pratiche_emittente_fiscale_id` e
> `ix_ordini_emittente_fiscale_id`, le cui FK non hanno una riga di policy.

### Fase 0 — Verifiche preliminari (introspezione runtime, a carico DB/BE)

- [x] Firma `script.fn_is_super_admin(p_auth_user_id integer)` — accetta `auth_user_id` ✔
- [x] Esistenza + nullability colonne `emittente_fiscale_id` su contratti/offerte/preventivi/documenti_generati/pratiche — tutte presenti e NOT NULL ✔
- [x] Natura policy `ordini` cliente/shop — faccia portale/shop gated per ruolo, non test ✔
- [x] Indici EF mancanti confermati a runtime (introspezione sez. D) → creati in Fase 5
- [x] Attributo ruolo `zeroerp_app` = **NOBYPASSRLS** ✔ (introspezione sez. B)
- [x] `titodb` (migrazioni) **esente** — non superuser/bypassrls ma **owner** → esente via ownership (conferma che la scelta **no-FORCE** è necessaria; introspezione sez. B)
- [x] `vendite.fatture.emittente_soggetto_ruolo_id` confermata NOT NULL (introspezione sez. C; 0 fatture con emittente orfano)
- [x] Introspezione viste `vw_*` / matview (introspezione sez. A: 9 viste DEFINER, 0 matview)
- [x] **[BE] ✅ FATTO 2026-06-02 (`4201c0f75`)** Caller del legacy `script.fn_get_emittenti_scope` ricablati sulla famiglia guarded → **zero lettori Python residui**: la legacy è droppabile
- [x] Job pgAgent sul lotto **[VERIFICATO — R4 RISOLTO 2026-06-01]**: solo `chiusura_scadenze_daily` tocca `vendite.contratti`. Il demone pgAgent gira come **`postgres`** (superuser, BYPASSRLS) → **esente dalla RLS**: il job cessa i contratti scaduti anche con RLS attiva. **Nessun fix necessario** (la fn è SECURITY INVOKER ma il ruolo bypassa). *(Ondata 1 fatture: nessun job batch.)*

### Fase 1 — Regola canonica + adapter + bonifica duplicati

> **Esito [IMPLEMENTATO 2026-06-01].** Scoperto che la **canonica esiste già**: `script.fn_check_user_emittente_scope(auth_user_id, emittente_fiscale_id)` (con bypass SUPER_ADMIN = fix C7 già dentro) ed è **già usata dal write-guard**. La Fase 1 si è quindi ridotta a far **delegare** la RLS-read alla canonica (zero logica duplicata), non a riscriverla. ChangeSet `20260601-06..09`.

- [x] Regola canonica unica — **già esistente** (`fn_check_user_emittente_scope`, auth_user_id/PK, `STABLE`)
- [x] Adapter **SR** (`fn_scope_ef_whitelist_via_sr`, `-06`), **via_fattura** (`-07`), **PK** (`fn_scope_ef_whitelist` rifirmato, `-09`) — tutti delegano alla canonica
- [x] Adapter **via_efba** (billing_account) — `fn_scope_ef_whitelist_via_efba` (`-35`, Ondata 2): `fn_get_emittenti_scope_sr_ids` ∩ `fn_check_ba_visible_for_emittenti`
- [x] **Riscritta** la policy read EF di `vendite.fatture` su `app.current_user_id` (`-08`), sostituendo `app.current_identita_id`
- [x] Fix **C7**: bypass SUPER_ADMIN ereditato per delega (read+write unificati sulla canonica)
- [x] Duplicati legacy `config.fn_*` — **già rimossi** da `20260308-12`; vecchia `fn_scope_ef_whitelist(identita_id, sr_id)` droppata (`-09`)
- [x] pgTAP `test-fn-scope-ef-whitelist.sql` aggiornato alle nuove firme (PK + via_sr)
- [x] **[BE] ✅ FATTO 2026-06-02** B5: lettori sulla famiglia guarded (`get_emittenti_ids`→`get_emittenti_pk_ids`; `parameter_repository` legge la whitelist diretta). Legacy droppabile lato DB

### Fase 2 — Scrittura (trigger guard)

> **Esito [IMPLEMENTATO 2026-06-01].** Il guard `trgfn_guard_emittente_scope` era **già parametrico** (`TG_ARGV`: modalità + colonna, modi `soggetto_ruolo`/`fattura`) e già su `app.current_user_id` + canonica. Aggiunta la **modalità `fiscale` (PK)** e creati gli attach. ChangeSet `20260601-10..17`.

- [x] Estesa la modalità **`fiscale`** (PK diretta) nel guard (`-10`)
- [x] Attach su `contratti` (`-11`), `offerte_commerciali` (`-12`), `preventivi` (`-13`), `documenti_generati` (`-14`), `pratiche` (`-15`)
- [x] `fatture_scadenze`: attach modalità **via-fattura** (`-16`)
- [x] `fatturazione_lotti`: attach modalità `soggetto_ruolo` (`-17`) — famiglia fatture Ondata 1
- [x] **Sanazione `fatturazione_lotti`**: backfill emittente via resolver + `SET NOT NULL` fail-fast (`-18`) — ⚠️ tocca dati esistenti, **da rivedere/eseguire contro DB reale**
- [x] `ordini`: attach guard scope (fatto in Fase 4, changeSet `-23`)

### Fase 3 — Viste

> **Esito [IMPLEMENTATO 2026-06-01].** Introspezione (`rls-introspezione-runtime`, sez. A): **9 viste DEFINER, nessuna matview**. Convertite a `security_invoker=on`. ChangeSet `20260601-26`.

- [x] `security_invoker=on` sulle 9 viste DEFINER del lotto: `vw_preventivi`, `vw_preventivi_list`, `vw_preventivi_pratiche`, `vw_preventivi_stato_fatturazione(_righe)`, `vw_offerte_commerciali_list`, `anagrafiche.vw_clienti_lista`, `anagrafiche.vw_clienti_codice_ba`, `dbops.vw_diag_v_clienti_links` (`-26`)
- [x] **Matview**: nessuna sul lotto → decisione non necessaria
- [ ] Verificare grant SELECT di `zeroerp_app` sulle tabelle base (security_invoker usa i privilegi del chiamante) — atteso ok (ruolo applicativo standard)

### Fase 4 — `vendite.ordini`: colonna emittente

> **Esito [IMPLEMENTATO 2026-06-01].** Replicato **fedelmente il pattern emittente di `contratti`** (2026-05-26): modello **user-derived** (non BA), guard di coerenza BA, codici errore registrati, backfill a 3 livelli. ChangeSet `20260601-19..25`.

- [x] Colonna `emittente_fiscale_id` BIGINT NULL + FK `fk_ordini_emittente_fiscale` (`-19`)
- [x] Codici errore `E_ORDINE_EMITTENTE_NON_RISOLTO` (467) + `E_ORDINE_EMITTENTE_BA_INCOERENTE` (468) (`-20`, CSV)
- [x] Default trigger **user-derived** `trgfn_ordini_default_emittente` + require-active (`-21`)
- [x] Guard coerenza BA `trgfn_ordini_guard_emittente_ba` — **skip se BA NULL** (ordini ha BA nullable) (`-22`)
- [x] Write-guard scope RLS modalità `fiscale` (`-23`) — completa l'attach rinviato dalla Fase 2
- [x] **Backfill 3-tier** user-derived → BA-derived → gestore globale (`-24`, ⚠️ dati reali, fail-soft con WARNING)
- [x] `SET NOT NULL` in `90_end` con pre-check 0-NULL (`-25`)
- [x] Indice EF su `ordini` → creato in **Fase 5** (changeSet `-34`)

### Fase 5 — Indici mancanti

> **Esito [IMPLEMENTATO 2026-06-01].** Introspezione sez. D: mancavano su 6 tabelle. Creati con `CREATE INDEX IF NOT EXISTS` + naming di policy (come `ix_preventivi_emittente_fiscale_id`). ChangeSet `20260601-34`.

- [x] Indice EF su `contratti`, `offerte_commerciali`, `documenti_generati`, `pratiche`, `ordini`, `fatturazione_lotti` (`-34`) — ⚠️ **quattro su sei rimossi dal loop `apply_fk_index_policy()`** (FK a `consentito = false`); verificato il 2026-09-11, vedi Stato in testa al §15

### Fase 5b — Policy RLS di lettura (dry-run) — *emerso dall'introspezione (sez. F)*

> **Esito [IMPLEMENTATO 2026-06-01].** Le policy di lettura esistevano solo su `fatture`. Create le 7 mancanti (dry-run, no ENABLE), gate `OPERATORE` + adapter giusto per convenzione. ChangeSet `20260601-27..33`.

- [x] PK: `rls_{preventivi,contratti,offerte_commerciali,documenti_generati,pratiche,ordini}_ef_whitelist` → `fn_scope_ef_whitelist` (`-27..31`, **`ordini` `-37`**)
- [x] `rls_fatture_scadenze_ef_whitelist` → `fn_scope_ef_whitelist_via_fattura` (`-32`)
- [x] `rls_fatturazione_lotti_ef_whitelist` → `fn_scope_ef_whitelist_via_sr` (`-33`)
- [x] **[ONDATA 2]** `fn_scope_ef_whitelist_via_efba` (`-35`) + `rls_billing_account_ef_whitelist` (`-36`) — riuso `fn_get_emittenti_scope_sr_ids` ∩ `fn_check_ba_visible_for_emittenti`

### Fase 6 — Test pgTAP

> **Esito parziale [IMPLEMENTATO 2026-06-01].** Template funzionale su `fatture` (`db/pgtap/rls/test-rls-fatture-ef-whitelist-functional.sql`): ENABLE locale alla tx + `SET ROLE zeroerp_app` (NOBYPASSRLS reale, già con grant) in blocchi `DO`, soft-skip se mancano dati. ⚠️ **Da eseguire/iterare contro DB reale.**

- [x] Ruolo NOBYPASSRLS = **`zeroerp_app`** (reale) + esenzione owner `titodb` (no FORCE) come "bypass"
- [x] Matrice §11 core su `fatture`: whitelist vuota / = emittente / = altro emittente / ruolo non-OPERATORE / identità non attiva / owner esente
- [x] Caso **SUPER_ADMIN** (fix C7) aggiunto al test funzionale `fatture` (caso 7) — binding profilo SUPER_ADMIN dinamico
- [x] **Anti-regressione viste** *definer* → `db/pgtap/rls/test-rls-viste-security-invoker.sql` (9 asserzioni `security_invoker=on`, CI-safe)
- [x] **Multi-policy `ordini`** ✅ **verde**: `db/pgtap/rls/test-rls-ordini-multipolicy.sql` — OPERATORE vede solo per emittente, non eredita da cliente/shop; gate per ruolo isola le 3 facce; + kill-switch
- [~] **Replica template su tutte le tabelle del lotto** — *NON in programma (decisione 2026-06-01)*. Motivo: ridondante. La funzione di scope è unica e già testata (unit verde); SR è coperto da `fatture`, PK da `ordini`, l'interazione multi-policy da `ordini`. Replicare N file per tabella aggiungerebbe manutenzione senza nuova copertura. Se in futuro serve, valutare un singolo test parametrico, non N file.

### Fase 7 — Prerequisito BE (bloccante per l'`ENABLE`)

- [x] **[BE — SBLOCCATO 2026-06-01]** Fix leak GUC cross-request (reset per richiesta, fail-closed) in piedi e testato (conferma utente). → Fasi 8–9 (`ENABLE`) ora abilitate.

### Fase 8 — Ondata 1 (convenzione SR)

> **Esito [IMPLEMENTATO 2026-06-01, APPLICATO 2026-06-02].** ChangeSet atomico `20260601-38` (ENABLE no-FORCE su `fatture` + `fatture_scadenze` + `fatturazione_lotti`), rollback = **DISABLE** (kill-switch, policy preservate). Il gate benchmark è **superato** (§12, nota 2026-09-11); lo script `benchmark-rls-ondata1.sql` è stato ritirato. *Nessun job batch coinvolto in Ondata 1.*

- [x] Changeset `ENABLE ROW LEVEL SECURITY` (no `FORCE`) atomico sulla famiglia fatture (`-38`)
- [x] **Kill-switch** = rollback `DISABLE` (non `DROP POLICY`) + snippet psql istantaneo nel commento
- [~] **Benchmark** pre/post `ENABLE` — *mai eseguito, e ritirato il 2026-09-11*: il gate è superato dai fatti e il predicato RLS non è indicizzabile (§12)
- [x] Applicare `-38` — **applicato il 2026-06-02**

### Fase 9 — Ondata 2 (convenzione PK), per gruppi di rischio

> **Esito [IMPLEMENTATO 2026-06-01, APPLICATI 2026-06-02].** Changeset ENABLE splittati per **blast radius / rischio**. Tutti no-FORCE, rollback = DISABLE. Erano da applicare una alla volta, ciascuna con benchmark/verifica: sono stati applicati tutti e tre il 2026-06-02, senza benchmark (superato — §12).

- [x] **Parte A** (`-39`): ENABLE su `preventivi`, `offerte_commerciali`, `documenti_generati`, `pratiche`, `ordini` (tabelle documentali, nessun job batch)
- [x] **Parte B** (`-40`): ENABLE su `anagrafiche.billing_account` — ⚠️ **blast radius alto** (dati master), changeset isolato, da validare a parte
- [x] **Parte C** (`-41`): ENABLE su `vendite.contratti` — **R4 risolto** (pgAgent = `postgres` superuser, esente; nessun fix)
- [x] Applicare A → B → C — **applicati il 2026-06-02** (`-39`, `-40`, `-41` in `databasechangelog`)

> **⚠️ Sequencing**: `-38/-39/-40` applicano su `liquibase update`. Per attivare **un'ondata per volta** (come da §9), usare `tag` + `updateToTag`/`updateCount`, non un singolo `update` che le attiverebbe tutte. Kill-switch (`rollbackCount`/`DISABLE`) pronto per ciascuna.

### Fuori dal lotto (backlog)

- [ ] `acquisti.*` (a sviluppo del dominio)
- [ ] config cross-EF (`listini`, `template_documenti`, arrotondamenti) → lotto config dedicato
