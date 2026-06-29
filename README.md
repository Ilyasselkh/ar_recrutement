# AR - Demande de Recrutement

Module Odoo de gestion des demandes RH couvrant les demandes de recrutement, remplacement, renouvellement de contrat, changement de type de contrat et demande de stagiaire.

Le module gere le circuit de validation, les candidats, les annonces, les entretiens, les offres, la date d'embauche, les dossiers candidats, le parcours d'integration, la periode d'essai, les refus, les ruptures et l'archivage.

## Objectif fonctionnel

Centraliser les demandes RH et imposer un workflow adapte au type de demande.

Le module permet de :

- creer une demande selon un type precis ;
- controler les champs obligatoires avant soumission ;
- faire valider par le Manager N+1, RH, MD ou Direction generale selon le cas ;
- suivre les candidats jusqu'a l'offre et la date d'embauche ;
- gerer les documents stagiaire, dossiers candidats, visite medicale et announcement ;
- suivre l'integration et la periode d'essai ;
- tracer toutes les transitions dans le chatter ;
- notifier les acteurs par email via les templates Odoo.

## Roles fonctionnels

### Demandeur

Le demandeur initie la demande et renseigne le besoin.

Il peut :

- creer une demande ;
- renseigner les champs fonctionnels en etat `Expression de besoin` ;
- soumettre la demande ;
- choisir les candidats a recevoir en entretien ;
- renseigner la validation finale demandeur ;
- completer la FA lorsque le flux le demande ;
- intervenir sur la periode d'essai N+1 hors cas MOD.

### Manager N+1

Le Manager N+1 valide ou refuse la demande apres soumission.

Condition importante : l'utilisateur doit etre le manager reel du demandeur.

### RH

RH pilote les etapes operationnelles du recrutement.

RH peut :

- valider au niveau RH ;
- saisir les annonces ;
- saisir les candidats et CV ;
- planifier les entretiens ;
- renseigner la validation RH et la FA RH ;
- gerer l'offre, la date d'embauche et les documents ;
- renseigner le matricule, le dossier candidat, la visite medicale et l'announcement ;
- renseigner le feedback RH ;
- valider la periode d'essai RH ;
- valider la deliberation finale ;
- envoyer une demande de stagiaire en archive de stage.

### MD / Direction

MD intervient pour :

- valider au niveau MD ;
- renseigner le feedback MD ;
- valider la Direction generale lorsque le flux MOI le demande ;
- refuser aux etapes MD, Feedback MD et Direction generale.

### Chef d'equipe et Superviseur

Ces roles interviennent uniquement pour les demandes MOD apres embauche.

Ils valident la periode d'essai dans l'ordre :

1. Chef d'equipe
2. Superviseur
3. Manager affecte / N+1
4. RH

## Types de demande

Le champ `Type de demande` peut prendre les valeurs suivantes :

- `Creation poste`
- `Remplacement`
- `Renouvellement de contrat`
- `Changement de type de contrat`
- `Demande de stagiaire`

Chaque type declenche des champs obligatoires et un flux specifique.

## Etats principaux du workflow

Les etats les plus importants sont :

- `Expression de besoin`
- `Validation N+1`
- `Validation RH`
- `Validation MD`
- `Annonce`
- `CVtheques`
- `Selection des Candidats`
- `Entretien`
- `Entretien Technique`
- `Entretien RH`
- `Deliberation`
- `Offre du Candidat`
- `Offre en Cours`
- `Date d'Embauche`
- `Affectation`
- `Matricule a Renseigner`
- `Dossier du Candidat`
- `Visite medicale`
- `Announcement`
- `Parcours d'Integration`
- `Feedback RH`
- `Feedback MD`
- `Chef d'equipe`
- `Superviseur`
- `Periode d'Essai N+1`
- `Periode d'Essai RH`
- `Direction generale`
- `Deliberation finale`
- `En cours de stage`
- `Archive de stage`
- `Acceptee`
- `Refusee`
- `Rupture`

## Flux commun de validation initiale

