## 📘 Documentazione Concettuale – Funzione `script.fn_get_ba_emittente_sr_id`

> **Ultimo aggiornamento**: 27 novembre 2026
>
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
[script.fn_get_ba_emittente_sr_id_installazione](/dbzero/script/manual/fn_get_ba_emittente_sr_id_installazione) — la stessa domanda senza il livello 2 («per l'installazione»), per le regole che non devono dipendere da chi agisce
>
[anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk) e [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id) — gli involucri che sollevano (PK e SR)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale

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

Sono **tre livelli**. Ogni billing account ha sempre il suo collegamento, e la
risposta è il primo; il secondo e il terzo riguardano solo l'istante della
nascita, prima che il trigger di nascita scriva il collegamento, e ripetono la
scelta che il trigger sta per fare:

1. **Mapping specifico.** Se quel billing account ha la sua riga in
   `emittenti_fiscali_billing_account`, l'emittente è quello. Al massimo una:
   lo garantisce l'indice univoco `uq_emittenti_fiscali_ba`. **Vince sempre**:
   il `COALESCE` non valuta i livelli dopo.
2. **Riserva in sessione — l'emittente di chi sta agendo.** Se il billing
   account non ha legame e c'è un operatore in sessione (`app.current_user_id`),
   l'emittente è il suo, risolto con
   [`script.fn_resolve_emittente_for_user`](/dbzero/script/manual/fn_resolve_emittente_for_user)
   — **la stessa funzione con cui il trigger
   [`anagrafiche.trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef)
   scrive il legame**. *Un BA appena nato appartiene a chi lo sta creando.*
3. **Riserva senza sessione — il default dell'installazione.** Nessuna GUC
   (batch, manutenzione), oppure un utente che il resolver non sa collocare:
   vale l'emittente marcato `is_default = true`, lo stesso con cui il trigger di
   nascita collega il billing account. Anche quello è al massimo uno:
   `uq_emittenti_fiscali_ba_default`. Senza nessuna azienda il billing account
   non nasce (`E_EMITTENTE_DEFAULT_MISSING`), e il livello non ha un caso.

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

Sull'emittente di default passava; con due emittenti in esercizio, invece, gli
operatori del secondo non avrebbero aperto clienti, perché il backend fa lo
stesso `RETURNING` (`clienti_repository.create_billing_account`).

Con il livello 2 la riserva dice in anticipo ciò che il trigger sta per
scrivere, e il `RETURNING` vede la riga.

Un BA che *resta* senza legame non esiste: il trigger di nascita lo collega
sempre (all'azienda di chi agisce o, senza sessione, alla predefinita), e il
collegamento non si cancella. Per questo, fuori dall'istante della nascita,
questa funzione e la sua gemella «per l'installazione» danno la stessa
risposta.

⚠️ I livelli 2 e 3 rispondono anche a un id che **non è un billing account**:
un id inventato riceve l'azienda di chi agisce o la predefinita. Questa
funzione non lo rifiuta, perché la chiamano le policy del billing account e
una policy non solleva. Lo rifiutano i due involucri per chi scrive,
[`anagrafiche.fn_get_emittente_fiscale_id`](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id)
e [`anagrafiche.fn_get_emittente_fiscale_pk`](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk),
con `E_BILLING_ACCOUNT_NOT_FOUND`: chi ha bisogno di un'azienda per scrivere
passa da loro, non da qui.

---

### ⚠️ Due cose che questa funzione **non** fa

**Non risale l'albero dei billing account.** Un figlio ha il suo collegamento,
come ogni billing account, e la risposta è quello: non eredita quello del
padre. Che padre e figlio siano della stessa azienda lo garantisce un'altra
regola ([anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente)).

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
* `STABLE`, e **non `PARALLEL SAFE`**: legge la GUC di sessione e chiama
  `fn_resolve_emittente_for_user` (plpgsql, senza marcatura, con il log via
  `dblink` sul ramo d'errore), e marcarla `SAFE` sarebbe una dichiarazione
  falsa al planner. Non lo è nemmeno la chiamante
  `fn_check_ba_visible_for_emittenti`; il costo è trascurabile, la ricerca è
  paginata;
* diventa disponibile per chiunque debba **mostrare** l'emittente di un rapporto
  cliente, non solo filtrarci sopra.
