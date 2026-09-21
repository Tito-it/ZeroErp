## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_ubicazioni_guard_parent`

> 👀 **Vedi anche**
>
> • [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — `parent_id` e `magazzino_id`, dove è montato
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — i codici nella frase
> • [magazzino.trgfn_trasferimenti_guard_stesso_emittente](/dbzero/magazzino/funzioni/trgfn_trasferimenti_guard_stesso_emittente) — lo stesso stampo, fail-closed sotto RLS
>
Guide: brief `brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici` (R-1, §4-bis)

---
### 🎯 Scopo Principale

(rev 2026-09-21 — anagrafiche di magazzino fuori dal pannello config)

**Il padre di un'ubicazione sta nello stesso magazzino, e la gerarchia non torna mai su
sé stessa.** La chiave esterna e il *require* generato chiedono solo che il padre esista e
sia attivo; la regola del modello — un'area contiene corsie *dello stesso magazzino* — non
la faceva rispettare nessuno finché le ubicazioni si scrivevano solo dal pannello di
configurazione. Con il drawer la regola ha un chiamante, e il filtro del picker è la
seconda sede: questo guard è la prima.

Due regole, due codici, entrambi `DATO_ERRATO` con `campo = parent_id` (il padre lo
sceglie una persona nel form):

* **padre di un altro magazzino** → `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO`, la frase
  nomina i codici delle ubicazioni e dei magazzini. Un padre di un altro emittente **non si
  vede** (la funzione legge sotto `rls_ubicazioni_ef_whitelist`) e si rifiuta lo stesso, con
  la frase che lo dice: *fail-closed*, come il guard dei trasferimenti;
* **ciclo** — il padre è l'ubicazione stessa, o una sua discendente, a qualsiasi
  profondità → `E_MAG_UBICAZIONE_PADRE_CICLICO`. Codice separato: «appartiene al magazzino
  X, non a X» sarebbe una frase falsa per un ciclo dentro lo stesso magazzino. La risalita
  degli antenati si fa solo in `UPDATE` (in `INSERT` la riga nuova non è ancora in nessuna
  catena) e non si perde in un ciclo preesistente.

Montato `BEFORE INSERT OR UPDATE OF parent_id`. **Il cambio di magazzino non passa di
qui**: `magazzino_id` è una colonna immutabile (lock delle colonne,
`E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`) — un'ubicazione che cambiasse magazzino
lascerebbe i figli nel magazzino vecchio e le righe del registro incoerenti. Per spostarla
si disattiva e se ne crea una nel magazzino giusto. Il lock viene prima del guard
nell'ordine alfabetico dei trigger: prima l'immutabilità, poi la validità del padre nuovo.

Presidio: `db/pgtap/magazzino/test-ubicazioni-guard-parent-v1.sql`.

---

### Storia

* 2026-09-21 — nasce con il brief delle anagrafiche di magazzino (`20260921-14`; lock su
  `magazzino_id` in `automation_lock_columns`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