Toutes les demandes commencent par :

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`

Ensuite, le flux depend du type de demande.

### Soumission demandeur

Depuis `Expression de besoin`, le demandeur clique sur `Soumettre`.

Conditions :

- l'utilisateur doit etre autorise a agir comme demandeur ;
- les champs obligatoires du type de demande doivent etre renseignes ;
- pour une demande de stagiaire, les lignes documents ne sont pas obligatoires a la soumission, mais le seront plus tard a l'etape Date d'embauche.

La demande passe ensuite a `Validation N+1`.

### Validation N+1

Conditions :

- l'utilisateur doit appartenir au groupe Manager ;
- l'utilisateur doit etre le Manager N+1 reel du demandeur ;
- la demande doit etre a l'etat `Validation N+1`.

Resultat :

- validation : passage a `Validation RH` ;
- refus : passage a `Refusee`.

### Validation RH initiale

Conditions :

- l'utilisateur doit appartenir au groupe RH ;
- la demande doit etre a l'etat `Validation RH`.

Resultat selon le type :

- demande stagiaire avec duree <= 3 mois : passage direct a `Annonce` ;
- autres demandes : passage a `Validation MD`.

### Validation MD initiale

Conditions :

- l'utilisateur doit appartenir au groupe MD ;
- la demande doit etre a l'etat `Validation MD`.

Resultat selon le type :

- creation poste : passage a `Annonce` ;
- remplacement : passage a `Annonce` ;
- demande stagiaire > 3 mois : passage a `Annonce` ;
- renouvellement de contrat : passage direct a `Acceptee` ;
- changement de type de contrat : passage direct a `Acceptee`.

## Flux Creation poste

### Champs fonctionnels

La demande de creation de poste utilise les champs communs du besoin :

- categorie professionnelle : `MOD` ou `MOI` ;
- date d'embauche souhaitee ;
- motif de la demande ;
- type de contrat : CDI, CDD ou ANAPEC ;
- duree du contrat si CDD ou ANAPEC ;
- budget ;
- contenu du poste ;
- profil annexe si necessaire ;
- rattachement hierarchique ;
- tuteur d'accueil ;
- remuneration et avantages ;
- formation de base ;
- experience ;
- nombre de personnes ;
- qualites personnelles ;
- formation complementaire ;
- consequences si recrutement non accepte.

Conditions globales :

- si le type de contrat est CDD ou ANAPEC, la duree du contrat est obligatoire ;
- si la formation de base est `Autre`, le champ de precision est obligatoire.

### Flux creation poste

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`
4. `Validation MD`
5. `Annonce`
6. `CVtheques`
7. `Selection des Candidats`
8. `Entretien`
9. `Entretien Technique`
10. `Entretien RH`
11. `Deliberation`
12. `Offre du Candidat`
13. `Offre en Cours`
14. `Date d'Embauche`
15. Suite selon categorie professionnelle : MOD ou MOI

## Flux Remplacement

### Champs obligatoires specifiques

Pour une demande de remplacement, les champs suivants sont obligatoires :

- personne remplacee ;
- raison du remplacement.

Raisons possibles :

- demission ;
- licenciement ;
- retraite ;
- mutation.

Les champs communs du besoin restent applicables.

### Flux remplacement

Le flux est identique a la creation de poste :

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`
4. `Validation MD`
5. `Annonce`
6. `CVtheques`
7. `Selection des Candidats`
8. `Entretien`
9. `Entretien Technique`
10. `Entretien RH`
11. `Deliberation`
12. `Offre du Candidat`
13. `Offre en Cours`
14. `Date d'Embauche`
15. Suite selon categorie professionnelle : MOD ou MOI

## Flux Renouvellement de contrat

### Champs obligatoires specifiques

Pour une demande de renouvellement, le champ suivant est obligatoire :

- duree de renouvellement.

Le type de renouvellement peut etre :

- CDD ;
- ANAPEC.

### Flux renouvellement

