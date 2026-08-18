## 📘 Documentazione Concettuale – Funzione `script.fn_get_ba_emittente_sr_id`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[script.fn_check_ba_visible_for_emittenti](/dbzero/script/manual/fn_check_ba_visible_for_emittenti)
>
[script.fn_search_soggetti_universale](/dbzero/script/manual/fn_search_soggetti_universale)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

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

Sono **due livelli**, ed è la regola già in vigore — non è cambiata, si è solo
spostata:

1. **Mapping specifico.** Se quel billing account ha la sua riga in
   `emittenti_fiscali_billing_account`, l'emittente è quello. Al massimo una:
   lo garantisce l'indice univoco `uq_emittenti_fiscali_ba`.
2. **Fallback sul default.** Se il billing account non ha nessun mapping, vale
   l'emittente marcato `is_default = true` — il "gestore globale" copre ciò che
   non è ancora stato assegnato a nessuno. Anche quello è al massimo uno:
   `uq_emittenti_fiscali_ba_default`.

> Sono i **due indici univoci** a rendere questa funzione ben definita. Senza di
> loro «l'emittente del billing account» non sarebbe nemmeno un singolare, e la
> domanda non avrebbe una risposta.

---

### ⚠️ Due cose che questa funzione **non** fa

**Non risale l'albero dei billing account.** Un figlio senza mapping proprio
*non* eredita quello del padre: ricade sul default globale. Non è una svista —
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

Senza quel `CASE`, un `NULL` cadrebbe nel livello 2 e si vedrebbe rispondere
**l'emittente di default**. Cioè: *«questo cliente non ha billing account»*
verrebbe letto come *«questo cliente ha un billing account non ancora
assegnato»*. Sono due cose diverse, e la seconda **apre**: quel cliente
risulterebbe visibile a chiunque abbia il default in whitelist.

I due test `2` e `9` di `db/pgtap/script/test-ba-emittente-risoluzione-v1.sql`
presidiano esattamente questo, dai due lati.

---

### Impatto e Vantaggi

* la regola «quale emittente fattura questo BA» ha **un posto solo**: il filtro
  della ricerca e l'etichetta a video non possono più divergere;
* `STABLE PARALLEL SAFE`, e la seconda metà non è decorativa: la chiamante
  `fn_check_ba_visible_for_emittenti` è `PARALLEL SAFE` e gira dentro la query
  dinamica della ricerca universale. Una delegata `UNSAFE` avrebbe reso la
  marcatura della chiamante una dichiarazione falsa al planner;
* diventa disponibile per chiunque debba **mostrare** l'emittente di un rapporto
  cliente, non solo filtrarci sopra.
