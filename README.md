# AR - Demande de Recrutement

Module Odoo couvrant le cycle complet de recrutement: expression du besoin, validations, suivi RH, candidats, annonces, dossiers, offre, periode essai, integration, rapports et archivage.

## Objectif

Cette documentation explique le perimetre fonctionnel du module, les roles utilisateurs, le workflow, la configuration et les principaux objets techniques.

## Utilisateurs concernes

- Demandeur ou manager
- RH
- MD ou direction generale
- Responsables entretien
- Administrateur Odoo

## Workflow metier

1. Expression du besoin
2. Soumission
3. Validation N+1
4. Validation RH
5. Validation MD
6. Direction generale si necessaire
7. Suivi candidats
8. Offre acceptee ou refusee
9. Integration ou periode essai
10. Archivage

## Fonctionnement operationnel

- Creer la demande de recrutement.
- Soumettre au manager.
- Renseigner les candidats et documents.
- Generer les fiches et rapports.
- Valider les etapes RH, MD ou direction.
- Suivre integration puis archiver.

## Configuration recommandee

- Verifier utilisateurs RH et managers.
- Configurer groupes et record rules.
- Verifier templates mail.
- Verifier rapports candidat et rapport general.
- Verifier les sequences.

## Dependances Odoo

- `base`
- `mail`
- `hr`
- `web`
- `website`

## Modeles principaux

- `ar.demande.de.recrutement`
- `ar.demande.recrutement.candidate`
- `ar.demande.recrutement.stagiaire.line`
- `ar.demande.recrutement.annonce`
- `ar.demande.recrutement.dossier.candidat.line`
- `ar.demande.recrutement.integration`
- `ar.recrutement.documentation`

## Structure importante du module

- `security/ir.model.access.csv`
- `security/record_rules.xml`
- `security/security.xml`
- `data/ar_demande_recrutement_general_report.xml`
- `data/mail_templates.xml`
- `data/report_araymond_layout.xml`
- `data/report_candidate_fa.xml`
- `data/sequence.xml`
- `views/ar_demande_recrutement_menu.xml`
- `views/ar_demande_recrutement_views.xml`
- `views/recrutement_documentation_views.xml`
- `wizard/__init__.py`
- `wizard/recrutement_action_wizard.py`
- `models/__init__.py`
- `models/ar_demande_recrutement.py`
- `models/recrutement_documentation.py`

## Securite

Les droits sont geres par les fichiers du dossier `security`. Il faut verifier les groupes, les regles enregistrement et les acces CSV apres installation ou modification du module.

## Notifications et suivi

Les modules qui dependent de `mail` utilisent le chatter Odoo pour tracer les changements. Les templates mail presents dans le dossier `data` servent a notifier les acteurs concernes par les transitions.

## Installation

1. Copier le module dans le dossier addons Odoo.
2. Redemarrer le serveur Odoo si necessaire.
3. Mettre a jour la liste des applications.
4. Installer ou mettre a jour le module.
5. Verifier les droits utilisateurs et tester un dossier de bout en bout.

## Maintenance

- Ajouter toute nouvelle etape a la fois dans le modele Python, les vues XML, les droits et les notifications.
- Tester les workflows avec plusieurs roles utilisateurs.
- Mettre a jour les rapports et templates mail quand la procedure interne change.
- Eviter de modifier les donnees de production sans sauvegarde.
- Documenter toute evolution fonctionnelle dans ce README.