Le renouvellement de contrat utilise un flux court.

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`
4. `Validation MD`
5. `Acceptee`

Refus possible depuis :

- `Validation N+1` par le Manager N+1 ;
- `Validation RH` par RH ;
- `Validation MD` par MD.

Important : ce type ne passe pas par les etapes annonce, candidats, offre, embauche, integration ou periode d'essai.

## Flux Changement de type de contrat

### Champs obligatoires specifiques

Pour une demande de changement de type de contrat, le champ `Changement de contrat` est obligatoire.

Valeurs possibles :

- CDD vers CDI ;
- ANAPEC vers CDD ;
- ANAPEC vers CDI ;
- INTERIM vers ANAPEC ;
- INTERIM vers CDD.

### Flux changement de contrat

Le changement de type de contrat utilise un flux court.

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`
4. `Validation MD`
5. `Acceptee`

Refus possible depuis :

- `Validation N+1` par le Manager N+1 ;
- `Validation RH` par RH ;
- `Validation MD` par MD.

Important : ce type ne passe pas par les etapes annonce, candidats, offre, embauche, integration ou periode d'essai.

## Flux Demande de stagiaire

### Champs obligatoires specifiques

Pour une demande de stagiaire, les champs suivants sont obligatoires :

- objet de recrutement ;
- nombre de stagiaires ;
- duree de stage en mois ;
- sujet ;
- remuneration : avec ou sans remuneration ;
- formation de base.

Si la formation de base est `Autre`, la precision est obligatoire.

### Regle de validation selon la duree

Le flux stagiaire depend de la duree :

- duree <= 3 mois : la validation MD est ignoree apres validation RH ;
- duree > 3 mois : la validation MD est obligatoire.

### Flux stagiaire duree <= 3 mois

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`
4. `Annonce`
5. `CVtheques`
6. `Selection des Candidats`
7. `Entretien`
8. `Entretien Technique`
9. `Entretien RH`
10. `Deliberation`
11. `Offre du Candidat`
12. `Offre en Cours`
13. `Date d'Embauche`
14. `En cours de stage`
15. `Archive de stage` ou sortie finale selon traitement RH

### Flux stagiaire duree > 3 mois

1. `Expression de besoin`
2. `Validation N+1`
3. `Validation RH`
4. `Validation MD`
5. `Annonce`
6. `CVtheques`
7. `Selection des Candidats`
8. `Entretien`
9. `Entretien Technique`
10. `Entretien RH`
11. `Deliberation`
12. `Offre du Candidat`
13. `Offre en Cours`
14. `Date d'Embauche`
15. `En cours de stage`
16. `Archive de stage` ou sortie finale selon traitement RH

### Conditions stagiaire a Date d'Embauche

