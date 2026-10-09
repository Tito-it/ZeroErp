# Brief DB — Il sesso di una persona fisica non si inventa

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB.
> **Origine:** revisione del codice BE non committato del 2026-10-09; decisione di Tid.
> **Stato:** 📝 **da fare** (il lato BE/FE è già chiuso, §4).

## 1. La regola (decisione di Tid, 2026-10-09)

Il sesso di una persona fisica lo **sceglie qualcuno che lo vede**. Il form a video può
**proporre** «M», ma la proposta deve essere visibile; un sesso che nessuno ha visto non si
scrive. Se il dato manca, la risposta è un **errore**, non un valore di comodo.

## 2. Che cosa dice oggi il DB (contratto, dalla doc auto-generata)

| Oggetto | Oggi | Effetto |
| --- | --- | --- |
| `anagrafiche.fn_crea_soggetto_pf` | `p_sesso DEFAULT NULL`, poi `COALESCE(p_sesso, 'M')` nell'`INSERT` | una chiamata senza sesso crea un uomo, senza errore |
| `anagrafiche.fn_crea_operatore_v2` (flusso A, soggetto nuovo) | passa `p_sesso` a `fn_crea_soggetto_pf` | eredita lo stesso default |
| `anagrafiche.soggetti.sesso` | `character(1)`, nullable, **`DEFAULT 'M'`** | anche un `INSERT` diretto senza sesso crea un uomo |

## 3. Che cosa si chiede

1. `fn_crea_soggetto_pf`: togliere il `COALESCE(p_sesso, 'M')`. Un `p_sesso` nullo (o diverso
   da `M`/`F`) è un rifiuto con un codice di validazione e il campo nel contesto, come gli
   altri obbligatori della funzione (`COLUMN` = `sesso`, perché il form accenda il campo).
2. `anagrafiche.soggetti.sesso`: togliere il `DEFAULT 'M'`. Va valutato se un vincolo deve
   pretendere `sesso IN ('M','F')` per le sole persone fisiche: la colonna è nullable perché i
   soggetti PG non ce l'hanno, e il «PF senza sesso» va escluso dalla struttura, non dal verbo.
   La decisione sulla forma (CHECK legato alla natura, o guard nel trigger della PF) spetta al
   team DB.
3. pgTAP: i test e i builder che chiamano `fn_crea_soggetto_pf` senza `p_sesso` vanno
   allineati (oggi lo nominano, tra gli altri, `test-fn-crea-soggetto-pf.sql`,
   `test-fn-crea-operatore.sql`, `test-fn-guard-soggetto-pf-pura.sql` e i builder `dbops`), e
   va aggiunto un caso che provi il rifiuto.

## 4. Lato BE/FE (fatto il 2026-10-09)

* `SoggettiService._create_pf`: il sesso è obbligatorio (`E_ANAG_VALIDAZIONE`); tolto il
  `"M"` di ripiego. `SoggettiRepository.crea_soggetto_pf` lo vuole senza default.
* `AmmSoftwareService.create_operatore`: col soggetto nuovo (flusso A) il sesso è obbligatorio
  (`M`/`F`, `E_AMM_VALIDAZIONE` col campo); col soggetto esistente (flusso B) passa `NULL`,
  che la funzione DB non legge. Tolta la costante `DEFAULT_SESSO`.
* Eliminato `AnagraficheCoreRepository` (un secondo wrapper di `fn_crea_soggetto_pf`, usato
  solo dai test, con `"IT"`/`"M"` cablati).
* Frontend: `SoggettoForm.vue` propone già «M» nella select, a video; l'etichetta ora porta
  l'asterisco dell'obbligatorio.

⚠️ Finché il §3 non è applicato, il default resta vivo per chi chiama la funzione DB senza
passare dal backend (processi batch, script, builder di test).
