# Analisi refactor frontend catalogo

## Punti da spostare/rivedere

### ArticoloDrawer

- `frontend/src/catalogo/components/ArticoloDrawer.vue:148`
  Applica `DEFAULT_IVA_ID` lato frontend in creazione articolo.
  Il default deve arrivare da backend/API tramite endpoint di inizializzazione form
  oppure essere applicato direttamente dal service/backend in creazione.

- `frontend/src/catalogo/components/ArticoloDrawer.vue:160`
  Decide lato Vue quali campi sono patchabili e omette `uom_id` perche' immutabile.
  La UI puo' rispettare il blocco, ma il contratto API dovrebbe dichiarare
  esplicitamente campi editabili e campi locked.

### ArticoliSearchTable

- `frontend/src/catalogo/components/ArticoliSearchTable.vue:62`
  Disabilita la gestione BoM se `!data.is_composito`.
  Va bene come vincolo UX, ma la decisione operativa dovrebbe arrivare dalla API
  come capability di riga (`can_manage_bom`, `manage_bom_reason`).

### ArticoloUomDrawer

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:46`
  Hardcoda le opzioni `roundingOptions`.
  I valori di rounding sono enum/regole di dominio e devono arrivare da lookup/API
  o da una configurazione centralizzata condivisa.

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:54`
  Imposta default operativi UoM (`factor_to_base`, `qty_step`, `rounding_mode`,
  `max_decimals`, flags vendita/acquisto/logistica, validita', attivo).
  Questi default devono essere restituiti dal backend/API come default di form.

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:74`
  Sincronizza `is_base` con `factor_to_base === 1`.
  La relazione tra UoM base e fattore e' una regola operativa e deve essere
  applicata lato backend/DB o restituita come policy esplicita.

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:198`
  Nasconde l'azione elimina per le UoM base.
  Il backend dovrebbe restituire per ogni riga `can_delete` e `delete_reason`,
  lasciando al frontend solo il rendering dell'azione.

### ArticoloBomDrawer

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:4`
  Codifica nel componente il pattern operativo BoM immutabile: chiudi riga,
  duplica come nuova versione, niente delete.
  Il backend/API dovrebbe esporre le azioni consentite per riga e le motivazioni.

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:117`
  Imposta default BoM (`coeff_qta`, `partecipa_qta`, `obbligatorio`,
  `determina_qta_padre`, `esposto_in_fattura`, `valido_dal = oggi`).
  Sono default di processo e devono arrivare dal backend/API.

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:198`
  Duplica una riga BoM come nuova versione copiando i campi e impostando
  `valido_dal = oggi`.
  La logica di versionamento dovrebbe essere una action backend dedicata oppure
  guidata da una policy API.

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:279`
  Calcola default e vincoli di chiusura riga (`oggi`, `min-date = valido_dal`).
  La semantica di validita'/chiusura deve essere centralizzata lato backend/DB
  ed esposta al frontend come limiti o azione validata.

### ConversioneUomDrawer

- `frontend/src/catalogo/components/ConversioneUomDrawer.vue:45`
  Imposta `valido_dal = new Date()` in creazione conversione.
  Il default di validita' deve arrivare dal backend/API o essere applicato dal
  service in creazione.

### UomConversioniDrawer

- `frontend/src/catalogo/components/UomConversioniDrawer.vue:82`
  Forza `uom_from_id = props.uomId` e consente edit inline solo del `fattore`.
  La UI puo' guidare il flusso, ma campi editabili e azioni consentite devono
  essere esplicitati dal contratto API.

### Store catalogo

- `frontend/src/catalogo/stores/articoli.js:16`
  Calcola `data_da` default come 1 gennaio dell'anno precedente.
  E' una policy di filtro temporale del catalogo: va spostata a configurazione
  server/API oppure documentata come default route/API centralizzato.