A l'etape `Date d'Embauche`, RH doit renseigner :

- la date d'embauche pour les candidats ayant accepte l'offre ;
- les documents stagiaire.

Pour les documents stagiaire, chaque ligne doit avoir :

- un type de document ;
- un fichier.

Types de documents possibles :

- Assurance ;
- Convention de stage ;
- CIN ;
- Photo ;
- Autre.

### En cours de stage

Une fois la date d'embauche validee, la demande stagiaire passe a `En cours de stage`.

La date theorique de fin de stage est calculee depuis :

- date d'embauche du candidat ;
- duree de stage en mois.

La case `En cours de stage` reste automatiquement cochee tant que la date theorique de fin de stage n'est pas depassee. Elle ne peut pas etre decochee avant cette date.

### Archive de stage

Depuis `En cours de stage`, RH peut envoyer la demande vers `Archive de stage`.

Conditions :

- la demande doit etre de type stagiaire ;
- l'etat doit etre `En cours de stage` ;
- l'utilisateur doit appartenir au groupe RH.

## Etapes de recrutement communes

Les etapes suivantes concernent les flux longs : creation poste, remplacement et demande de stagiaire.

### Annonce

Acteur : RH.

Conditions pour valider :

- au moins une ligne d'annonce doit exister ;
- chaque ligne d'annonce doit avoir un fichier d'annonce.

Resultat :

- passage a `CVtheques`.

### CVtheques

Acteur : RH.

Conditions pour valider :

- au moins un candidat doit etre saisi ;
- chaque candidat doit avoir un nom ;
- chaque candidat doit avoir un CV.

Resultat :

- passage a `Selection des Candidats`.

### Selection des Candidats

Acteur : demandeur.

Le demandeur renseigne l'avis entretien :

- `Approuve` ;
- `Refuse` ;
- `En attente`.

Regles :

- si tous les candidats sont refuses, retour a `CVtheques` ;
- si au moins un candidat est approuve, passage a `Entretien` ;
- si une decision manque, la validation est bloquee.

### Entretien

Acteur : RH.

Conditions :

- chaque candidat approuve doit avoir une date et heure d'entretien.

Resultat :

- passage a `Entretien Technique`.

### Entretien Technique

Acteur : demandeur.

Le demandeur renseigne `Validation demandeur` pour chaque candidat :

- Oui ;
- Non.

Regles :

- si tous les candidats sont a Non, la demande passe quand meme a `Entretien RH` ;
- si un candidat est a Oui, sa FA doit etre completee ;
- si une validation demandeur manque, la validation est bloquee.

### FA demandeur

La FA est renseignee a l'etape `Entretien Technique`.

Elle est obligatoire pour les candidats retenus par le demandeur.

Champs principaux requis :

- date d'entretien ;
- presentation generale ;
- formation initiale ;
- formation complementaire ;
- experiences professionnelles / competences metiers ;
- communication orale ;
- ecoute ;
- negociation et persuasion ;
- esprit d'equipe / leadership ;
- autonomie ;
- dynamisme ;
- reactivite ;
- engagement ;
- rigueur ;
- actuellement en poste ;
- appreciations et motivations generales.

Si `Actuellement en poste = Oui`, les champs suivants sont aussi requis :

- fonction actuelle ;
- entreprise actuelle ;
- salaire actuel ;
- preavis.

Les pretentions salariales sont obligatoires et doivent etre superieures a 0, sauf pour une demande de stagiaire sans remuneration.

### Entretien RH

Acteur : RH.

RH renseigne `Validation RH` pour les candidats non refuses.

Conditions :

- chaque candidat concerne doit avoir une validation RH ;
- pour chaque candidat valide RH = Oui, la FA RH doit etre completee.

Resultat :

- passage a `Deliberation`.

### FA RH

La FA RH est renseignee uniquement par RH a l'etape `Entretien RH`.

Les champs requis sont equivalents a la FA demandeur :

- date d'entretien ;
- presentation generale ;
- formation initiale ;
- formation complementaire ;
- experiences professionnelles / competences metiers ;
- communication orale ;
- ecoute ;
- negociation et persuasion ;
- esprit d'equipe / leadership ;
- autonomie ;
- dynamisme ;
- reactivite ;
- engagement ;
- rigueur ;
- actuellement en poste ;
- appreciations et motivations generales.

Si `Actuellement en poste = Oui`, les champs fonction actuelle, entreprise actuelle, salaire actuel et preavis sont requis.

Les pretentions salariales sont obligatoires et doivent etre superieures a 0, sauf pour une demande de stagiaire sans remuneration.

### Deliberation

Acteur : RH.

Conditions :

- les candidats approuves par le demandeur doivent avoir une decision de deliberation ;
- au moins un candidat doit etre en deliberation = Oui pour continuer.

Regles :

- si aucun candidat n'est retenu en deliberation, retour a `CVtheques` ;
- si au moins un candidat est retenu, passage a `Offre du Candidat`.

### Offre du Candidat

Acteur : RH.

Conditions :

- pour chaque candidat approuve en deliberation, renseigner le nom de l'offre ;
- joindre le fichier de l'offre.

Resultat :

- passage a `Offre en Cours`.

### Offre en Cours

Acteur : RH.

RH renseigne la decision d'offre :

- Acceptee ;
- Refusee.

Regles :

- si aucune offre n'est acceptee, retour a `CVtheques` ;
- si au moins une offre est acceptee, passage a `Date d'Embauche` ;
- l'action `Refuser` sur l'offre passe directement la demande a `Refusee`.

