## 📘 Documentazione Concettuale – Funzione `script.fn_get_ba_emittente_sr_id`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_check_ba_visible_for_emittenti](/dbzero/script/manual/fn_check_ba_visible_for_emittenti)
>
[script.fn_search_soggetti_universale](/dbzero/script/manual/fn_search_soggetti_universale)
>
[script.fn_resolve_emittente_for_user](/dbzero/script/manual/fn_resolve_emittente_for_user) — la delegata del livello 2, la stessa del trigger z90
>
[anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk) e [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id) — gli involucri che sollevano (PK e SR)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 13-09-26)

Risponde a una domanda sola, e la mette per la prima volta in forma di **nome**
invece che di sì/no:

> **Quale emittente fattura questo billing account?**

Restituisce il `soggetto_ruolo_id` dell'emittente, oppure `NULL` se non è
risolvibile.

---

### Il problema che risolve

Fino al 18-08-2026 quella domanda esisteva nel database **solo in forma
booleana**, dentro `fn_check_ba_visible_for_emittenti`: *«questo billing account
è visibile per questi emittenti?»*. Perfetta per filtrare, inutile per
mostrare.

Quando è arrivata la richiesta di **far vedere il nome dell'emittente** nella
riga della ricerca universale, c'erano due strade:

1. riscrivere la regola una seconda volta, nel punto che deve mostrarla;
2. estrarla, e far chiedere a entrambi.

La prima è la strada che sembra più corta. Ma due copie della stessa regola non
restano uguali: la prima modifica ne tocca una sola, e da quel momento **il
filtro e l'etichetta a video raccontano cose diverse sullo stesso billing
account** — senza nessun errore, perché nessuna delle due è sbagliata da sola.
Per una regola di perimetro è il difetto peggiore possibile, perché è
silenzioso.

Quindi: estratta qui, e il check delega.

---

### Logica Operativa

Sono **tre livelli** dal 2026-09-13 (changeSet `20260913-01`, D13 — decisione
di Tid del 2026-09-12); fino a quel giorno erano due, e la differenza è tutta
nel secondo:

1. **Mapping specifico.** Se quel billing account ha la sua riga in
   `emittenti_fiscali_billing_account`, l'emittente è quello. Al massimo una:
   lo garantisce l'indice univoco `uq_emittenti_fiscali_ba`. **Vince sempre**:
   il `COALESCE` non valuta i livelli dopo.
2. **Riserva in sessione — l'emittente di chi sta agendo.** Se il billing
   account non ha legame e c'è un operatore in sessione (`app.current_user_id`),
   l'emittente è il suo, risolto con
   [`script.fn_resolve_emittente_for_user`](/dbzero/script/manual/fn_resolve_emittente_for_user)
   — **la stessa funzione con cui il trigger
   [`trgfn_billing_account_link_ef`](/dbzero/anagrafiche/manual/trgfn_billing_account_link_ef)
   scrive il legame**. *Un BA non ancora collegato appartiene a chi lo sta
   creando.*
3. **Riserva senza sessione — il default dell'installazione.** Nessuna GUC
   (batch, manutenzione), oppure un utente che il resolver non sa collocare
   (admin globale senza emittente attivo, istanza «0 emittenti»): vale
   l'emittente marcato `is_default = true`. Anche quello è al massimo uno:
   `uq_emittenti_fiscali_ba_default`.

> Sono i **due indici univoci** a rendere i livelli 1 e 3 ben definiti, e il
> modello «un operatore, un emittente» a rendere tale il livello 2. Senza di
> loro «l'emittente del billing account» non sarebbe nemmeno un singolare, e la
> domanda non avrebbe una risposta.

#### Perché il livello 2 esiste — il difetto D13

Il legame BA → emittente lo scrive un trigger **AFTER** (`z90_link_ef`), cioè
*dopo* che un `INSERT … RETURNING id` ha già chiesto di vedere la riga. In
quell'istante il BA non ha legame, e la policy di lettura
(`rls_billing_account_ef_whitelist` → `fn_scope_ef_whitelist_via_efba` →
`fn_check_ba_visible_for_emittenti` → questa funzione) chiedeva chi lo fattura:
con due soli livelli la risposta era **il default**, cioè un'altra azienda, e
la rilettura negava — *«la nuova riga viola la regola di sicurezza per riga»*
(42501). L'`INSERT` in sé passava; era il `RETURNING` a morire.

