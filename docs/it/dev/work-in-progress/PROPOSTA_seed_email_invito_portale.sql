-- PROPOSTA per branch `dev/db-tid`: seed template email INVITO_PORTALE.
-- Necessario per abilitare lo Sprint C1 Portali MVP (§5.5.3).
--
-- L'admin lancia l'invito portale via endpoint
--   POST /api/v1/anagrafiche/clienti/{id}/invita-portale/
-- il quale chiama EmailDispatchService.send_email(codice_template='INVITO_PORTALE').
-- Senza questo template il send fallisce con template-not-found.
--
-- Variabili disponibili (passate dal service InvitoPortaleService):
--   nome               -> display name destinatario (ragione sociale o cognome+nome)
--   entita             -> label tipo entita ("Cliente BA-000123" o "Fornitore 42")
--   azienda            -> "ZeroErp" (hardcoded service, da parametrizzare in futuro)
--   link               -> URL attivazione /attivazione-portale/<token>
--   scadenza_ore       -> numero di ore validita token ("72")
--   invitato_da        -> display name dell'operatore che ha inviato
--   ruolo_applicativo  -> "CLIENTE_PORTALE" | "FORNITORE_PORTALE"
--
-- Proposta: un unico template INVITO_PORTALE (no duplicazione CLIENTE/FORNITORE)
-- con placeholder {{entita}} che differenzia i casi. Meno manutenzione.
--
-- Da inserire come nuovo changeset Liquibase in
--   db/changelog/migrations_v2/80_data/sql/config/  (CSV) oppure
--   db/changelog/migrations_v2/80_data/config/YYYYMMDD-NN-seed-email-template-invito-portale-mctit.yaml

INSERT INTO config.email_templates (
    codice,
    unita_organizzativa_id,
    tipo_prestazione_id,
    lingua,
    oggetto,
    corpo_html,
    corpo_testo,
    variabili_disponibili,
    attivo,
    meta,
    data_insert,
    user_insert,
    data_update,
    user_update
) VALUES (
    'INVITO_PORTALE',
    NULL,
    NULL,
    'it',
    'Benvenuto in {{azienda}} - Attiva il tuo accesso al portale',
    '<h2>Benvenuto {{nome}}!</h2>' ||
    '<p>Sei stato invitato ad accedere al <strong>portale self-service</strong> di {{azienda}} come <em>{{entita}}</em>.</p>' ||
    '<p>Clicca sul link seguente per impostare la tua password e attivare l''accesso:</p>' ||
    '<p><a href="{{link}}">Attiva il tuo accesso al portale</a></p>' ||
    '<p>Il link scade tra {{scadenza_ore}} ore.</p>' ||
    '<p>Una volta completata l''attivazione potrai consultare le tue fatture, scadenze e ordini direttamente dal portale.</p>' ||
    '<p>Se non hai richiesto questo invito, ignora questa email.</p>' ||
    '<p>Cordiali saluti,<br/>{{invitato_da}}</p>',
    'Benvenuto {{nome}}! Sei stato invitato ad accedere al portale di {{azienda}} come {{entita}}. ' ||
    'Attiva il tuo accesso: {{link}} (scade tra {{scadenza_ore}} ore).',
    '["nome","entita","azienda","link","scadenza_ore","invitato_da","ruolo_applicativo"]'::jsonb,
    true,
    '{}'::jsonb,
    now(),
    'SEED',
    now(),
    'SEED'
)
ON CONFLICT (codice) DO UPDATE SET
    oggetto = EXCLUDED.oggetto,
    corpo_html = EXCLUDED.corpo_html,
    corpo_testo = EXCLUDED.corpo_testo,
    variabili_disponibili = EXCLUDED.variabili_disponibili,
    attivo = EXCLUDED.attivo,
    data_update = now(),
    user_update = 'SEED';

-- Verifica post-insert:
--   SELECT codice, oggetto, attivo FROM config.email_templates WHERE codice = 'INVITO_PORTALE';