### Date d'Embauche

Acteur : RH.

Conditions :

- chaque candidat avec offre acceptee doit avoir une date d'embauche ;
- pour les stagiaires, les documents stagiaire sont obligatoires.

Resultat selon le type :

- demande stagiaire : passage a `En cours de stage` ;
- creation poste / remplacement MOD : passage a `Affectation` ;
- creation poste / remplacement MOI : passage a `Matricule a Renseigner` ;
- autre cas de securite : passage a `Parcours d'Integration`.

## Suite post-embauche MOD

MOD correspond a la categorie professionnelle `ouvrier`.

### Flux MOD

1. `Date d'Embauche`
2. `Affectation`
3. `Matricule a Renseigner`
4. `Feedback RH`
5. `Chef d'equipe`
6. `Superviseur`
7. `Periode d'Essai N+1`
8. `Periode d'Essai RH`
9. `Deliberation finale`
10. `Acceptee`, `Rupture` ou reconduction de periode d'essai

### Affectation

Acteur : RH.

Pour chaque candidat accepte, RH renseigne :

- Chef d'equipe affecte ;
- Manager affecte ;
- Superviseur affecte.

### Matricule a Renseigner

Acteur : RH.

Pour chaque candidat accepte, RH renseigne :

- matricule a renseigner.

Resultat MOD :

- passage a `Feedback RH`.

### Feedback RH

Acteur : RH.

Conditions :

- les lignes de suivi doivent exister ;
- chaque ligne doit avoir un feedback RH.

Resultat MOD :

- passage a `Chef d'equipe`.

### Chef d'equipe

Acteur : Chef d'equipe affecte.

Conditions :

- tous les candidats concernes doivent avoir une validation Chef d'equipe.

Resultat :

- passage a `Superviseur`.

### Superviseur

Acteur : Superviseur affecte.

Conditions :

- tous les candidats concernes doivent avoir une validation Superviseur.

Resultat :

- passage a `Periode d'Essai N+1`.

### Periode d'Essai N+1 MOD

Acteur : Manager affecte.

Conditions :

- tous les candidats concernes doivent avoir une validation N+1 ;
- l'EPE doit etre completee pour tous les candidats concernes ;
- seul le Manager affecte peut valider cette etape.

Resultat :

- passage a `Periode d'Essai RH`.

### Periode d'Essai RH MOD

Acteur : RH.

Conditions :

- validation Chef d'equipe renseignee ;
- validation Superviseur renseignee ;
- validation N+1 renseignee ;
- validation RH renseignee.

Regles :

- si une decision est `Rupture`, passage a `Rupture` ;
- sinon passage a `Deliberation finale`.

## Suite post-embauche MOI

MOI correspond a la categorie professionnelle `non_cadre`.

### Flux MOI

1. `Date d'Embauche`
2. `Matricule a Renseigner`
3. `Dossier du Candidat`
4. `Visite medicale`
5. `Announcement`
6. `Parcours d'Integration`
7. `Feedback RH`
8. `Feedback MD`
9. `Periode d'Essai N+1`
10. `Periode d'Essai RH`
11. `Direction generale`
12. `Deliberation finale`
13. `Acceptee`, `Rupture` ou reconduction de periode d'essai

### Matricule a Renseigner

Acteur : RH.

Pour chaque candidat accepte, RH renseigne :

- matricule a renseigner.

Cas particulier :

- pour un changement de contrat ANAPEC, l'ancien matricule est obligatoire.

### Dossier du Candidat

Acteur : RH.

Le systeme prepare les lignes de dossier candidat.

Condition minimale avant passage a la suite :

- le document `Photos` doit etre joint pour chaque candidat recrute.

Les types de documents disponibles incluent :

- CIN ;
- certificat d'habitude physique ;
- diplomes ;
- attestations ;
- certificats des anciennes experiences ;
- fiche anthropometrique ;
- extrait de naissance ;
- certificat de residence ;
- photos ;
- acte de mariage ;
- extrait de naissance des enfants ;
- CV ;
- diplome ;
- attestation de travail ;
- RIB ;
- photo ;
- contrat ;
- autre.

