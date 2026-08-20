## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_emittenti_fiscali_guard_attivo` *(RITIRATA)*

> ⛔ **Questa funzione non esiste più dal 2026-08-20** (changeSet `20260820-02`).
> La pagina resta perché la regola che teneva è ancora viva, e chi arriva qui da
> un vecchio link deve trovare **dove è finita**, non un vuoto.
>
> 👀 **Dove vive adesso la regola**
>
> • [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)
> — trigger `trg_emittenti_fiscali_a10_emittenti_fiscali_billing_acco_b98811`
> su [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali),
> generato dall'automazione ATTIVO
> • codice errore: `E_ATTIVO_BLOCK_CHILDREN_EXIST` (125), che **nomina la
> tabella collegata**. Il vecchio `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA` (131) è
> ritirato con `obsoleto_dal = 2026-08-20`

---

### 🎯 Cosa faceva

(latest review 23-01-26 — la funzione è stata ritirata il 2026-08-20)

Impediva la disattivazione (`attivo = false`) di un emittente fiscale quando
esistevano righe di mapping in `emittenti_fiscali_billing_account` collegate al
suo `emittente_soggetto_ruolo_id`. Evento: `BEFORE UPDATE OF attivo`.

### Perché è stata tolta

Era diventata un **doppione esatto**, non un presidio in più.

1. Il `20260819-04` ha dato a `emittenti_fiscali_billing_account` una chiave
   esterna verso `emittenti_fiscali` — prima non ne aveva **nessuna**.
2. L'automazione ATTIVO scopre le figlie dalle chiavi esterne: la notte
   successiva ha generato il trigger generico sulla stessa identica coppia.
3. I trigger `BEFORE ... FOR EACH ROW` scattano in **ordine alfabetico**, e
   `…emittenti_fiscali_billing_acco_b98811` viene prima di
   `…guard_attivo_upd`: da quel momento questa funzione non veniva più
   raggiunta.

⚠️ E i due non erano nemmeno *simili*, erano **equivalenti**: il generico
distingue fra «righe collegate» e «righe collegate *attive*» solo quando la
tabella figlia ha una colonna `attivo` — e `emittenti_fiscali_billing_account`
non ce l'ha. Stessa tabella, stessa colonna, stesso predicato, stesso momento.

L'unico vantaggio rimasto era il **messaggio dedicato**, e nemmeno quello: il
`20260820-01` ha insegnato al messaggio generico a nominare la tabella che
blocca, per tutti i trigger della famiglia insieme.

### ⛔ Il costo, dichiarato

Da allora la regola vive in un trigger **generato**: se la chiave esterna
sparisse o cambiasse bersaglio, l'automazione toglierebbe il trigger e il
divieto se ne andrebbe **in silenzio**. È lo stesso costo che il progetto paga
già per gli altri quindici figli di `emittenti_fiscali`, e il presidio è il
test 7 di `db/pgtap/vendite/test-registri-per-emittente-v1.sql`, che verifica
che quel trigger ci sia.

---

{% include-markdown "signature-core.md" %}
