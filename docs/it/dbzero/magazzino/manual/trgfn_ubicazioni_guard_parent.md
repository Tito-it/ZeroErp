## 📘 Documentazione Concettuale – Trigger function `magazzino.trgfn_ubicazioni_guard_parent`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — `parent_id` e `magazzino_id`, dove è montato
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — i codici nella frase
>
> Approfondimento funzioni:
>
> * [magazzino.trgfn_trasferimenti_guard_stesso_emittente](/dbzero/magazzino/funzioni/trgfn_trasferimenti_guard_stesso_emittente) — lo stesso stampo, fail-closed sotto la sicurezza di riga

---

### 🎯 Scopo Principale

**Il padre di un'ubicazione sta nello stesso magazzino, e la gerarchia non torna mai su
sé stessa.** È montato prima dell'inserimento e dell'aggiornamento delle ubicazioni.

La chiave esterna e il controllo generato chiedono solo che il padre esista e sia attivo; la
regola del modello — un'area contiene corsie *dello stesso magazzino* — la fa rispettare questo
guard. Con il drawer la regola ha un chiamante, e il filtro del selettore è la seconda sede:
questo guard è la prima.

---

### Due regole, due codici

Entrambi `DATO_ERRATO` con campo `parent_id` (il padre lo sceglie una persona nel form):

* **padre di un altro magazzino** → `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO`, la frase
  nomina i codici delle ubicazioni e dei magazzini. Un padre di un altro emittente **non si
  vede** (la funzione legge con i permessi di chi scrive, sotto la sicurezza di riga) e si
  rifiuta lo stesso, con la frase che lo dice: *fail-closed*, come il guard dei trasferimenti;
* **ciclo** — il padre è l'ubicazione stessa, o una sua discendente, a qualsiasi
  profondità → `E_MAG_UBICAZIONE_PADRE_CICLICO`. Codice separato: «appartiene al magazzino
  X, non a X» sarebbe una frase falsa per un ciclo dentro lo stesso magazzino. La risalita
  degli antenati si fa solo in aggiornamento (in inserimento la riga nuova non è ancora in
  nessuna catena) e non si perde in un ciclo preesistente.

---

### Il cambio di magazzino non passa di qui

`magazzino_id` è una colonna immutabile (lock delle colonne,
`E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`): un'ubicazione che cambiasse magazzino lascerebbe i
figli nel magazzino vecchio e le righe del registro incoerenti. Per spostarla si disattiva e
se ne crea una nel magazzino giusto.

Il lock viene prima del guard nell'ordine alfabetico dei trigger: prima l'immutabilità, poi la
validità del padre nuovo.

---

### Codici errore

* `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO` — il padre è di un altro magazzino, o non è
  visibile a chi scrive.
* `E_MAG_UBICAZIONE_PADRE_CICLICO` — il padre è l'ubicazione stessa o una sua discendente.

---

### Test

`db/pgtap/magazzino/test-ubicazioni-guard-parent-v1.sql`.

---

### Note di migrazione

* 2026-09-21 — nasce con `brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici` (R-1,
  §4-bis), quando le ubicazioni escono dal pannello di configurazione e arrivano nel drawer.
  Nello stesso cantiere `magazzino_id` entra fra le colonne immutabili, al posto di un ramo del
  guard dedicato al cambio di magazzino.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