### Visite medicale

Acteur : RH.

Conditions :

- chaque candidat recrute doit avoir `Visite medicale faite` ;
- la valeur doit etre Oui.

Resultat :

- passage a `Announcement`.

### Announcement

Acteur : RH.

Conditions :

- chaque candidat recrute doit avoir l'announcement envoye.

Resultat :

- generation / synchronisation des lignes d'integration ;
- passage a `Parcours d'Integration`.

### Parcours d'Integration

Acteur : RH.

Conditions :

- les lignes d'integration doivent exister ;
- chaque ligne doit avoir un departement ;
- chaque formulaire d'integration doit contenir des lignes ;
- chaque ligne d'integration doit avoir un service accueillant, une rubrique, un tuteur et une date.

Resultat :

- passage a `Feedback RH`.

### Feedback RH

Acteur : RH.

Conditions :

- chaque ligne d'integration doit avoir un feedback RH.

Resultat MOI :

- passage a `Feedback MD`.

### Feedback MD

Acteur : MD.

Conditions :

- chaque ligne d'integration doit avoir un feedback MD.

Resultat :

- passage a `Periode d'Essai N+1`.

### Periode d'Essai N+1 MOI

Acteur : demandeur ou utilisateur autorise a agir comme demandeur.

Conditions :

- chaque candidat concerne doit avoir une validation N+1 ;
- l'EPE doit etre completee.

Resultat :

- passage a `Periode d'Essai RH`.

### Periode d'Essai RH MOI

Acteur : RH.

Conditions :

- validation N+1 renseignee ;
- validation RH renseignee.

Regles :

- si une decision N+1 ou RH est `Rupture`, passage a `Rupture` ;
- sinon passage a `Direction generale`.

### Direction generale

Acteur : MD / Direction.

Conditions :

- chaque candidat concerne doit avoir une decision Direction generale.

Regles :

- si au moins une decision est `Rupture`, passage a `Rupture` ;
- sinon passage a `Deliberation finale`.

## Deliberation finale

Acteur : RH.

La deliberation finale concerne les candidats en periode d'essai.

Decision possible :

- Confirmation ;
- Reconduction ;
- Rupture du contrat.

Regles :

- si au moins une decision est `Rupture`, la demande passe a `Rupture` ;
- si au moins une decision est `Reconduction`, une nouvelle ligne de validation est creee et le flux repart en periode d'essai ;
- si toutes les decisions sont en confirmation, la demande passe a `Acceptee`.

Cas MOD :

- en cas de reconduction, le flux repart a `Chef d'equipe`.

Cas MOI :

- en cas de reconduction, le flux repart a `Periode d'Essai N+1`.

## EPE - Evaluation periode d'essai

L'EPE est obligatoire a l'etape `Periode d'Essai N+1`.

Champs requis :

- nom et prenom ;
- poste ;
- date d'entree en fonction ;
- affectation ;
- evaluateur ;
- date d'evaluation ;
- points forts ;
- points a ameliorer ;
- principales missions et realisations ;
- atteinte des resultats / objectifs ;
- potentiel pour le developpement ;
- maitrise technique ;
- capacite d'adaptation ;
- engagement et dynamisme ;
- autonomie et prise d'initiative ;
- commentaire.

Les decisions de periode d'essai possibles sont :

- Confirmation ;
- Reconduction ;
- Rupture du contrat.

## Refus

La demande peut passer a `Refusee` depuis plusieurs etapes.

### Refus Manager N+1

Possible a :

- `Validation N+1`.

Conditions :

- utilisateur dans le groupe Manager ;
- utilisateur = Manager N+1 reel du demandeur.

### Refus RH

Possible notamment a :

- `Validation RH` ;
- `CVtheques` ;
- `Entretien` ;
- `Deliberation` ;
- `Date d'Embauche` ;
- `Affectation` ;
- `Matricule a Renseigner` ;
- `Dossier du Candidat` ;
- `Visite medicale` ;
- `Announcement` ;
- `Parcours d'Integration` ;
- `Feedback RH` ;
- `Periode d'Essai RH` ;
- `Deliberation finale`.