Sull'emittente di default passava, ed è il motivo per cui nessuno l'ha visto
fino al 2026-09-12: riprodotto su dbdev con un operatore dell'emittente 44
(`EMITEST`). Il backend fa lo stesso `RETURNING`
(`clienti_repository.create_billing_account`) ⇒ **con due emittenti in
esercizio, gli operatori del secondo non aprivano clienti.**

Con il livello 2 la riserva dice in anticipo ciò che il trigger sta per
scrivere, e il `RETURNING` vede la riga. Le tre risposte possibili alla domanda
*«un BA appena scritto, ancora senza legame, di chi è?»* — e perché è stata
scelta questa — sono nel brief
[brief-db-ba-riserva-emittente-operatore-d13](/dev/work-done/brief-db-ba-riserva-emittente-operatore-d13).

⚠️ **Il prezzo, dichiarato.** Un BA che *resta* senza legame — creato senza
sessione: un seed, una migrazione, un'installazione «0 emittenti» — era «del
default» e ora è, in sessione, di chiunque lo guardi, ciascuno sotto il proprio
emittente. È un dato anomalo che il modello ammette (il trigger lega sempre
quando c'è una sessione), non un caso d'uso. La forma che lo chiuderebbe del
tutto — l'emittente come **colonna** del BA — resta una decisione di modello in
coda, non un lavoro.

---

### ⚠️ Due cose che questa funzione **non** fa

**Non risale l'albero dei billing account.** Un figlio senza mapping proprio
*non* eredita quello del padre: ricade sulla riserva (chi agisce, o il default). Non è una svista —
è esattamente il comportamento che c'era prima, e cambiarlo qui sarebbe stato un
cambio di semantica travestito da riordino. Se un giorno si deciderà che
l'albero eredita, si deciderà una volta e si cambierà **questa** funzione: da
oggi c'è un posto solo dove farlo. L'omogeneità dell'albero è un'altra cosa e
vive altrove ([anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente)).

**Non applica lo scope di chi legge.** Dice *chi fattura*, non *chi può vedere*.
Il filtro di perimetro è responsabilità del chiamante — ed è una separazione
voluta: la stessa risposta serve sia a filtrare sia a mostrare, e mescolarci
dentro il permesso la renderebbe inutilizzabile per il secondo uso.

---

### ⚠️ Il billing account nullo non è un billing account non mappato

È la trappola per cui la funzione ha un `CASE` in testa che a prima vista sembra
ridondante.

Senza quel `CASE`, un `NULL` cadrebbe nei livelli 2 e 3 e si vedrebbe rispondere
**un emittente** — quello di chi agisce, o il default. Cioè: *«questo cliente
non ha billing account»* verrebbe letto come *«questo cliente ha un billing
account non ancora assegnato»*. Sono due cose diverse, e la seconda **apre**:
quel cliente risulterebbe visibile a chiunque abbia in whitelist quell'emittente.

I due test `2` e `10` di `db/pgtap/script/test-ba-emittente-risoluzione-v1.sql`
presidiano esattamente questo, dai due lati; i test `4` e `5` sono la coppia
del livello 2 (in sessione → l'operatore) e del livello 3 (senza sessione → il
default), che si distinguono solo se l'operatore di contesto **non** è quello
del default — per questo la fixture costruisce **due** aziende e apre il
contesto sulla seconda.

---

### Impatto e Vantaggi

* la regola «quale emittente fattura questo BA» ha **un posto solo**: il filtro
  della ricerca e l'etichetta a video non possono più divergere;
* `STABLE`, e **non più `PARALLEL SAFE`** dal `20260913-01`. Fino a quel giorno
  la seconda metà «non era decorativa»: la chiamante
  `fn_check_ba_visible_for_emittenti` era `PARALLEL SAFE` e girava dentro la
  query dinamica della ricerca universale. Ora questa funzione legge la GUC di
  sessione e chiama `fn_resolve_emittente_for_user` (plpgsql, senza marcatura,
  con il log via `dblink` sul ramo d'errore): tenere il `SAFE` sarebbe stata la
  stessa *dichiarazione falsa al planner* che il progetto ha già rifiutato il
  18-08 su `fn_search_soggetti_universale`. Il `SAFE` è caduto anche sulla
  chiamante (`20260913-02`); costo reale ~zero, la ricerca è paginata;
* diventa disponibile per chiunque debba **mostrare** l'emittente di un rapporto
  cliente, non solo filtrarci sopra.
