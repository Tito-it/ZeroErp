# Brief DB — La riga di listino che ha dato il prezzo a una commessa non si tocca più

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-08. **A chi:** team DB
> (`dev/db-tid`); poi BE (§5), che **attende** la consegna DB.
> **Origine:** L0 di [piano-be-type-checker.md](piano-be-type-checker.md) §4.4.
> Riscrivendo riallinea e sblocca del prezzo di una riga di commessa, la
> provenienza del prezzo è diventata un insieme unico (building block
> `apps/vendite/services/prezzo_riga_commessa.py`). `listino_riga_id` ne è rimasta
> **fuori**, perché scriverla cambia il comportamento dei listini e il push non
> la può passare.
> **Decisione:** di Tid, 2026-10-08 — una riga di listino che ha dato il prezzo
> a una riga di commessa **diventa immutabile** (è «propagata»).
> **Stato:** 🟡 aperto, in attesa del team DB.

## 1. La regola

Il prezzo di una riga di commessa deve restare **riproducibile**: la riga di
listino da cui viene non si modifica né si cancella finché una riga a valle la
cita. È la regola che `vendite.trgfn_listini_righe_guard_stato` scrive già per le
versioni `ATTIVA` («ammessa solo se la riga non è propagata a valle»), ed è la
ragione dell'eccezione N6 (rettifica controllata solo su righe non propagate).

Il guard c'è. Manca chi **scrive** il legame.

## 2. Che cosa dice oggi il DB (contratto, letto dalla doc auto-generata)

| Sede | Che cosa fa | Con la regola |
| --- | --- | --- |
| `vendite.trgfn_listini_righe_guard_stato` | su versione `ATTIVA` blocca UPDATE e DELETE di una riga se `EXISTS` una `commesse_attivita` o una `attivita_fatturabili` con `listino_riga_id = OLD.id` (`E_RIGA_LISTINO_PROPAGATA`) | ✅ è la regola |
| `vendite.fn_upsert_commessa_attivita` (madre del push) | ha `p_listino_versione_id`, **non** ha un parametro per `listino_riga_id`: la riga di commessa nasce con la colonna `NULL` | 🔴 nessun push può scrivere il legame |
| `vendite.fn_batch_upsert_commessa_attivita` | legge dal JSON `listino_versione_id` e lo passa alla madre; `listino_riga_id` no | 🔴 idem |
| `vendite.fn_emit_attivita_fatturabili_da_commessa` | copia su `attivita_fatturabili` gli otto campi di audit del prezzo (`prezzo_base_snapshot`, `origine_prezzo`, …), **non** `listino_riga_id` | 🔴 il legame non arriva nemmeno a valle |
| `vendite.fn_resolve_prezzo_listino_v2[_esito]`, stadio BUNDLE | il prezzo viene da `listini_righe_componenti` (`v_bundle_riga_id`), ma l'id di quella riga **non è restituito**; `listino_riga_id` resta `NULL` | 🟡 vedi §3 R-4 |

Risultato: oggi **nessun percorso** scrive `listino_riga_id` su una riga di
commessa o di attività fatturabile. Per il guard dei listini una riga usata da
una commessa non risulta mai «propagata», e la rettifica N6
(`ListiniRepository.check_riga_propagata` lato BE) la lascia modificare.

⚠️ Il backend può già scrivere la colonna con una `UPDATE` dal riallineamento,
ma non lo fa apposta: scriverla da un percorso solo sarebbe un'asimmetria (una
riga di listino «propagata» solo se qualcuno ha premuto «riallinea»).

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **La madre del push riceve la riga di listino.** `fn_upsert_commessa_attivita` acquista `p_listino_riga_id bigint DEFAULT NULL` e la scrive (INSERT e ramo `ON CONFLICT DO UPDATE`, come `listino_versione_id`). ⚠️ La firma si **sostituisce**, non si affianca: un overload con un parametro in più e `DEFAULT` renderebbe ambigue le chiamate esistenti (`fn(T)` + `fn(T, U DEFAULT NULL)`). Allineare `fn_batch_upsert_commessa_attivita` (chiave JSON `listino_riga_id`) e il builder `dbops.fn_pgtap_crea_commessa_attivita`, se il team DB lo ritiene. |
| **R-2** | **Il legame arriva a valle.** `fn_emit_attivita_fatturabili_da_commessa` copia `listino_riga_id` insieme agli otto campi di audit che già copia. |
| **R-3** | **Che cosa vuol dire «propagata» quando il prezzo cambia** — da decidere. Oggi il guard guarda il riferimento **attuale**: se un riallineamento sposta la riga di commessa dalla riga di listino R1 alla R2, R1 torna modificabile (a meno che un'attività fatturabile già in fattura la citi ancora). Il prezzo vecchio resta nel diario della riga (`meta.riallineamenti`), ma senza l'id della riga di listino. Due letture possibili: «propagata = citata **adesso**» (com'è) oppure «propagata = citata **almeno una volta**» (serve un registro, o la storia). Il BE propone la prima, ma è una decisione sul modello. |
| **R-4** | **Il kit (stadio BUNDLE).** Il prezzo di un componente dentro un kit viene da `listini_righe_componenti`, che ha il suo guard (`trgfn_listini_righe_comp_guard_immutabilita_v5`) ma nessun legame con la commessa. La stessa regola vale per quella riga? Se sì, servono l'id della riga bundle in uscita dal resolver, una colonna su `commesse_attivita` (e `attivita_fatturabili`) e il guard che la guarda. Se no, va scritto perché. |
| **R-5** | **pgTAP.** Il caso costruito: una riga di commessa nata dal push con la riga di listino; UPDATE e DELETE della riga di listino su versione `ATTIVA` → `E_RIGA_LISTINO_PROPAGATA`; la stessa riga di listino **non** citata → modificabile. E per R-2: l'attività fatturabile emessa porta la riga di listino. |

## 4. Fuori da questo brief

- **Il recupero delle righe esistenti.** Il progetto non è in produzione: le
  righe di commessa già scritte restano senza riga di listino. Nessuna
  migrazione di dati.
- **Le altre famiglie di riga** (righe di onere, rettifiche da reso): non vengono
  dal listino (`fn_aggiungi_onere_commessa` passa `p_listino_versione_id = NULL`;
  le rettifiche citano la fattura). Restano con la colonna `NULL`.

## 5. Ricaduta BE (dopo la consegna DB)

1. `listino_riga_id` entra nella provenienza: `COLONNE_PROVENIENZA_PREZZO` in
   `apps/vendite/db/commesse_repository.py` (sede unica) e
   `provenienza_da_resolver` nel building block. Da lì lo prendono il push
   (`CommessaAttivitaInput` → `batch_upsert_attivita`) e riallinea/sblocca
   (`update_attivita_prezzo`, su commessa e attività fatturabile).
2. La variazione eccezionale lo azzera con il resto della provenienza da listino:
   un prezzo scritto a mano non viene da una riga di listino.
3. Test sul DB vero: la rettifica N6 di una riga di listino usata da una
   commessa risponde `E_RIGA_LISTINO_PROPAGATA` (oggi passa).
4. Se R-4 è sì: il kit, con la sua colonna, nello stesso giro.