Condition :

- utilisateur dans le groupe RH.

### Refus MD

Possible a :

- `Validation MD` ;
- `Feedback MD` ;
- `Direction generale`.

Condition :

- utilisateur dans le groupe MD.

## Modification d'une demande

Le bouton `Modifier` remet la demande a `Expression de besoin` et relance le workflow depuis le debut.

La modification est interdite dans les etats finaux :

- `Rupture` ;
- `Archive de stage` ;
- `Acceptee` ;
- `Refusee`.

Utilisateurs autorises a modifier :

- demandeur ;
- rattachement hierarchique ;
- Manager N+1 ;
- RH ;
- MD.

La modification reinitialise :

- les validateurs N+1, RH et MD ;
- les dates de validation N+1, RH et MD ;
- les indicateurs d'archivage rupture et stage.

## Securite et droits

Les principaux controles d'acces sont :

- les champs du besoin sont modifiables en `Expression de besoin` par le demandeur autorise ;
- les annonces sont creees et modifiees par RH ;
- les candidats et informations RH sont renseignes par RH ;
- les documents stagiaire sont geres par RH ;
- le dossier candidat est gere par RH ;
- la FA est modifiable uniquement a l'etape `Entretien Technique` ;
- la FA RH est modifiable uniquement par RH a l'etape `Entretien RH` ;
- l'EPE est modifiable uniquement a l'etape `Periode d'Essai N+1` ;
- les validations Chef d'equipe, Superviseur et Manager affecte sont reservees aux acteurs affectes.

## Notifications

Le module utilise le chatter Odoo et les templates email.

A chaque changement d'etat ou d'etape :

- une trace est ajoutee dans le chatter ;
- les emails correspondant a la transition sont envoyes aux groupes ou utilisateurs concernes.

Les templates sont definis dans :

- `data/mail_templates.xml`

## Rapports et impressions

Le module fournit notamment :

- rapport global de demande ;
- FA candidat ;
- FA RH ;
- EPE ;
- documents et vues de suivi selon le candidat.

Fichiers principaux :

- `data/ar_demande_recrutement_general_report.xml`
- `data/report_candidate_fa.xml`
- `data/report_araymond_layout.xml`

## Sequences

La reference de demande est generee automatiquement selon le type :

- Creation poste : `RH-CP-`
- Remplacement : `RH-REM-`
- Renouvellement : `RH-REN-`
- Changement contrat : `RH-CC-`
- Demande de stagiaire : `RH-STG-`

## Modeles principaux

- `ar.demande.de.recrutement`
- `ar.demande.recrutement.candidate`
- `ar.demande.recrutement.stagiaire.line`
- `ar.demande.recrutement.annonce`
- `ar.demande.recrutement.dossier.candidat.line`
- `ar.demande.recrutement.integration`
- `ar.recrutement.documentation`

## Structure du module

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
- `wizard/recrutement_action_wizard.py`
- `models/ar_demande_recrutement.py`
- `models/recrutement_documentation.py`

## Installation

1. Copier le module dans le dossier addons Odoo.
2. Redemarrer le serveur Odoo si necessaire.
3. Mettre a jour la liste des applications.
4. Installer ou mettre a jour le module.
5. Verifier les groupes utilisateurs : Manager, RH, MD.
6. Tester au moins un dossier par type de demande.

## Maintenance fonctionnelle

Lorsqu'une etape ou une regle change, verifier aussi :

- le champ `state` dans le modele ;
- les boutons de la vue formulaire ;
- les statusbars par type de demande ;
- les controles Python ;
- les droits et groupes ;
- les templates email ;
- les rapports ;
- ce README.

Les flux les plus sensibles sont :

- le flux court Renouvellement / Changement de contrat ;
- la bifurcation stagiaire selon duree <= 3 mois ou > 3 mois ;
- la bifurcation post-embauche MOD / MOI ;
- la reconduction de periode d'essai.
