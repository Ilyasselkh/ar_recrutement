from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
from markupsafe import Markup
import html as html_lib
import mimetypes
import re

class ARDemandeDeRecrutement(models.Model):
    _name = "ar.demande.de.recrutement"
    _description = "Demande de Recrutement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Référence", default="Nouveau", readonly=True, copy=False, tracking=True)

    state = fields.Selection([
        ("demandeur", "EXPRESSION DE BESOIN"),
        ("n1", "VALIDATION N+1"),
        ("rh", "VALIDATION RH"),
        ("md", "VALIDATION MD"),

        ("annonce", "ANNONCE"),
        ("cv_tech", "CVthèques"),
        ("selection_candidats", "Sélection des Candidats"),
        ("entretien", "Entretien"),
        ("candidat_retenu", "Entretien Technique"),
        ("validation_rh", "Entretien RH"),
        ("deliberation", "Délibération"),
        ("offre_candidat", "Offre du Candidat"),
        ("offre_en_cours", "Offre en Cours"),
        ("date_embauche", "Date d'Embauche"),
        ("affectation", "Affectation"),

        ("en_cours_stage", "En cours de stage"),

        ("matricule_a_renseigner", "Matricule à Renseigner"),
        ("dossier_candidat", "Dossier du Candidat"),
        ("visite_medicale", "Visite médicale"),
        ("envoie_annonce", "Announcement"),
        ("parcours_integration", "Parcours d'Intégration"),
        ("feedback_rh", "Feedback RH"),
        ("feedback_md", "Feedback MD"),
        ("periode_essai_n1", "Période d'Essai N+1"),
        ("periode_essai_rh", "Période d'Essai RH"),
        ("direction_generale", "Direction générale"),
        ("deliberation_finale", "Délibération finale"),
        ("rupture", "Rupture"),

        ("archive_stage","Archive de stage"),

        ("accepte", "Acceptée"),
        ("refuse", "Refusée"),
    ], default="demandeur", tracking=True, required=True)

    # Étape interne pour gérer les retours RH/Demandeur
    step = fields.Selection([
        ("draft", "Brouillon (Demandeur)"),
        ("wait_validation", "Validation hiérarchique"),
        ("rh_collect_candidates", "RH: Saisie candidats + CV"),
        ("demandeur_choose", "Demandeur: Choix candidats"),
        ("rh_schedule_interview", "RH: Planifier entretiens"),
        ("demandeur_final_choice", "Demandeur: Retenu"),
        ("rh_validate_final", "RH: Validation RH + FA RH"),
        ("rh_deliberation", "RH: Délibération"),
        ("rh_offer_candidate", "RH: Offre du candidat"),
        ("rh_offer_in_progress", "RH: Offre en cours"),
        ("rh_hiring_date", "RH: Date d'embauche"),
        ("done", "Terminé"),
    ], default="draft", tracking=True)

    # Champs grisés 
    demandeur_id = fields.Many2one(
        "res.users", string="Demandeur", default=lambda self: self.env.user,
        readonly=True, tracking=True
    )

    employee_id = fields.Many2one(
        "hr.employee", string="Employé (RH)",
        compute="_compute_employee", store=True, readonly=True
    )
    manager_id = fields.Many2one(
        "res.users", string="Manager N+1",
        compute="_compute_manager", store=True, readonly=True, tracking=True
    )
    department_id = fields.Many2one(
        "hr.department", string="Département",
        compute="_compute_department", store=True, readonly=True
    )

    has_retenu_final = fields.Boolean(
        string="A un candidat retenu",
        compute="_compute_has_retenu_final",
        store=False,
    )

    current_user_is_rh = fields.Boolean(
        string="Utilisateur RH",
        compute="_compute_current_user_is_rh",
        store=False,
    )
    current_user_can_act_as_demandeur = fields.Boolean(
        string="Peut agir comme demandeur",
        compute="_compute_current_user_can_act_as_demandeur",
        store=False,
    )

    is_rupture_archived = fields.Boolean(
        string="Rupture archivée",
        default=False,
        tracking=True
    )

    is_stage_archived = fields.Boolean(
        string="Stage archivé",
        default=False,
        tracking=True
    )

    date_validation_n1 = fields.Datetime(string="Date validation N+1", readonly=True, tracking=True)
    date_validation_rh = fields.Datetime(string="Date validation RH", readonly=True, tracking=True)
    date_validation_md = fields.Datetime(string="Date validation MD", readonly=True, tracking=True)
    validateur_n1_id = fields.Many2one("res.users", string="Valide par N+1", readonly=True, tracking=True)
    validateur_rh_id = fields.Many2one("res.users", string="Valide par RH", readonly=True, tracking=True)
    validateur_md_id = fields.Many2one("res.users", string="Valide par MD", readonly=True, tracking=True)

    integration_ids = fields.One2many(
        "ar.demande.recrutement.integration", "demande_id",
        string="Parcours d'intégration"
    )

    validation_integration_ids = fields.One2many(
        "ar.demande.recrutement.integration", "validation_demande_id",
        string="Validation période d'essai"
    )

    dossier_candidat_line_ids = fields.One2many(
        "ar.demande.recrutement.dossier.candidat.line",
        "demande_id",
        string="Dossier du Candidat"
    )

    announcement_civility = fields.Selection(
        [
            ("m", "M."),
            ("mme", "Mme"),
        ],
        string="Civilité",
        compute="_compute_announcement_civility",
        inverse="_inverse_announcement_civility",
        store=False,
    )

    def _report_clean_html(self, html_value):
        """Nettoie un HTML vide pour éviter d'afficher des blocs vides dans le report."""
        if not html_value:
            return False

        text_only = re.sub(r"<[^>]+>", "", html_value or "")
        text_only = (text_only or "").replace("&nbsp;", " ").strip()

        if not text_only:
            return False

        return Markup(html_value)

    def has_field_value(self, field_name):
        """Retourne True si le champ contient une vraie valeur exploitable dans le report."""
        self.ensure_one()
        field = self._fields.get(field_name)
        if not field:
            return False

        value = self[field_name]

        if field.type in ("char", "text", "html", "selection", "date", "datetime", "many2one"):
            if field.type == "html":
                return bool(self._report_clean_html(value))
            return bool(value)

        if field.type in ("integer", "float", "monetary"):
            return value not in (False, None, 0, 0.0)

        if field.type == "boolean":
            return bool(value)

        if field.type == "binary":
            return bool(value)

        if field.type in ("one2many", "many2many"):
            return bool(value)

        return bool(value)

    def get_field_display(self, field_name):
        """Retourne la valeur formatée d'un champ pour le report."""
        self.ensure_one()
        field = self._fields.get(field_name)
        if not field:
            return ""

        value = self[field_name]

        if field.type == "selection":
            return dict(field.selection).get(value, "")

        if field.type == "many2one":
            return value.display_name if value else ""

        if field.type == "boolean":
            return _("Oui") if value else _("Non")

        if field.type == "html":
            return self._report_clean_html(value)

        if field.type == "binary":
            return _("Oui")

        return value or ""
    
    def action_print_general_report(self):
        self.ensure_one()
        return self.env.ref("ar_recrutement.action_report_ar_demande_recrutement_general").report_action(self)

    def get_report_validation_history(self):
        self.ensure_one()
        entries = []

        def format_dt(dt_value):
            if not dt_value:
                return ""
            local_dt = fields.Datetime.context_timestamp(self, dt_value)
            return local_dt.strftime("%d/%m/%Y %H:%M:%S")

        entries.append({
            "label": _("Creation"),
            "value": "%s - %s" % (
                self.create_uid.name if self.create_uid else "-",
                format_dt(self.create_date),
            ),
            "detail": _("Creation de la demande"),
        })

        workflow_messages = self.message_ids.filtered(
            lambda message: message.body and "Changement d'etape effectue par" in message.body
        ).sorted("date")

        for message in workflow_messages:
            body = html_lib.unescape(re.sub(r"<[^>]+>", "", message.body or "")).strip()
            match = re.search(
                r"Changement d'etape effectue par (.*?) : (.*?) / (.*?) -> (.*?) / (.*?)\.",
                body,
            )
            if match:
                user_name, old_state, old_step, new_state, new_step = match.groups()
                entries.append({
                    "label": new_state,
                    "value": "%s - %s" % (user_name, format_dt(message.date)),
                    "detail": "%s / %s -> %s / %s" % (old_state, old_step, new_state, new_step),
                })
            else:
                entries.append({
                    "label": _("Workflow"),
                    "value": "%s - %s" % (
                        message.author_id.name if message.author_id else "-",
                        format_dt(message.date),
                    ),
                    "detail": body,
                })

        return entries

    def get_report_accepted_candidates(self):
        self.ensure_one()
        return self.candidate_ids.filtered(lambda candidate: candidate.offre_decision == "accepte")

    def get_report_candidate_integration(self, candidate):
        self.ensure_one()
        return self.integration_ids.filtered(lambda line: line.candidate_id == candidate)[:1]

    def has_general_report_content(self):
        """Optionnel : utile si tu veux conditionner certains blocs globaux."""
        self.ensure_one()
        return True

    def action_envoyer_archive_stage(self):
        for rec in self:
            if rec.demande_type != "demande_stagiaire":
                raise AccessError(_("Cette action est réservée uniquement aux demandes de stagiaire."))

            if rec.state != "en_cours_stage":
                raise AccessError(_("Cette action n'est autorisée qu'à l'état En cours de stage."))

            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Vous n'êtes pas autorisé à envoyer cette demande à l'archive de stage."))

            rec.write({
                "state": "archive_stage",
                "step": "done",
                "is_stage_archived": False,
            })

    def action_archiver_stage(self):
        for rec in self:
            if rec.state != "archive_stage":
                raise AccessError(_("L'archivage n'est autorisé que pour les demandes à l'état Archive de stage."))

            if rec.demande_type != "demande_stagiaire":
                raise AccessError(_("Cette action est réservée uniquement aux demandes de stagiaire."))

            rec.write({"is_stage_archived": True})

    def action_archiver_rupture(self):
        for rec in self:
            if rec.state != "rupture":
                raise AccessError(_("L'archivage n'est autorisé que pour les demandes à l'état Rupture."))
            rec.write({"is_rupture_archived": True})

    def _check_is_rattachement_hierarchique(self):
        self.ensure_one()
        if not self.rattachement_hierarchique_id or self.rattachement_hierarchique_id.id != self.env.user.id:
            raise AccessError(_("Seule la personne renseignée dans 'Rattachement hiérarchique' peut valider cette étape."))

    @api.depends("candidate_ids.retenu_final", "candidate_ids.demandeur_decision")
    def _compute_has_retenu_final(self):
        for rec in self:
            rec.has_retenu_final = any(
                c.retenu_final == "oui" and c.demandeur_decision != "refuse"
                for c in rec.candidate_ids
            )

    @api.depends_context("uid")
    def _compute_current_user_is_rh(self):
        is_rh = self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh")
        for rec in self:
            rec.current_user_is_rh = is_rh

    @api.depends("demandeur_id", "rattachement_hierarchique_id")
    @api.depends_context("uid")
    def _compute_current_user_can_act_as_demandeur(self):
        current_user_id = self.env.user.id
        for rec in self:
            rec.current_user_can_act_as_demandeur = current_user_id in (
                rec.demandeur_id.id,
                rec.rattachement_hierarchique_id.id,
            )

    def _check_can_act_as_demandeur(self):
        self.ensure_one()
        if self.env.user.id not in (self.demandeur_id.id, self.rattachement_hierarchique_id.id):
            raise AccessError(_("Seul le demandeur ou le rattachement hiérarchique peut continuer cette étape."))

    def _sync_step_from_state(self):
        mapping = {
            "demandeur": "draft",
            "n1": "wait_validation",
            "rh": "wait_validation",
            "md": "wait_validation",
            "annonce": "wait_validation",
            "cv_tech": "rh_collect_candidates",
            "selection_candidats": "demandeur_choose",
            "entretien": "rh_schedule_interview",
            "candidat_retenu": "demandeur_final_choice",
            "validation_rh": "rh_validate_final",
            "deliberation": "rh_deliberation",
            "offre_candidat": "rh_offer_candidate",
            "offre_en_cours": "rh_offer_in_progress",
            "date_embauche": "rh_hiring_date",
            "affectation": "wait_validation",
            "en_cours_stage": "wait_validation",
            "matricule_a_renseigner": "wait_validation",
            "envoie_annonce": "wait_validation",
            "dossier_candidat": "wait_validation",
            "visite_medicale": "wait_validation",
            "parcours_integration": "wait_validation",
            "feedback_rh": "wait_validation",
            "feedback_md": "wait_validation",
            "periode_essai_n1": "wait_validation",
            "periode_essai_rh": "wait_validation",
            "direction_generale": "wait_validation",
            "deliberation_finale": "wait_validation",
            "rupture": "done",
            "archive_stage": "done",
            "accepte": "done",
            "refuse": "done",
        }
        for rec in self:
            target_step = mapping.get(rec.state)
            if target_step and rec.step != target_step:
                rec.step = target_step

    @api.depends("demandeur_id")
    def _compute_employee(self):
        for rec in self:
            rec.employee_id = self.env["hr.employee"].search([("user_id", "=", rec.demandeur_id.id)], limit=1)

    @api.depends("employee_id")
    def _compute_manager(self):
        for rec in self:
            
            mgr_user = rec.employee_id.parent_id.user_id if rec.employee_id and rec.employee_id.parent_id else False
            rec.manager_id = mgr_user

    @api.depends("employee_id")
    def _compute_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id if rec.employee_id else False

    # =========================
    # EMAILS WORKFLOW 
    # =========================
    def _clean_header(self, value):
        if not value:
            return False
        return str(value).replace("\n", "").replace("\r", "").strip()

    def _get_user_email(self, user):
        if not user:
            return False
        user = user.sudo()
        email = user.partner_id.email or user.email
        return self._clean_header(email) if email else False

    def _get_demandeur_email(self):
        self.ensure_one()
        return self._get_user_email(self.demandeur_id)

    def _get_demandeur_recipient_emails(self):
        self.ensure_one()
        emails = []
        for user in (self.demandeur_id, self.rattachement_hierarchique_id):
            email = self._get_user_email(user)
            if email and email not in emails:
                emails.append(email)
        return emails

    def _get_manager_email(self):
        self.ensure_one()
        return self._get_user_email(self.manager_id)

    def _get_group_emails(self, group_xmlid):
        """Retourne la liste emails des users d'un groupe."""
        grp = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not grp:
            return []
        emails = set()
        for u in grp.user_ids:
            e = self._get_user_email(u)
            if e:
                emails.add(e)
        return list(emails)

    def _get_employee_emails(self):
        """Retourne les emails professionnels des employes actifs."""
        emails = set()
        employees = self.env["hr.employee"].sudo().search([])
        for employee in employees:
            email = employee.work_email or employee.user_id.partner_id.email or employee.user_id.email
            email = self._clean_header(email) if email else False
            if email:
                emails.add(email)
        return list(emails)

    def _get_announcement_candidates(self):
        self.ensure_one()
        candidates = self.candidate_ids.filtered(
            lambda c: c.offre_decision == "accepte"
            and c.hiring_date
            and not c.is_refused_line
        )
        return candidates

    def _get_announcement_candidate(self):
        self.ensure_one()
        candidate_id = self.env.context.get("announcement_candidate_id")
        if candidate_id:
            candidate = self.candidate_ids.filtered(lambda c: c.id == candidate_id)[:1]
            if candidate:
                return candidate
        return self._get_announcement_candidates()[:1]

    def _compute_announcement_civility(self):
        for rec in self:
            candidate = rec._get_announcement_candidate()
            rec.announcement_civility = candidate.announcement_civility if candidate else False

    def _inverse_announcement_civility(self):
        for rec in self:
            candidate = rec._get_announcement_candidate()
            if candidate:
                candidate.announcement_civility = rec.announcement_civility

    def _get_announcement_civility_label(self):
        self.ensure_one()
        candidate = self._get_announcement_candidate()
        if not candidate:
            return ""
        return dict(candidate._fields["announcement_civility"].selection).get(candidate.announcement_civility, "")

    def _get_announcement_photo_line(self):
        self.ensure_one()
        candidate = self._get_announcement_candidate()
        return self.dossier_candidat_line_ids.filtered(
            lambda l: l.document_type == "photos"
            and l.document_file
            and (not candidate or l.candidate_id == candidate)
        )[:1]

    def _get_announcement_photo_data_uri(self):
        self.ensure_one()
        photo_line = self._get_announcement_photo_line()
        if not photo_line:
            return False

        photo_data = photo_line.document_file
        if isinstance(photo_data, bytes):
            photo_data = photo_data.decode()

        mimetype = mimetypes.guess_type(photo_line.document_filename or "")[0]
        if not mimetype or not mimetype.startswith("image/"):
            mimetype = "image/jpeg"

        return "data:%s;base64,%s" % (mimetype, photo_data)

    def _format_announcement_date(self):
        self.ensure_one()
        candidate = self._get_announcement_candidate()
        hiring_date = candidate.hiring_date if candidate else self.date_embauche_effective
        if not hiring_date:
            return ""

        months = {
            1: "Janvier",
            2: "Février",
            3: "Mars",
            4: "Avril",
            5: "Mai",
            6: "Juin",
            7: "Juillet",
            8: "Août",
            9: "Septembre",
            10: "Octobre",
            11: "Novembre",
            12: "Décembre",
        }
        return "%02d %s %s" % (hiring_date.day, months.get(hiring_date.month), hiring_date.year)

    def _send_template(self, xmlid, email_to_list):
        """Envoi mail template à une liste d'emails."""
        self.ensure_one()
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template:
            return

        recipients = [self._clean_header(e) for e in (email_to_list or [])]
        recipients = [e for e in recipients if e]
        if not recipients:
            return

        email_values = {
            "email_to": self._clean_header(",".join(recipients)),
            "reply_to": self._clean_header(self.env.user.partner_id.email or self.env.user.email or ""),
        }
        template.send_mail(self.id, force_send=True, email_values=email_values)

    def action_send_announcement_mail(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Seul le groupe RH peut envoyer l'announcement."))
            if rec.state != "envoie_annonce":
                raise AccessError(_("L'envoi de l'announcement est autorisé uniquement à l'état Announcement."))

            candidates = rec._get_announcement_candidates()
            if not candidates:
                raise ValidationError(_("Aucun candidat recruté trouvé pour générer l'announcement."))

            missing = []
            for candidate in candidates:
                if not candidate.announcement_civility:
                    missing.append(_("Announcement : Civilité (%s)") % candidate.candidate_name)
                photo_line = rec.with_context(announcement_candidate_id=candidate.id)._get_announcement_photo_line()
                if not photo_line:
                    missing.append(_("Announcement : Photo (%s)") % candidate.candidate_name)
            rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

            recipients = rec._get_employee_emails()
            if not recipients:
                raise ValidationError(_("Aucun email employé trouvé pour envoyer l'announcement."))

            template = rec.env.ref("ar_recrutement.mail_template_rec_announcement_to_employees", raise_if_not_found=False)
            if not template:
                raise ValidationError(_("Template email announcement introuvable."))

            clean_recipients = [rec._clean_header(email) for email in recipients]
            clean_recipients = [email for email in clean_recipients if email]
            pending_candidates = candidates.filtered(lambda candidate: not candidate.announcement_sent)
            if not pending_candidates:
                raise ValidationError(_("Tous les announcements ont déjà été envoyés."))

            for candidate in pending_candidates:
                template.with_context(announcement_candidate_id=candidate.id).send_mail(
                    rec.id,
                    force_send=True,
                    email_values={
                        "email_to": rec._clean_header(",".join(clean_recipients)),
                        "reply_to": rec._clean_header(rec.env.user.partner_id.email or rec.env.user.email or ""),
                    },
                )
                candidate.write({
                    "announcement_sent": True,
                    "announcement_sent_date": fields.Date.context_today(rec),
                })
            rec.message_post(
                body=_("L'email d'announcement a été envoyé pour %s candidat(s) à %s employé(s).") % (len(pending_candidates), len(clean_recipients))
            )

    def _send_on_state_step_change(self, old_state, old_step, new_state, new_step):
        """Règles emails selon ton workflow."""
        self.ensure_one()

        RH_GRP = "ar_recrutement.group_ar_recrutement_rh"
        MD_GRP = "ar_recrutement.group_ar_recrutement_md"

        if old_state == "demandeur" and old_step == "draft" and new_state == "n1" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_manager_validation",
                [self._get_manager_email()],
            )
            return

        if old_state == "n1" and new_state == "rh" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_manager_approved_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_processing",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "rh" and old_step == "wait_validation" and new_state == "md" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_rh_approved_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_to_md_processing",
                self._get_group_emails(MD_GRP),
            )
            return

        if old_state == "rh" and old_step == "wait_validation" and new_state == "annonce" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_annonce",
                self._get_group_emails(RH_GRP),
            )
            return

        # MD valide -> ANNONCE
        if old_state == "md" and old_step == "wait_validation" and new_state == "annonce" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_annonce",
                self._get_group_emails(RH_GRP),
            )
            return

        # RH valide ANNONCE -> RH : Annonce approuvée, saisir candidats (CV-Tech)
        if old_state == "annonce" and old_step == "wait_validation" and new_state == "cv_tech" and new_step == "rh_collect_candidates":
            self._send_template(
                "ar_recrutement.mail_template_rec_md_approved_to_rh",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "cv_tech" and old_step == "rh_collect_candidates" and new_state == "selection_candidats" and new_step == "demandeur_choose":
            self._send_template(
                "ar_recrutement.mail_template_rec_candidates_ready_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        if old_state == "selection_candidats" and old_step == "demandeur_choose" and new_state == "entretien" and new_step == "rh_schedule_interview":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_schedule_interview",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "entretien" and old_step == "rh_schedule_interview" and new_state == "candidat_retenu" and new_step == "demandeur_final_choice":
            self._send_template(
                "ar_recrutement.mail_template_rec_interview_planned_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        if old_state == "candidat_retenu" and old_step == "demandeur_final_choice" and new_state == "validation_rh" and new_step == "rh_validate_final":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_validation_rh",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "validation_rh" and old_step == "rh_validate_final" and new_state == "deliberation" and new_step == "rh_deliberation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_deliberation",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "deliberation" and old_step == "rh_deliberation" and new_state == "offre_candidat" and new_step == "rh_offer_candidate":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_offer_candidate",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "offre_candidat" and old_step == "rh_offer_candidate" and new_state == "offre_en_cours" and new_step == "rh_offer_in_progress":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_offer_in_progress",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "offre_en_cours" and old_step == "rh_offer_in_progress" and new_state == "date_embauche" and new_step == "rh_hiring_date":
            self._send_template(
                "ar_recrutement.mail_template_rec_offer_accepted_to_rh",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "offre_en_cours" and old_step == "rh_offer_in_progress" and new_state == "cv_tech" and new_step == "rh_collect_candidates":
            self._send_template(
                "ar_recrutement.mail_template_rec_offer_refused_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return
        
        # Date d'embauche -> En cours de stage
        if old_state == "date_embauche" and old_step == "rh_hiring_date" and new_state == "en_cours_stage" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_en_cours_stage",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_en_cours_stage_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # En cours de stage -> Parcours d'intégration
        if old_state == "en_cours_stage" and old_step == "wait_validation" and new_state == "parcours_integration" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_parcours_integration",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_parcours_integration_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return
        
        # En cours de stage -> Archive de stage
        if old_state == "en_cours_stage" and old_step == "wait_validation" and new_state == "archive_stage" and new_step == "done":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_archive_stage",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_archive_stage_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # En cours de stage -> Acceptée
        if old_state == "en_cours_stage" and old_step == "wait_validation" and new_state == "accepte" and new_step == "done":
            return

        # Date d'embauche -> Parcours d'intégration
        # Date d'embauche -> Matricule à Renseigner (cas MOI)
        if old_state == "date_embauche" and old_step == "rh_hiring_date" and new_state == "matricule_a_renseigner" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_matricule_a_renseigner",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_matricule_a_renseigner_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Matricule à Renseigner -> Dossier du Candidat
        if old_state == "matricule_a_renseigner" and old_step == "wait_validation" and new_state == "dossier_candidat" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_dossier_candidat",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_dossier_candidat_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Dossier du Candidat -> Visite médicale
        if old_state == "dossier_candidat" and old_step == "wait_validation" and new_state == "visite_medicale" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_visite_medicale",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_visite_medicale_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Visite médicale -> Announcement
        if old_state == "visite_medicale" and old_step == "wait_validation" and new_state == "envoie_annonce" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_envoie_annonce",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_envoie_annonce_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        if (
            (old_state == "date_embauche" and old_step == "rh_hiring_date")
            or (old_state == "envoie_annonce" and old_step == "wait_validation")
        ) and new_state == "parcours_integration" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_parcours_integration",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_parcours_integration_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return
        
        # Date d'embauche -> Affectation (cas MOD / ouvrier)
        if old_state == "date_embauche" and old_step == "rh_hiring_date" and new_state == "affectation" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_affectation",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_affectation_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Affectation -> Matricule à Renseigner (cas MOD / ouvrier)
        if old_state == "affectation" and old_step == "wait_validation" and new_state == "matricule_a_renseigner" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_matricule_a_renseigner",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_matricule_a_renseigner_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Matricule à Renseigner -> Feedback RH (cas MOD / ouvrier)
        if old_state == "matricule_a_renseigner" and old_step == "wait_validation" and new_state == "feedback_rh" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_feedback_rh",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_feedback_rh_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Parcours d'intégration -> Feedback RH
        if old_state == "parcours_integration" and old_step == "wait_validation" and new_state == "feedback_rh" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_feedback_rh",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_feedback_rh_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Feedback RH -> Feedback MD
        if old_state == "feedback_rh" and old_step == "wait_validation" and new_state == "feedback_md" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_md_feedback_md",
                self._get_group_emails(MD_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_feedback_md_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Feedback MD -> Période d'essai N+1
        if old_state == "feedback_md" and old_step == "wait_validation" and new_state == "periode_essai_n1" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_n1_periode_essai",
                [self._get_user_email(self.rattachement_hierarchique_id)],
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_periode_essai_n1_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Période d'essai N+1 -> Période d'essai RH
        if old_state == "periode_essai_n1" and old_step == "wait_validation" and new_state == "periode_essai_rh" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_periode_essai",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_periode_essai_rh_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return
        
        # Période d'essai RH -> Direction générale
        if old_state == "periode_essai_rh" and old_step == "wait_validation" and new_state == "direction_generale" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_md_direction_generale",
                self._get_group_emails(MD_GRP),
            )
            return
        
        # Période d'essai RH -> Acceptée (cas MOD / ouvrier)
        if old_state == "periode_essai_rh" and old_step == "wait_validation" and new_state == "accepte" and new_step == "done":
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_approved_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Direction générale -> Acceptée
        if old_state == "direction_generale" and old_step == "wait_validation" and new_state == "deliberation_finale" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_rh_deliberation_finale",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "direction_generale" and old_step == "wait_validation" and new_state == "rupture" and new_step == "done":
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_rupture_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_rupture_to_rh",
                self._get_group_emails(RH_GRP),
            )
            return

        if old_state == "deliberation_finale" and old_step == "wait_validation" and new_state == "accepte" and new_step == "done":
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_approved_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Direction générale -> Rupture
        if old_state == "deliberation_finale" and old_step == "wait_validation" and new_state == "rupture" and new_step == "done":
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_rupture_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_rupture_to_rh",
                self._get_group_emails(RH_GRP),
            )
            return

        # Acceptée après Direction générale
        if old_state == "direction_generale" and old_step == "wait_validation" and new_state == "accepte" and new_step == "done":
            self._send_template(
                "ar_recrutement.mail_template_rec_direction_generale_approved_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        if old_state == "deliberation_finale" and old_step == "wait_validation" and new_state == "periode_essai_n1" and new_step == "wait_validation":
            self._send_template(
                "ar_recrutement.mail_template_rec_to_n1_periode_essai",
                [self._get_user_email(self.rattachement_hierarchique_id)],
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_periode_essai_n1_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Retour à Cv-Tech si aucun candidat retenu (Validation demandeur = tous Non)
        if (
            old_state == "candidat_retenu"
            and old_step == "demandeur_final_choice"
            and new_state == "cv_tech"
            and new_step == "rh_collect_candidates"
        ):
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Retour à Cv-Tech depuis Validation RH (tous Validation RH = Non)
        if (
            old_state == "validation_rh"
            and old_step == "rh_validate_final"
            and new_state == "cv_tech"
            and new_step == "rh_collect_candidates"
        ):
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Retour à Cv-Tech depuis Délibération (Décision finale = Non)
        if (
            old_state == "deliberation"
            and old_step == "rh_deliberation"
            and new_state == "cv_tech"
            and new_step == "rh_collect_candidates"
        ):
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return
        
        # Retour à Cv-Tech depuis Sélection des candidats (tous Avis entretien = Refusé)
        if (
            old_state == "selection_candidats"
            and old_step == "demandeur_choose"
            and new_state == "cv_tech"
            and new_step == "rh_collect_candidates"
        ):
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected",
                self._get_group_emails(RH_GRP),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_back_to_cvtech_no_selected_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

        # Rupture depuis période d'essai N+1 ou RH
        if new_state == "rupture":
            self._send_template(
                "ar_recrutement.mail_template_rec_rupture_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            self._send_template(
                "ar_recrutement.mail_template_rec_rupture_to_rh",
                self._get_group_emails(RH_GRP),
            )
            return

        if new_state == "refuse":
            self._send_template(
                "ar_recrutement.mail_template_rec_refused_to_demandeur",
                self._get_demandeur_recipient_emails(),
            )
            return

    def _post_workflow_trace(self, old_state, old_step, new_state, new_step):
        self.ensure_one()
        state_labels = dict(self._fields["state"].selection)
        step_labels = dict(self._fields["step"].selection)
        self.message_post(
            body=_("Changement d'etape effectue par %s : %s / %s -> %s / %s.") % (
                self.env.user.name,
                state_labels.get(old_state, old_state),
                step_labels.get(old_step, old_step),
                state_labels.get(new_state, new_state),
                step_labels.get(new_step, new_step),
            )
        )

    # Type de demande
    demande_type = fields.Selection([
        ("creation_poste", "Création poste"),
        ("remplacement", "Remplacement"),
        ("renouvellement", "Renouvellement de contrat"),
        ("changement_contrat", "Changement de type de contrat"),
        ("demande_stagiaire", "Demande de stagiaire"),
    ], string="Type de demande", required=True, tracking=True)

    stagiaire_nombre = fields.Integer(string="Nombre", tracking=True)
    stagiaire_duree_mois = fields.Integer(string="Durée de stage (en mois)", tracking=True)
    stagiaire_remuneration = fields.Selection([
        ("avec", "Avec rémunération"),
        ("sans", "Sans rémunération"),
    ], string="Rémunération", tracking=True)

    stagiaire_sujet = fields.Char(string="Sujet", tracking=True)

    stagiaire_line_ids = fields.One2many(
        "ar.demande.recrutement.stagiaire.line",
        "demande_id",
        string="Sujet & Assurance"
    )

    # Champs "Création poste"
    categorie_prof = fields.Selection([
        ("ouvrier", "MOD"),
        ("non_cadre", "MOI"),
    ], tracking=True)

    date_embauche_souhaitee = fields.Date(tracking=True)
    motif_demande = fields.Text(tracking=True)

    type_contrat = fields.Selection([
        ("cdi", "CDI"),
        ("cdd", "CDD (classique / apprentissage)"),
        ("anapec", "ANAPEC"),
    ], string="Type de contrat", tracking=True)

    duree_contrat = fields.Char(string="Durée(En mois)", tracking=True)  
    recrutement_budget = fields.Selection([("oui", "Oui"), ("non", "Non")], tracking=True)

    contenu_poste = fields.Html(string="Contenu du poste / tâches principales", tracking=True)

    profil_annexe = fields.Binary(string="Profil en annexe", attachment=True, tracking=True)

    rattachement_hierarchique_id = fields.Many2one("res.users", string="Rattachement hiérarchique", tracking=True)
    nom_tuteur_id = fields.Many2one("res.users", string="Nom du tuteur d’accueil", tracking=True)

    remuneration_avantages = fields.Text(tracking=True)
    offre_candidat_nom = fields.Char(string="Nom de l'Offre", tracking=True)
    offre_candidat_file = fields.Binary(string="Fichier de l'Offre", attachment=True)
    offre_candidat_filename = fields.Char(string="Nom du fichier de l'Offre")
    deliberation_decision_finale = fields.Selection(
        [("oui", "Oui"), ("non", "Non")],
        string="Décision finale",
        tracking=True,
    )
    deliberation_commentaire = fields.Text(string="Commentaire", tracking=True)
    date_embauche_effective = fields.Date(string="Date d'embauche", tracking=True)
    ancien_matricule = fields.Char(string="Ancien Matricule", tracking=True)
    nouvelle_affectation_matricule = fields.Char(string="Nouveau Affectation de matricule", tracking=True)
    visite_medicale_faite = fields.Boolean(string="Visite médicale faite", tracking=True)
    visite_medicale_faite_radio = fields.Selection(
        [("oui", "Oui"), ("non", "Non")],
        string="Visite médicale faite",
        compute="_compute_visite_medicale_faite_radio",
        inverse="_inverse_visite_medicale_faite_radio",
        readonly=False,
    )
    # Profil souhaité
    formation_base = fields.Selection([
        ("bac", "Bac"),
        ("bac2", "Bac+2"),
        ("licence", "Licence"),
        ("master", "Master"),
        ("ingenieur", "Ingénieur"),
        ("autre", "Autre"),
    ], string="Formation de base", tracking=True)

    formation_base_autre = fields.Char(string="Préciser (Autre formation)", tracking=True)  

    experience_annees = fields.Integer(string="Expérience (années)", tracking=True)
    nombre_personnes = fields.Integer(string="Nombre de personnes", tracking=True)

    qualites_personnelles = fields.Text(string="Qualités personnelles", tracking=True)

    formation_complementaire = fields.Text(string="Formation complémentaire éventuellement nécessaire", tracking=True)

    consequences_si_refus = fields.Text(string="Conséquences si recrutement non accepté", tracking=True)

    # =========================
    # ANNONCE 
    # =========================
    annonce_ids = fields.One2many(
        "ar.demande.recrutement.annonce",
        "demande_id",
        string="Annonces",
        tracking=True,
    )

    # ---- Remplacement ----
    personne_remplacee_id = fields.Many2one(
        "res.users",
        string="Nom de la personne remplacée",
        tracking=True
    )
    raison_remplacement = fields.Selection([
        ("demission", "Démission"),
        ("licenciement", "Licenciement"),
        ("retraite", "Retraite"),
        ("mutation", "Mutation"),
    ], string="Raison du remplacement", tracking=True)

    # ---- Renouvellement ----
    renouvellement_type = fields.Selection([
        ("cdd", "CDD"),
        ("anapec", "ANAPEC"),
    ], string="Renouvellement", tracking=True)
    renouvellement_duree = fields.Char(string="Durée de renouvellement", tracking=True)

    # ---- Changement contrat ----
    changement_contrat = fields.Selection([
        ("cdd_to_cdi", "CDD => CDI"),
        ("anapec_to_cdd", "ANAPEC => CDD"),
        ("anapec_to_cdi", "ANAPEC => CDI"),
        ("interim_to_anapec", "INTÉRIM => ANAPEC"),
        ("interim_to_cdd", "INTÉRIM => CDD"),
    ], string="Changement de contrat", tracking=True)

    # ---- Lignes candidats ----
    candidate_ids = fields.One2many(
        "ar.demande.recrutement.candidate", "demande_id",
        string="Candidats"
    )
    candidate_display_ids = fields.Many2many(
        "ar.demande.recrutement.candidate",
        "ar_demande_candidate_display_rel",
        "demande_id",
        "candidate_id",
        compute="_compute_candidate_display_ids",
        string="Candidats",
    )
    offer_display_candidate_ids = fields.Many2many(
        "ar.demande.recrutement.candidate",
        "ar_demande_offer_display_rel",
        "demande_id",
        "candidate_id",
        compute="_compute_candidate_display_ids",
        string="Offre du Candidat",
    )
    hiring_display_candidate_ids = fields.Many2many(
        "ar.demande.recrutement.candidate",
        "ar_demande_hiring_display_rel",
        "demande_id",
        "candidate_id",
        compute="_compute_candidate_display_ids",
        string="Date d'embauche & Matricule",
    )
    medical_display_candidate_ids = fields.Many2many(
        "ar.demande.recrutement.candidate",
        "ar_demande_medical_display_rel",
        "demande_id",
        "candidate_id",
        compute="_compute_candidate_display_ids",
        string="Visite médicale",
    )

    objet_recrutement = fields.Char(
        string="Objet de recrutement",
        tracking=True
    )

    @api.depends("candidate_ids", "candidate_ids.demandeur_decision")
    def _compute_candidate_display_ids(self):
        for rec in self:
            rec.candidate_display_ids = rec.candidate_ids
            rec.offer_display_candidate_ids = rec.candidate_ids.filtered(
                lambda candidate: candidate.demandeur_decision == "approuve"
            )
            rec.hiring_display_candidate_ids = rec.candidate_ids.filtered(
                lambda candidate: candidate.offre_decision == "accepte"
            )
            rec.medical_display_candidate_ids = rec.candidate_ids.filtered(
                lambda candidate: candidate.offre_decision == "accepte"
                and candidate.hiring_date
            )

    def _get_demande_prefix(self, demande_type):
        prefixes = {
            "creation_poste": "RH-CP-",
            "remplacement": "RH-REM-",
            "renouvellement": "RH-REN-",
            "changement_contrat": "RH-CC-",
            "demande_stagiaire": "RH-STG-",
        }
        return prefixes.get(demande_type, "DR-")
    
    def _is_non_stagiaire_standard_flow(self):
        self.ensure_one()
        return self.demande_type in (
            "creation_poste",
            "remplacement",
            "renouvellement",
            "changement_contrat",
        )

    def _open_action_wizard(self, action_type):
        self.ensure_one()
        return {
            "name": _("Confirmation"),
            "type": "ir.actions.act_window",
            "res_model": "ar.demande.recrutement.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_demande_id": self.id,
                "default_action_type": action_type,
            }
        }

    def action_open_modify_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("modify")

    def _open_recruitment_popup(self, xmlid, title):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "ar.demande.de.recrutement",
            "view_mode": "form",
            "view_id": self.env.ref(xmlid).id,
            "res_id": self.id,
            "target": "new",
        }

    def action_open_entretien_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_entretien",
            _("Entretien"),
        )

    def action_open_deliberation_offre_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_deliberation_offre",
            _("Offre du Candidat"),
        )

    def action_open_date_matricule_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_date_matricule",
            _("Date d'embauche & Matricule"),
        )

    def action_open_dossier_candidat_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_dossier_candidat",
            _("Dossier du Candidat"),
        )

    def action_open_visite_medicale_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_visite_medicale",
            _("Visite médicale"),
        )

    def action_open_announcement_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_announcement",
            _("Announcement"),
        )

    def action_open_suivi_collaborateur_popup(self):
        return self._open_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_popup_suivi_collaborateur",
            _("Suivi collaborateur"),
        )

    def action_open_validate_n1_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("validate_n1")

    def action_open_submit_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("submit")

    def action_open_validate_rh_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("validate_rh")

    def action_open_validate_md_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("validate_md")

    def action_open_validate_direction_generale_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("validate_direction_generale")

    def action_open_validate_deliberation_finale_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("validate_deliberation_finale")

    def action_open_validate_periode_essai_n1_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("validate_periode_essai_n1")

    def action_open_offer_accept_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("offer_accept")

    def action_open_offer_refuse_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("offer_refuse")

    def action_open_refuse_wizard(self):
        self.ensure_one()
        return self._open_action_wizard("refuse")

    def action_demander_modification(self):
        for rec in self:
            if rec.state in ("rupture", "archive_stage", "accepte", "refuse"):
                raise AccessError(_("Modification impossible pour les états Rupture, Acceptée et Refusée."))

            allowed = (
                self.env.user == rec.demandeur_id
                or self.env.user == rec.rattachement_hierarchique_id
                or (
                    self.env.user.has_group("ar_recrutement.group_ar_recrutement_manager")
                    and rec.manager_id
                    and rec.manager_id == self.env.user
                )
                or self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh")
                or self.env.user.has_group("ar_recrutement.group_ar_recrutement_md")
            )

            if not allowed:
                raise AccessError(_("Vous n'avez pas le droit de modifier cette demande."))

            rec.write({
                "state": "demandeur",
                "step": "draft",
                "is_rupture_archived": False,
                "is_stage_archived": False,
                "validateur_n1_id": False,
                "validateur_rh_id": False,
                "validateur_md_id": False,
                "date_validation_n1": False,
                "date_validation_rh": False,
                "date_validation_md": False,
            })

            rec.message_post(
                body=_("La demande a été remise à l'état Expression de besoin. Le workflow a été relancé depuis le début.")
            )

    def _check_is_real_rattachement_hierarchique(self):
        self.ensure_one()
        if not self.rattachement_hierarchique_id or self.rattachement_hierarchique_id.id != self.env.user.id:
            raise AccessError(_("Seule la personne renseignée dans 'Rattachement hiérarchique' peut valider cette étape."))

    @api.constrains("type_contrat", "duree_contrat")
    def _check_duree_contrat(self):
        for rec in self:
            if rec.type_contrat in ("cdd", "anapec") and not (rec.duree_contrat or "").strip():
                raise ValidationError(_("Merci de renseigner la durée du contrat (CDD/ANAPEC)."))

    @api.constrains("formation_base", "formation_base_autre")
    def _check_formation_autre(self):
        for rec in self:
            if rec.formation_base == "autre" and not (rec.formation_base_autre or "").strip():
                raise ValidationError(_("Merci de préciser la formation de base (Autre)."))
            
    @api.onchange("formation_base")
    def _onchange_formation_base(self):
        if self.formation_base != "autre":
            self.formation_base_autre = False

    @api.depends("visite_medicale_faite")
    def _compute_visite_medicale_faite_radio(self):
        for rec in self:
            rec.visite_medicale_faite_radio = "oui" if rec.visite_medicale_faite else "non"

    def _inverse_visite_medicale_faite_radio(self):
        for rec in self:
            rec.visite_medicale_faite = rec.visite_medicale_faite_radio == "oui"

    def write(self, vals):
        demandeur_only_fields = {
            "personne_remplacee_id",
            "raison_remplacement",
            "renouvellement_type",
            "renouvellement_duree",
            "changement_contrat",
            "objet_recrutement",
            "stagiaire_sujet",
            "stagiaire_nombre",
            "stagiaire_duree_mois",
            "stagiaire_remuneration",
            "categorie_prof",
            "date_embauche_souhaitee",
            "motif_demande",
            "type_contrat",
            "duree_contrat",
            "recrutement_budget",
            "contenu_poste",
            "profil_annexe",
            "profil_annexe_filename",
            "rattachement_hierarchique_id",
            "nom_tuteur_id",
            "remuneration_avantages",
            "formation_base",
            "formation_base_autre",
            "experience_annees",
            "nombre_personnes",
            "qualites_personnelles",
            "formation_complementaire",
            "consequences_si_refus",
        }
        if demandeur_only_fields.intersection(vals):
            for rec in self:
                if rec.state == "demandeur":
                    rec._check_can_act_as_demandeur()

        rh_only_fields = {
            "ancien_matricule",
            "nouvelle_affectation_matricule",
            "dossier_candidat_line_ids",
            "visite_medicale_faite",
            "deliberation_decision_finale",
            "deliberation_commentaire",
        }
        if rh_only_fields.intersection(vals) and not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner les informations Matricule, Dossier du Candidat et Visite médicale."))

        old = {rec.id: (rec.state, rec.step) for rec in self}

        res = super().write(vals)

        # si state change sans step, on synchronise
        if "state" in vals and "step" not in vals:
            self._sync_step_from_state()

        if "state" in vals or "step" in vals:
            for rec in self:
                old_state, old_step = old.get(rec.id, (False, False))
                new_state, new_step = rec.state, rec.step
                if (old_state, old_step) != (new_state, new_step):
                    rec._post_workflow_trace(old_state, old_step, new_state, new_step)
                    rec._send_on_state_step_change(old_state, old_step, new_state, new_step)

        return res
    
    # Séquence
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            demande_type = vals.get("demande_type") or self.env.context.get("default_demande_type")

            if vals.get("name", "Nouveau") == "Nouveau":
                sequence_number = self.env["ir.sequence"].next_by_code("ar.demande.de.recrutement") or "0000"
                prefix = self._get_demande_prefix(demande_type)
                vals["name"] = f"{prefix}{sequence_number}"

            if demande_type and not vals.get("demande_type"):
                vals["demande_type"] = demande_type

        return super().create(vals_list)

    
    @api.constrains(
        "demande_type",
        "personne_remplacee_id",
        "raison_remplacement",
        "renouvellement_duree",
        "changement_contrat",
        "stagiaire_nombre",
        "stagiaire_duree_mois",
        "stagiaire_remuneration",
        "formation_base",
        "objet_recrutement",
        "stagiaire_line_ids",
    )
    def _check_specific_fields(self):
        for rec in self:
            if rec.demande_type == "remplacement":
                if not rec.personne_remplacee_id or not rec.raison_remplacement:
                    raise ValidationError(_("Remplacement: merci de renseigner la personne remplacée et la raison."))

            if rec.demande_type == "renouvellement":
                if not rec.renouvellement_duree:
                    raise ValidationError(_("Renouvellement: merci de renseigner la durée."))

            if rec.demande_type == "changement_contrat":
                if not rec.changement_contrat:
                    raise ValidationError(_("Changement contrat: merci de sélectionner le type de changement."))

            if rec.demande_type == "demande_stagiaire":
                if not rec.objet_recrutement:
                    raise ValidationError(_("Demande de stagiaire: merci de renseigner l'objet de recrutement."))
                if not rec.stagiaire_nombre or rec.stagiaire_nombre <= 0:
                    raise ValidationError(_("Demande de stagiaire: merci de renseigner un nombre valide."))
                if not rec.stagiaire_duree_mois or rec.stagiaire_duree_mois <= 0:
                    raise ValidationError(_("Demande de stagiaire: merci de renseigner la durée de stage en mois."))
                if not rec.stagiaire_sujet:
                    raise ValidationError(_("Demande de stagiaire: merci de renseigner le sujet."))
                if not rec.stagiaire_remuneration:
                    raise ValidationError(_("Demande de stagiaire: merci de renseigner la rémunération."))
                if not rec.formation_base:
                    raise ValidationError(_("Demande de stagiaire: merci de renseigner la formation de base."))



    def _sync_integration_lines(self):
        Integration = self.env["ar.demande.recrutement.integration"]

        for rec in self:
            candidats_cibles = rec.candidate_ids.filtered(
                lambda c: c.offre_decision == "accepte"
                and c.hiring_date
                and not c.is_refused_line
            )

            existing_by_candidate = {
                line.candidate_id.id: line
                for line in rec.integration_ids.filtered(lambda l: l.candidate_id)
            }

            candidate_ids_to_keep = []

            for cand in candidats_cibles:
                candidate_ids_to_keep.append(cand.id)

                if cand.id not in existing_by_candidate:
                    Integration.create({
                        "demande_id": rec.id,
                        "validation_demande_id": rec.id,
                        "candidate_id": cand.id,
                        "integration_department_id": rec.department_id.id or False,
                        "validation_n1_essai": cand.validation_n1_essai,
                        "validation_rh_essai": cand.validation_rh_essai,
                        "validation_direction_generale": cand.validation_direction_generale,
                    })

            lines_to_remove = rec.integration_ids.filtered(
                lambda l: not l.candidate_id or l.candidate_id.id not in candidate_ids_to_keep
            )
            if lines_to_remove:
                lines_to_remove.unlink()
            rec._cleanup_suivi_duplicate_lines()

    def _cleanup_suivi_duplicate_lines(self):
        for rec in self:
            lines_by_candidate = {}
            for line in rec.integration_ids.filtered(lambda l: l.candidate_id):
                lines_by_candidate.setdefault(line.candidate_id.id, self.env["ar.demande.recrutement.integration"])
                lines_by_candidate[line.candidate_id.id] |= line

            for lines in lines_by_candidate.values():
                if len(lines) <= 1:
                    continue

                sorted_lines = lines.sorted(
                    key=lambda line: (
                        bool(line.integration_line_ids),
                        bool(line.feedback_rh or line.feedback_md),
                        bool(line.validation_n1_essai or line.validation_rh_essai or line.validation_direction_generale or line.validation_deliberation_finale),
                        line.id,
                    ),
                    reverse=True,
                )
                (lines - sorted_lines[:1]).write({"demande_id": False})

    def action_refresh_integration_lines(self):
        for rec in self:
            rec._sync_integration_lines()

    def _get_active_trial_lines(self):
        self.ensure_one()
        return self.validation_integration_ids.filtered(
            lambda l: l.candidate_id
            and not l.candidate_id.is_refused_line
            and not l.is_trial_history
        )

    def _get_default_dossier_candidat_documents(self):
        return [
            "cin",
            "certificat_habitude_physique",
            "diplomes",
            "attestations",
            "certificats_anciennes_experiences",
            "fiche_anthropometrique",
            "extrait_naissance",
            "certificat_residence",
            "photos",
            "acte_mariage",
            "rib",
            "extrait_naissance_enfants",
            "autre",
        ]

    def _ensure_dossier_candidat_lines(self):
        DossierLine = self.env["ar.demande.recrutement.dossier.candidat.line"]
        for rec in self:
            candidates = rec.candidate_ids.filtered(
                lambda c: c.offre_decision == "accepte"
                and c.hiring_date
                and not c.is_refused_line
            )
            if len(candidates) == 1:
                rec.dossier_candidat_line_ids.filtered(lambda line: not line.candidate_id).write({
                    "candidate_id": candidates.id,
                })

            existing_keys = {
                (line.candidate_id.id, line.document_type)
                for line in rec.dossier_candidat_line_ids
                if line.candidate_id and line.document_type
            }
            candidate_ids_to_keep = []
            for candidate in candidates:
                candidate_ids_to_keep.append(candidate.id)
                for document_type in rec._get_default_dossier_candidat_documents():
                    key = (candidate.id, document_type)
                    if key in existing_keys:
                        continue
                    DossierLine.create({
                        "demande_id": rec.id,
                        "candidate_id": candidate.id,
                        "document_type": document_type,
                    })
                    existing_keys.add(key)

            rec.dossier_candidat_line_ids.filtered(
                lambda line: not line.document_file
                and (
                    not line.candidate_id
                    or line.candidate_id.id not in candidate_ids_to_keep
                )
            ).unlink()

    def _raise_missing_fields(self, title, missing_items):
        if missing_items:
            unique_items = list(dict.fromkeys(missing_items))
            raise ValidationError("%s\n%s" % (
                _("Veuillez remplir les champs suivants :"),
                "\n".join("- %s" % item for item in unique_items),
            ))

    # -------------------------
    # Boutons workflow
    # -------------------------
    def action_soumettre(self):
        for rec in self:

            # 1) Création -> N+1
            if rec.state == "demandeur" and rec.step == "draft":
                rec._check_can_act_as_demandeur()
                rec._check_stagiaire_lines(check_document_type=False, check_document_file=False)
                rec.write({"state": "n1", "step": "wait_validation"})
                continue

            # 2) Sélection candidats (Demandeur)
            #    - si toutes les lignes = Refusé => retour à CVthèques
            #    - si au moins une ligne = Approuvé => Entretien
            #    - sinon => blocage tant que toutes les lignes ne sont pas décidées
            if rec.state == "selection_candidats" and rec.step == "demandeur_choose":
                rec._check_can_act_as_demandeur()
                if not rec.candidate_ids:
                    raise ValidationError(_("Aucun candidat trouvé."))

                has_approuve = any(c.demandeur_decision == "approuve" for c in rec.candidate_ids)
                all_refuse = all(c.demandeur_decision == "refuse" for c in rec.candidate_ids)

                if all_refuse:
                    rec.write({"state": "cv_tech", "step": "rh_collect_candidates"})
                    continue

                if has_approuve:
                    rec.write({"state": "entretien", "step": "rh_schedule_interview"})
                    continue

                missing = [
                    _("Avis entretien")
                    for c in rec.candidate_ids
                    if not c.demandeur_decision
                ]
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

            # 3) Entretien technique (Demandeur)
            #    - si toutes les lignes = Non => retour à CVthèques
            #    - si au moins une ligne = Oui => Entretien RH
            #    - sinon => blocage tant que toutes les lignes ne sont pas décidées
            if rec.state == "candidat_retenu" and rec.step == "demandeur_final_choice":
                rec._check_can_act_as_demandeur()
                if not rec.candidate_ids:
                    raise ValidationError(_("Aucun candidat trouvé."))

                all_non = all(c.retenu_final == "non" for c in rec.candidate_ids)

                if all_non:
                    rec.write({"state": "validation_rh", "step": "rh_validate_final"})
                    continue

                missing = [
                    _("Validation demandeur")
                    for c in rec.candidate_ids
                    if not c.retenu_final
                ]
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                retenus = rec.candidate_ids.filtered(
                    lambda c: c.retenu_final == "oui" and not c.is_refused_line
                )
                candidats_sans_fa = retenus.filtered(lambda c: not c.fa_complete)
                if candidats_sans_fa:
                    rec._raise_missing_fields(
                        _("Veuillez complÃ©ter les champs obligatoires suivants :"),
                        [
                            _("FA (%s)") % c.candidate_name
                            for c in candidats_sans_fa
                        ]
                    )

                rec.write({"state": "validation_rh", "step": "rh_validate_final"})
                continue
        
    def _all_candidates_refused_in_selection(self):
        self.ensure_one()
        return (
            bool(self.candidate_ids)
            and all(c.demandeur_decision == "refuse" for c in self.candidate_ids)
        )

    def _all_candidates_non_in_entretien_tech(self):
        self.ensure_one()
        return (
            bool(self.candidate_ids)
            and all(c.retenu_final == "non" for c in self.candidate_ids)
        )

    def _all_candidates_non_in_entretien_rh(self):
        self.ensure_one()
        return (
            bool(self.candidate_ids)
            and all(c.rh_validation == "non" for c in self.candidate_ids)
        )

    
    def _check_stagiaire_lines(self, check_document_type=False, check_document_file=False):
        for rec in self:
            if rec.demande_type != "demande_stagiaire":
                continue

            # Ne contrôler le tableau Documents que lorsqu'on demande
            # explicitement les vérifications de type/fichier
            if check_document_type or check_document_file:
                if not rec.stagiaire_line_ids:
                    raise ValidationError(_("Merci d'ajouter au moins une ligne dans le tableau Documents stagiaire."))

            if check_document_type:
                lignes_sans_type = rec.stagiaire_line_ids.filtered(lambda l: not l.document_type)
                if lignes_sans_type:
                    rec._raise_missing_fields(
                        _("Veuillez renseigner les champs obligatoires suivants :"),
                        [_("Documents stagiaire : Type de document")]
                    )

            if check_document_file:
                lignes_sans_fichier = rec.stagiaire_line_ids.filtered(lambda l: not l.assurance_file)
                if lignes_sans_fichier:
                    rec._raise_missing_fields(
                        _("Veuillez renseigner les champs obligatoires suivants :"),
                        [_("Documents stagiaire : Fichier document")]
                    )

    def _check_is_real_manager(self):
        self.ensure_one()
        if not self.manager_id or self.manager_id.id != self.env.user.id:
            raise AccessError(_("Seul le manager N+1 du demandeur peut valider."))
        
    def action_valider_n1(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_manager"):
                raise AccessError(_("Vous n'etes pas autorise a valider en tant que Manager N+1."))
            if rec.state != "n1":
                raise AccessError(_("Validation N+1 uniquement a l'etat Manager N+1."))
            rec._check_is_real_manager()
            rec.write({
                "state": "rh",
                "step": "wait_validation",
                "validateur_n1_id": self.env.user.id,
                "date_validation_n1": fields.Datetime.now(),
            })

    def action_valider_periode_essai_n1(self):
        for rec in self:
            if rec.state != "periode_essai_n1":
                raise AccessError(_("Validation autorisee uniquement a l'etat Periode d'essai N+1."))
            rec._check_can_act_as_demandeur()

            lignes = rec._get_active_trial_lines()

            if not lignes:
                raise ValidationError(_("Aucun candidat concerne."))

            if lignes.filtered(lambda l: not l.validation_n1_essai):
                raise ValidationError(_("Veuillez renseigner la validation N+1."))

            if lignes.filtered(lambda l: not l.epe_complete):
                raise ValidationError(_("Veuillez completer la fiche EPE pour tous les candidats concernes."))

            rec.write({
                "state": "periode_essai_rh",
                "step": "wait_validation"
            })

    def action_valider_rh(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Vous n'êtes pas autorisé à valider en tant que RH."))

            # 1) Validation RH initiale
            if rec.state == "rh" and rec.step == "wait_validation":
                next_state = "md"
                if rec.demande_type == "demande_stagiaire" and rec.stagiaire_duree_mois <= 3:
                    next_state = "annonce"

                rec.write({
                    "state": next_state,
                    "step": "wait_validation",
                    "validateur_rh_id": self.env.user.id,
                    "date_validation_rh": fields.Datetime.now(),
                })
                continue

            # 2) ANNONCE -> CVthèques
            if rec.state == "annonce" and rec.step == "wait_validation":
                if not rec.annonce_ids:
                    raise ValidationError(_("Veuillez ajouter au moins une ligne d'annonce avant validation."))
                if rec.annonce_ids.filtered(lambda l: not l.annonce_file):
                    rec._raise_missing_fields(
                        _("Veuillez renseigner les champs obligatoires suivants :"),
                        [_("Annonce : Fichier d'annonce")]
                    )
                rec.write({"state": "cv_tech", "step": "rh_collect_candidates"})
                continue

            # 3) Cv-Tech -> Sélection candidats
            if rec.state == "cv_tech" and rec.step == "rh_collect_candidates":
                if not rec.candidate_ids:
                    raise ValidationError(_("Ajoutez au moins un candidat."))
                if rec.candidate_ids.filtered(lambda c: not c.candidate_name or not c.cv_file):
                    missing = []
                    for c in rec.candidate_ids:
                        line_missing = []
                        if not c.candidate_name:
                            line_missing.append(_("Nom du candidat"))
                        if not c.cv_file:
                            line_missing.append(_("CV"))
                        if line_missing:
                            missing.extend(line_missing)
                    rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)
                rec.write({"state": "selection_candidats", "step": "demandeur_choose"})
                continue

            # 4) Entretien -> Candidat retenu
            if rec.state == "entretien" and rec.step == "rh_schedule_interview":
                approuves = rec.candidate_ids.filtered(lambda c: c.demandeur_decision == "approuve")
                if any(not c.interview_datetime for c in approuves):
                    missing = [
                        _("Date & heure entretien")
                        for c in approuves
                        if not c.interview_datetime
                    ]
                    rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)
                    raise ValidationError(_("Veuillez renseigner la date/heure d'entretien pour tous les candidats approuvés."))
                rec.write({"state": "candidat_retenu", "step": "demandeur_final_choice"})
                continue

            # 5) Entretien RH
            #    - si toutes les lignes = Non => retour à CVthèques
            #    - si au moins une ligne = Oui => Offre du Candidat
            #    - sinon => blocage tant que toutes les lignes ne sont pas décidées
            if rec.state == "validation_rh" and rec.step == "rh_validate_final":
                if not rec.candidate_ids:
                    raise ValidationError(_("Aucun candidat trouvé."))

                missing_rh_validation = rec.candidate_ids.filtered(lambda c: not c.rh_validation and not c.is_refused_line)
                if missing_rh_validation:
                    missing = [
                        _("Validation RH")
                        for c in missing_rh_validation
                    ]
                    rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                retenus_rh = rec.candidate_ids.filtered(
                    lambda c: c.rh_validation == "oui"
                )

                for c in retenus_rh:
                    if not c.rhfa_complete:
                        rec._raise_missing_fields(
                            _("Veuillez compléter les champs obligatoires suivants :"),
                            [_("FA RH")]
                        )
                        raise ValidationError(_("Veuillez compléter la FA RH pour le(s) candidat(s) avec Validation RH = Oui."))

                rec.write({"state": "deliberation", "step": "rh_deliberation"})
                continue

            # 6) Délibération -> Offre du candidat
            if rec.state == "deliberation" and rec.step == "rh_deliberation":
                deliberation_lines = rec.candidate_ids.filtered(
                    lambda c: c.demandeur_decision == "approuve"
                )
                if not deliberation_lines:
                    raise ValidationError(_("Aucun candidat approuvé dans Avis entretien."))

                missing_deliberation = deliberation_lines.filtered(lambda c: not c.deliberation_decision)
                if missing_deliberation:
                    rec._raise_missing_fields(
                        _("Veuillez renseigner les champs obligatoires suivants :"),
                        [_("Délibération")]
                    )

                if not any(c.deliberation_decision == "oui" for c in deliberation_lines):
                    rec.write({"state": "cv_tech", "step": "rh_collect_candidates"})
                    continue

                rec.write({"state": "offre_candidat", "step": "rh_offer_candidate"})
                continue

            # 7) Offre du candidat -> Offre en cours
            if rec.state == "offre_candidat" and rec.step == "rh_offer_candidate":
                missing = []
                offer_lines = rec.candidate_ids.filtered(
                    lambda c: c.demandeur_decision == "approuve"
                    and c.deliberation_decision == "oui"
                )
                if not offer_lines:
                    raise ValidationError(_("Aucun candidat avec Délibération = Oui."))

                for line in offer_lines:
                    if not line.offre_candidat_nom:
                        missing.append(_("Offre du Candidat : Nom de l'Offre"))
                    if not line.offre_candidat_file:
                        missing.append(_("Offre du Candidat : Fichier de l'Offre"))
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)
                rec.write({"state": "offre_en_cours", "step": "rh_offer_in_progress"})
                continue

            # 8) Date d'embauche
            if rec.state == "date_embauche" and rec.step == "rh_hiring_date":
                retenus_rh = rec.candidate_ids.filtered(
                    lambda c: c.offre_decision == "accepte"
                    and not c.is_refused_line
                )

                if retenus_rh and any(not c.hiring_date for c in retenus_rh):
                    missing = [
                        _("Date d'embauche")
                        for c in retenus_rh
                        if not c.hiring_date
                    ]
                    rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)
                    raise ValidationError(_(
                        "Veuillez renseigner la date d'embauche uniquement pour le(s) candidat(s) ayant accepté l'offre."
                    ))

                # Contrôle des documents stagiaire
                rec._check_stagiaire_lines(check_document_type=True, check_document_file=True)

                # Workflow stagiaire
                if rec.demande_type == "demande_stagiaire":
                    rec.write({"state": "en_cours_stage", "step": "wait_validation"})
                    continue

                # Workflow selon catégorie professionnelle
                if rec._is_non_stagiaire_standard_flow():
                    rec._sync_integration_lines()

                    if rec.categorie_prof == "ouvrier":
                        rec.write({"state": "affectation", "step": "wait_validation"})
                        continue

                    if rec.categorie_prof == "non_cadre":
                        rec.write({"state": "matricule_a_renseigner", "step": "wait_validation"})
                        continue

                    raise ValidationError(_("Veuillez renseigner la catégorie professionnelle avant validation."))

                # Sécurité fallback
                rec.write({"state": "parcours_integration", "step": "wait_validation"})
                rec._sync_integration_lines()
                continue


            # 8) Suite MOI : Matricule -> Dossier -> Visite médicale -> Announcement -> Parcours
            if rec.state == "affectation" and rec.step == "wait_validation":
                if rec.demande_type == "demande_stagiaire" or rec.categorie_prof != "ouvrier":
                    raise AccessError(_("Cette etape est reservee aux demandes MOD hors stagiaire."))

                retenus_rh = rec.candidate_ids.filtered(
                    lambda c: c.offre_decision == "accepte"
                    and c.hiring_date
                    and not c.is_refused_line
                )
                missing = []
                for candidate in retenus_rh:
                    if not candidate.chef_equipe_id:
                        missing.append(_("Affectation : Chef d'equipe affecte (%s)") % candidate.candidate_name)
                    if not candidate.manager_affecte_id:
                        missing.append(_("Affectation : Manager affecte (%s)") % candidate.candidate_name)
                    if not candidate.superviseur_affecte_id:
                        missing.append(_("Affectation : Superviseur affecte (%s)") % candidate.candidate_name)
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                rec.write({"state": "matricule_a_renseigner", "step": "wait_validation"})
                continue

            if rec.state == "matricule_a_renseigner" and rec.step == "wait_validation":
                if rec.demande_type == "demande_stagiaire" or rec.categorie_prof not in ("ouvrier", "non_cadre"):
                    raise AccessError(_("Cette etape est reservee aux demandes MOD/MOI hors stagiaire."))

                accepted_lines = rec.candidate_ids.filtered(
                    lambda c: c.offre_decision == "accepte"
                    and c.hiring_date
                    and not c.is_refused_line
                )
                missing = []
                if rec.demande_type == "changement_contrat" and rec.type_contrat == "anapec":
                    for candidate in accepted_lines.filtered(lambda c: not c.ancien_matricule):
                        missing.append(_("Date d'embauche & Matricule : Ancien matricule (%s)") % candidate.candidate_name)
                for candidate in accepted_lines.filtered(lambda c: not c.nouvelle_affectation_matricule):
                    missing.append(_("Date d'embauche & Matricule : Matricule à renseigner (%s)") % candidate.candidate_name)
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                if rec.categorie_prof == "ouvrier":
                    rec.write({"state": "feedback_rh", "step": "wait_validation"})
                else:
                    rec.write({"state": "dossier_candidat", "step": "wait_validation"})
                    rec._ensure_dossier_candidat_lines()
                continue

            if rec.state == "dossier_candidat" and rec.step == "wait_validation":
                if rec.demande_type == "demande_stagiaire" or rec.categorie_prof != "non_cadre":
                    raise AccessError(_("Cette etape est reservee aux demandes MOI hors stagiaire."))

                rec._ensure_dossier_candidat_lines()
                missing = []
                candidates = rec.candidate_ids.filtered(
                    lambda c: c.offre_decision == "accepte"
                    and c.hiring_date
                    and not c.is_refused_line
                )
                for candidate in candidates:
                    photos_line = rec.dossier_candidat_line_ids.filtered(
                        lambda l: l.candidate_id == candidate
                        and l.document_type == "photos"
                    )[:1]
                    if not photos_line or not photos_line.document_file:
                        missing.append(_("Dossier du Candidat : Photos (%s)") % candidate.candidate_name)
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                rec.write({"state": "visite_medicale", "step": "wait_validation"})
                continue

            if rec.state == "visite_medicale" and rec.step == "wait_validation":
                if rec.demande_type == "demande_stagiaire" or rec.categorie_prof != "non_cadre":
                    raise AccessError(_("Cette etape est reservee aux demandes MOI hors stagiaire."))

                candidates = rec._get_announcement_candidates()
                if not candidates:
                    raise ValidationError(_("Aucun candidat recruté trouvé pour valider la visite médicale."))
                missing = []
                for candidate in candidates:
                    if not candidate.medical_visit_done:
                        missing.append(_("Visite médicale faite (%s)") % candidate.candidate_name)
                    elif candidate.medical_visit_done != "oui":
                        missing.append(_("Visite médicale faite = Oui (%s)") % candidate.candidate_name)
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                rec.write({"state": "envoie_annonce", "step": "wait_validation"})
                continue

            if rec.state == "envoie_annonce" and rec.step == "wait_validation":
                if rec.demande_type == "demande_stagiaire" or rec.categorie_prof != "non_cadre":
                    raise AccessError(_("Cette etape est reservee aux demandes MOI hors stagiaire."))

                candidates = rec._get_announcement_candidates()
                if not candidates:
                    raise ValidationError(_("Aucun candidat recruté trouvé pour valider l'announcement."))
                missing = []
                for candidate in candidates:
                    if not candidate.announcement_sent:
                        missing.append(_("Announcement envoyé (%s)") % candidate.candidate_name)
                rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                rec._sync_integration_lines()
                rec.write({"state": "parcours_integration", "step": "wait_validation"})
                continue

            if rec.state == "parcours_integration" and rec.step == "wait_validation":
                rec._sync_integration_lines()

                if not rec.integration_ids:
                    raise ValidationError(_("Aucune ligne d'intégration n'a été générée."))

                integrations_invalides = rec.integration_ids.filtered(
                    lambda l: not l.integration_department_id
                )
                if integrations_invalides:
                    missing = [
                        _("Département")
                        for line in integrations_invalides
                    ]
                    rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                for integration in rec.integration_ids:
                    if not integration.integration_line_ids:
                        raise ValidationError(_("Veuillez compléter le formulaire Intégration pour tous les candidats."))

                    lignes_invalides = integration.integration_line_ids.filtered(
                        lambda line: not line.service_accueillant or not line.rubrique or not line.tuteur_id or not line.date_integration
                    )
                    if lignes_invalides:
                        missing = []
                        for line in lignes_invalides:
                            line_missing = []
                            if not line.service_accueillant:
                                line_missing.append(_("Département ou Service accueillant"))
                            if not line.rubrique:
                                line_missing.append(_("Rubrique / Étape"))
                            if not line.tuteur_id:
                                line_missing.append(_("Tuteur"))
                            if not line.date_integration:
                                line_missing.append(_("Date"))
                            missing.extend(line_missing)
                        rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

                rec.write({"state": "feedback_rh", "step": "wait_validation"})
                continue

            # 9) Feedback RH -> Feedback MD
            if rec.state == "feedback_rh" and rec.step == "wait_validation":
                if not rec.integration_ids:
                    raise ValidationError(_("Aucune ligne d'intégration trouvée."))

                if rec.integration_ids.filtered(lambda l: not l.feedback_rh):
                    raise ValidationError(_("Veuillez renseigner le Feedback RH pour tous les candidats."))

                rec.write({"state": "feedback_md", "step": "wait_validation"})
                continue

            # 10) Période d'Essai RH
            if rec.state == "periode_essai_rh" and rec.step == "wait_validation":
                lignes = rec._get_active_trial_lines()

                if not lignes:
                    raise ValidationError(_("Aucun candidat concerné pour la période d'essai RH."))

                if lignes.filtered(lambda l: not l.validation_n1_essai):
                    raise ValidationError(_("Veuillez renseigner 'Validation N+1' pour tous les candidats concernés."))

                if lignes.filtered(lambda l: not l.validation_rh_essai):
                    raise ValidationError(_("Veuillez renseigner 'Validation RH' pour tous les candidats concernés."))

                has_rupture = any(
                    l.validation_n1_essai == "rupture" or l.validation_rh_essai == "rupture"
                    for l in lignes
                )

                if has_rupture:
                    rec.write({"state": "rupture", "step": "done"})
                    continue

                # Si aucune rupture n'est demandée, le flux continue.
                if rec._is_non_stagiaire_standard_flow():
                    if rec.categorie_prof == "ouvrier":
                        rec.write({"state": "accepte", "step": "done"})
                        continue

                    if rec.categorie_prof == "non_cadre":
                        rec.write({"state": "direction_generale", "step": "wait_validation"})
                        continue

                    raise ValidationError(_("Veuillez renseigner la catégorie professionnelle avant validation."))

                # Fallback / autres cas : logique actuelle vers direction générale
                rec.write({"state": "direction_generale", "step": "wait_validation"})
                continue

    def action_offre_acceptee(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Vous n'êtes pas autorisé à valider l'offre en tant que RH."))
            if rec.state != "offre_en_cours" or rec.step != "rh_offer_in_progress":
                raise AccessError(_("Cette action est autorisée uniquement à l'état Offre en Cours."))

            offer_lines = rec.candidate_ids.filtered(
                lambda c: c.demandeur_decision == "approuve"
                and c.deliberation_decision == "oui"
            )
            if not offer_lines:
                raise ValidationError(_("Aucun candidat avec Délibération = Oui."))
            if offer_lines.filtered(lambda c: not c.offre_decision):
                rec._raise_missing_fields(
                    _("Veuillez renseigner les champs obligatoires suivants :"),
                    [_("Décision offre")]
                )

            if not any(c.offre_decision == "accepte" for c in offer_lines):
                rec.write({"state": "cv_tech", "step": "rh_collect_candidates"})
                continue

            rec.write({"state": "date_embauche", "step": "rh_hiring_date"})

    def action_offre_refusee(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Vous n'êtes pas autorisé à refuser l'offre en tant que RH."))
            if rec.state != "offre_en_cours" or rec.step != "rh_offer_in_progress":
                raise AccessError(_("Cette action est autorisée uniquement à l'état Offre en Cours."))
            rec.write({"state": "refuse", "step": "done"})

    def action_valider_md(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_md"):
                raise AccessError(_("Vous n'êtes pas autorisé à valider en tant que MD."))

            # MD -> Annonce pour tous les types, y compris stagiaire
            if rec.state == "md":
                rec.write({
                    "state": "annonce",
                    "step": "wait_validation",
                    "validateur_md_id": self.env.user.id,
                    "date_validation_md": fields.Datetime.now(),
                })
                continue

            # Feedback MD -> Période d'essai N+1 (uniquement hors stagiaire)
            if rec.state == "feedback_md":
                if rec.demande_type == "demande_stagiaire":
                    raise AccessError(_("Cette étape n'est pas applicable à la demande de stagiaire."))

                if not rec.integration_ids:
                    raise ValidationError(_("Aucune ligne d'intégration trouvée."))

                if rec.integration_ids.filtered(lambda l: not l.feedback_md):
                    raise ValidationError(_("Veuillez renseigner le Feedback MD pour tous les candidats."))

                rec.write({"state": "periode_essai_n1", "step": "wait_validation"})
                continue

            raise AccessError(_("Validation MD autorisée uniquement aux états MD ou Feedback MD."))

    def action_refuser(self):
        for rec in self:
            if rec.state not in (
                "n1", "rh", "md", "annonce", "cv_tech", "selection_candidats",
                "entretien", "candidat_retenu", "validation_rh", "deliberation", "date_embauche", "affectation",
                "en_cours_stage", "matricule_a_renseigner", "dossier_candidat",
                "visite_medicale", "envoie_annonce", "parcours_integration", "feedback_rh", "feedback_md",
            "periode_essai_n1", "periode_essai_rh", "direction_generale", "deliberation_finale"
            ):
                raise AccessError(_("Refus non autorisé dans cet état."))

            if rec.state == "n1":
                if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_manager"):
                    raise AccessError(_("Vous n'êtes pas autorisé à refuser en tant que Manager N+1."))
                rec._check_is_real_manager()

            elif rec.state == "periode_essai_n1":
                if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_manager"):
                    raise AccessError(_("Vous n'êtes pas autorisé à refuser en tant que Manager N+1."))
                rec._check_is_real_rattachement_hierarchique()

            elif rec.state in ("rh", "annonce", "cv_tech", "selection_candidats", "entretien", "candidat_retenu",
                                "validation_rh", "deliberation", "date_embauche", "affectation", "en_cours_stage", "matricule_a_renseigner",
                                "dossier_candidat", "visite_medicale", "envoie_annonce", "parcours_integration",
                                "feedback_rh", "periode_essai_rh", "deliberation_finale"):
                if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                    raise AccessError(_("Vous n'êtes pas autorisé à refuser en tant que RH."))

            elif rec.state in ("md", "feedback_md", "direction_generale"):
                if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_md"):
                    raise AccessError(_("Vous n'êtes pas autorisé à refuser en tant que MD."))

            rec.write({"state": "refuse", "step": "done"})

    
    def action_valider_direction_generale(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_md"):
                raise AccessError(_("Vous n'êtes pas autorisé à valider en tant que Directeur (MD)."))

            if rec.state != "direction_generale":
                raise AccessError(_("Validation uniquement à l'état Direction générale."))

            lignes = rec._get_active_trial_lines()

            if not lignes:
                raise ValidationError(_("Aucun candidat concerné pour la validation Direction générale."))

            if lignes.filtered(lambda l: not l.validation_direction_generale):
                raise ValidationError(_("Veuillez renseigner 'Direction générale' pour tous les candidats concernés."))

            has_rupture = any(
                l.validation_direction_generale == "rupture"
                for l in lignes
            )

            if has_rupture:
                rec.write({"state": "rupture", "step": "done"})
            else:
                rec.write({"state": "deliberation_finale", "step": "wait_validation"})

    def action_valider_deliberation_finale(self):
        for rec in self:
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Vous n'êtes pas autorisé à valider la délibération finale en tant que RH."))

            if rec.state != "deliberation_finale":
                raise AccessError(_("Validation uniquement à l'état Délibération finale."))

            lignes = rec._get_active_trial_lines()

            if not lignes:
                raise ValidationError(_("Aucun candidat concerné pour la délibération finale."))

            if lignes.filtered(lambda l: not l.validation_deliberation_finale):
                raise ValidationError(_("Veuillez renseigner 'Délibération' pour tous les candidats concernés."))

            has_rupture = any(
                l.validation_deliberation_finale == "rupture"
                for l in lignes
            )
            reconduction_lines = lignes.filtered(
                lambda l: l.validation_deliberation_finale == "reconduction"
            )

            if has_rupture:
                rec.write({"state": "rupture", "step": "done"})
            elif reconduction_lines:
                Integration = self.env["ar.demande.recrutement.integration"]
                for line in reconduction_lines:
                    Integration.create({
                        "validation_demande_id": rec.id,
                        "candidate_id": line.candidate_id.id,
                        "integration_department_id": line.integration_department_id.id or rec.department_id.id or False,
                    })
                rec._cleanup_suivi_duplicate_lines()
                rec.write({"state": "periode_essai_n1", "step": "wait_validation"})
            else:
                rec.write({"state": "accepte", "step": "done"})



class ARDemandeRecrutementStagiaireLine(models.Model):
    _name = "ar.demande.recrutement.stagiaire.line"
    _description = "Ligne Sujet / Assurance Stagiaire"
    _order = "id asc"

    demande_id = fields.Many2one(
        "ar.demande.de.recrutement",
        string="Demande",
        required=True,
        ondelete="cascade"
    )

    document_type = fields.Selection([
        ("assurance", "Assurance"),
        ("convention_stage", "Convention de stage"),
        ("cin", "CIN"),
        ("photo", "Photo"),
        ("autre", "Autre"),
    ], string="Type de document", tracking=True)

    assurance_file = fields.Binary(
        string="Assurance",
        attachment=True,
        tracking=True
    )

    assurance_filename = fields.Char(
        string="Nom du fichier Assurance",
        tracking=True
    )

    demande_state = fields.Selection(
        related="demande_id.state",
        string="État de la demande",
        store=True,
        readonly=True
    )

    demande_type = fields.Selection(
        related="demande_id.demande_type",
        string="Type de demande",
        store=True,
        readonly=True
    )

    stagiaire_duree_mois = fields.Integer(
        related="demande_id.stagiaire_duree_mois",
        string="Durée de stage",
        store=True,
        readonly=True
    )

    current_user_is_rh = fields.Boolean(
        related="demande_id.current_user_is_rh",
        string="Utilisateur RH",
        store=False,
        readonly=True,
    )

    def _check_rh_can_edit(self):
        if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner les documents stagiaire."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_rh_can_edit()
        return super().create(vals_list)

    def write(self, vals):
        if {"document_type", "assurance_file", "assurance_filename"}.intersection(vals):
            self._check_rh_can_edit()
        return super().write(vals)

    def unlink(self):
        self._check_rh_can_edit()
        return super().unlink()

    @api.constrains("document_type", "assurance_file", "demande_state", "demande_type", "stagiaire_duree_mois")
    def _check_document_required_date_embauche(self):
        for rec in self:
            if rec.demande_type != "demande_stagiaire":
                continue

            if rec.demande_state == "date_embauche":
                if not rec.document_type:
                    raise ValidationError(_("Le type de document est obligatoire à l'état Date d'embauche."))
                if not rec.assurance_file:
                    raise ValidationError(_("Le fichier document est obligatoire à l'état Date d'embauche."))


class ARDemandeRecrutementCandidate(models.Model):
    _name = "ar.demande.recrutement.candidate"
    _description = "Candidats - Demande Recrutement"
    _order = "id desc"

    def init(self):
        super().init()
        # Convert legacy Oui/Non values to the new trial-period decisions.
        self.env.cr.execute("""
            UPDATE ar_demande_recrutement_candidate
               SET validation_n1_essai = CASE validation_n1_essai
                   WHEN 'oui' THEN 'confirmation'
                   WHEN 'non' THEN 'rupture'
                   ELSE validation_n1_essai
               END,
               validation_rh_essai = CASE validation_rh_essai
                   WHEN 'oui' THEN 'confirmation'
                   WHEN 'non' THEN 'rupture'
                   ELSE validation_rh_essai
               END
             WHERE validation_n1_essai IN ('oui', 'non')
                OR validation_rh_essai IN ('oui', 'non')
        """)
        self.env.cr.execute("""
            UPDATE ar_demande_recrutement_candidate
               SET validation_direction_generale = CASE validation_direction_generale
                   WHEN 'oui' THEN 'confirmation'
                   WHEN 'non' THEN 'rupture'
                   ELSE validation_direction_generale
               END
             WHERE validation_direction_generale IN ('oui', 'non')
        """)

    @api.depends("demande_id.dossier_candidat_line_ids.candidate_id", "demande_id.dossier_candidat_line_ids.document_type", "demande_id.dossier_candidat_line_ids.document_file")
    def _compute_announcement_photo_ok(self):
        for rec in self:
            rec.announcement_photo_ok = bool(rec.demande_id.dossier_candidat_line_ids.filtered(
                lambda line: line.candidate_id == rec
                and line.document_type == "photos"
                and line.document_file
            ))

    demande_id = fields.Many2one("ar.demande.de.recrutement", required=True, ondelete="cascade")

    candidate_name = fields.Char(string="Nom du candidat", required=True, Tracking=True)
    announcement_civility = fields.Selection(
        [
            ("m", "M."),
            ("mme", "Mme"),
        ],
        string="Civilité",
        tracking=True,
    )
    announcement_photo_ok = fields.Boolean(
        string="Photo",
        compute="_compute_announcement_photo_ok",
        store=False,
    )
    announcement_sent = fields.Boolean(string="Announcement envoyé", tracking=True)
    announcement_sent_date = fields.Date(string="Date d'envoi announcement", tracking=True)
    medical_visit_done = fields.Selection(
        [("oui", "Oui"), ("non", "Non")],
        string="Visite médicale faite",
        tracking=True,
    )
    medical_visit_date = fields.Date(string="Date visite médicale", tracking=True)
    cv_file = fields.Binary(string="CV", attachment=True, Tracking=True)
    cv_filename = fields.Char(string="Nom du CV", Tracking=True)

    demandeur_decision = fields.Selection([
        ("approuve", "Approuvé"),
        ("refuse", "Refusé"),
        ("pending", "En attente"),
    ], default="pending", string="Décision demandeur", Tracking=True)

    interview_datetime = fields.Datetime(string="Date & heure entretien", Tracking=True)

    retenu_final = fields.Selection(
        [("oui", "Oui"), ("non", "Non")],
        string="Retenu final",
        default="non",
        tracking=True,
    )

    stage_end_date = fields.Date(
        string="Fin de stage théorique",
        compute="_compute_stage_end_date",
        store=True,
        tracking=True
    )

    stage_in_progress = fields.Boolean(
        string="En cours de stage",
        default=False,
        tracking=True
    )

    can_edit_stage_in_progress = fields.Boolean(
        string="Peut modifier En cours de stage",
        compute="_compute_can_edit_stage_in_progress",
        store=False
    )

    hiring_date = fields.Date(string="Date d'embauche", Tracking=True)
    chef_equipe_id = fields.Many2one("res.users", string="Chef d'equipe affecte", tracking=True)
    manager_affecte_id = fields.Many2one("res.users", string="Manager affecte", tracking=True)
    superviseur_affecte_id = fields.Many2one("res.users", string="Superviseur affecte", tracking=True)
    ancien_matricule = fields.Char(string="Ancien Matricule", tracking=True)
    nouvelle_affectation_matricule = fields.Char(string="Matricule à renseigner", tracking=True)
    demande_categorie_prof = fields.Selection(
        related="demande_id.categorie_prof",
        string="Categorie professionnelle",
        store=False,
    )

    is_refused_line = fields.Boolean(
        string="Ligne refusée (UI)",
        compute="_compute_is_refused_line",
        store=False,
        Tracking=True
    )

    rh_validation = fields.Selection(
        [("oui", "Oui"), ("non", "Non")],
        string="Validation RH",
        default="non",
        tracking=True,
    )

    deliberation_decision = fields.Selection(
        [("oui", "Oui"), ("non", "Non")],
        string="Délibération",
        tracking=True,
    )
    offre_candidat_nom = fields.Char(string="Nom de l'Offre", tracking=True)
    offre_candidat_file = fields.Binary(string="Fichier de l'Offre", attachment=True)
    offre_candidat_filename = fields.Char(string="Nom du fichier de l'Offre")
    offre_decision = fields.Selection(
        [("accepte", "Acceptée"), ("refuse", "Refusée")],
        string="Décision offre",
        tracking=True,
    )

    candidate_dossier_line_ids = fields.One2many(
        "ar.demande.recrutement.dossier.candidat.line",
        "candidate_id",
        string="Dossier du Candidat",
    )

    candidate_integration_ids = fields.One2many(
        "ar.demande.recrutement.integration",
        "candidate_id",
        string="Suivi collaborateur",
    )

    candidate_validation_integration_ids = fields.One2many(
        "ar.demande.recrutement.integration",
        "candidate_id",
        string="Validation periode d'essai",
    )

    PERIODE_ESSAI_DECISION = [
        ("confirmation", "Confirmation"),
        ("reconduction", "Reconduction"),
        ("rupture", "Rupture du contrat"),
    ]

    validation_n1_essai = fields.Selection(
        PERIODE_ESSAI_DECISION,
        string="PE N+1",
        tracking=True,
    )

    validation_rh_essai = fields.Selection(
        PERIODE_ESSAI_DECISION,
        string="PE RH",
        tracking=True,
    )

    validation_direction_generale = fields.Selection(
        PERIODE_ESSAI_DECISION,
        string="Direction générale",
        tracking=True,
    )

    EVAL_LEVELS = [
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
    ]

    # =========================
    # EPE
    # =========================
    EPE_SCORE = [
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
    ]

    EPE_DECISION = [
        ("confirmation", "Confirmation"),
        ("reconduction", "Reconduction"),
        ("rupture", "Rupture du contrat"),
    ]

    EPE_LEGENDE = [
        ("pas_satisfait", "Pas satisfait"),
        ("a_ameliorer", "à améliorer"),
        ("satisfait", "Satisfait"),
        ("tres_satisfait", "Très satisfait"),
    ]

    # 1. Identification du salarié
    epe_nom_prenom = fields.Char(string="Nom & Prénom", tracking=True)
    epe_poste = fields.Char(string="Poste", tracking=True)
    epe_date_entree_fonction = fields.Date(string="Date d'entrée en fonction", tracking=True)

    epe_affectation_id = fields.Many2one(
        "hr.department",
        string="Affectation",
        compute="_compute_epe_defaults",
        store=False,
        readonly=True,
        tracking=True,
    )

    epe_evaluateur_id = fields.Many2one(
        "res.users",
        string="Evaluateur",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    epe_date_evaluation = fields.Date(string="Date d'évaluation", tracking=True)

    epe_points_forts = fields.Text(string="Points Forts", tracking=True)
    epe_points_ameliorer = fields.Text(string="Points à améliorer", tracking=True)

    # 2. Missions / réalisations
    epe_missions_realisation = fields.Text(
        string="Principales missions et réalisations accomplies durant la période de probation",
        tracking=True
    )

    # 3. Critères d'appréciation
    epe_atteinte_resultats = fields.Selection(EPE_SCORE, string="Atteinte des résultats/objectifs", tracking=True)
    epe_potentiel_developpement = fields.Selection(EPE_SCORE, string="Potentiel pour le développement", tracking=True)
    epe_maitrise_technique = fields.Selection(EPE_SCORE, string="Maitrise technique", tracking=True)
    epe_capacite_adaptation = fields.Selection(EPE_SCORE, string="Capacité d'adaptation", tracking=True)
    epe_engagement_dynamisme = fields.Selection(EPE_SCORE, string="Engagement et dynamisme", tracking=True)
    epe_autonomie_initiative = fields.Selection(EPE_SCORE, string="Autonomie et prise d'initiative", tracking=True)
    epe_commentaire = fields.Text(string="Commentaire", tracking=True)

    # 4. Autres remarques
    epe_autres_remarques = fields.Text(string="Autres Remarques", tracking=True)

    # 5. Décision finale
    epe_decision = fields.Selection(EPE_DECISION, string="Décision", tracking=True)
    epe_legende = fields.Selection(EPE_LEGENDE, string="Légende", tracking=True)

    epe_complete = fields.Boolean(
        string="EPE complétée",
        compute="_compute_epe_complete",
        store=False,
        tracking=True
    )

    # =========================
    # FA
    # =========================
    fa_interview_realisee_par = fields.Many2one(
        "res.users",
        string="Entretien réalisé par",
        default=lambda self: self.env.user,
        readonly=True, tracking=True
    )
    fa_date_entretien = fields.Date(string="Date d’entretien", tracking=True)
    fa_presentation_generale = fields.Selection(EVAL_LEVELS, string="Présentation générale", tracking=True)

    # SAVOIR
    fa_formation_initiale = fields.Selection(EVAL_LEVELS, string="Formation initiale", tracking=True)
    fa_formation_complementaire_eval = fields.Selection(EVAL_LEVELS, string="Formation complémentaire", tracking=True)

    # SAVOIR-FAIRE
    fa_experiences_professionnelles = fields.Selection(EVAL_LEVELS, string="Expériences professionnelles / Compétences métiers", tracking=True)
    fa_communication_orale = fields.Selection(EVAL_LEVELS, string="Communication orale", tracking=True)
    fa_ecoute = fields.Selection(EVAL_LEVELS, string="Ecoute", tracking=True)
    fa_negociation_persuasion = fields.Selection(EVAL_LEVELS, string="Capacité de négociation et persuasion", tracking=True)
    fa_esprit_equipe_leadership = fields.Selection(EVAL_LEVELS, string="Esprit d’équipe / Esprit de leadership", tracking=True)

    # SAVOIR-ETRE
    fa_autonomie = fields.Selection(EVAL_LEVELS, string="Autonomie", tracking=True)
    fa_dynamisme = fields.Selection(EVAL_LEVELS, string="Dynamisme", tracking=True)
    fa_reactivite = fields.Selection(EVAL_LEVELS, string="Réactivité", tracking=True)
    fa_engagement = fields.Selection(EVAL_LEVELS, string="Engagement", tracking=True)
    fa_rigueur = fields.Selection(EVAL_LEVELS, string="Rigueur", tracking=True)

    fa_actuellement_en_poste = fields.Selection([
        ("oui", "Oui"),
        ("non", "Non"),
    ], string="Actuellement en poste", tracking=True)

    fa_fonction_actuelle = fields.Char(string="Fonction actuelle", tracking=True)
    fa_entreprise_actuelle = fields.Char(string="Entreprise actuelle", tracking=True)
    fa_salaire_actuel = fields.Char(string="Salaire actuel", tracking=True)
    fa_preavis = fields.Char(string="Préavis", tracking=True)

    fa_appreciations_generales = fields.Text(string="Appréciations et motivations générales", tracking=True)

    fa_complete = fields.Boolean(
        string="FA complétée",
        compute="_compute_fa_complete",
        store=False, tracking=True
    )

    fa_pretentions_salariales_num = fields.Float(string="Prétentions salariales", tracking=True)
    rhfa_pretentions_salariales_num = fields.Float(string="Prétentions salariales", tracking=True)
    
    # =========================
    # FA RH
    # =========================
    rhfa_interview_realisee_par = fields.Many2one(
        "res.users",
        string="Entretien réalisé par",
        default=lambda self: self.env.user,
        readonly=True, tracking=True
    )
    rhfa_date_entretien = fields.Date(string="Date d’entretien", tracking=True)
    rhfa_presentation_generale = fields.Selection(EVAL_LEVELS, string="Présentation générale", tracking=True)

    # SAVOIR
    rhfa_formation_initiale = fields.Selection(EVAL_LEVELS, string="Formation initiale", tracking=True)
    rhfa_formation_complementaire_eval = fields.Selection(EVAL_LEVELS, string="Formation complémentaire", tracking=True)

    # SAVOIR-FAIRE
    rhfa_experiences_professionnelles = fields.Selection(EVAL_LEVELS, string="Expériences professionnelles / Compétences métiers", tracking=True)
    rhfa_communication_orale = fields.Selection(EVAL_LEVELS, string="Communication orale", tracking=True)
    rhfa_ecoute = fields.Selection(EVAL_LEVELS, string="Ecoute", tracking=True)
    rhfa_negociation_persuasion = fields.Selection(EVAL_LEVELS, string="Capacité de négociation et persuasion", tracking=True)
    rhfa_esprit_equipe_leadership = fields.Selection(EVAL_LEVELS, string="Esprit d’équipe / Esprit de leadership", tracking=True)

    # SAVOIR-ETRE
    rhfa_autonomie = fields.Selection(EVAL_LEVELS, string="Autonomie", tracking=True)
    rhfa_dynamisme = fields.Selection(EVAL_LEVELS, string="Dynamisme", tracking=True)
    rhfa_reactivite = fields.Selection(EVAL_LEVELS, string="Réactivité", tracking=True)
    rhfa_engagement = fields.Selection(EVAL_LEVELS, string="Engagement", tracking=True)
    rhfa_rigueur = fields.Selection(EVAL_LEVELS, string="Rigueur", tracking=True)

    rhfa_actuellement_en_poste = fields.Selection([
        ("oui", "Oui"),
        ("non", "Non"),
    ], string="Actuellement en poste", tracking=True)

    rhfa_fonction_actuelle = fields.Char(string="Fonction actuelle", tracking=True)
    rhfa_entreprise_actuelle = fields.Char(string="Entreprise actuelle", tracking=True)
    rhfa_salaire_actuel = fields.Char(string="Salaire actuel", tracking=True)
    rhfa_preavis = fields.Char(string="Préavis", tracking=True)

    rhfa_appreciations_generales = fields.Text(string="Appréciations et motivations générales", tracking=True)

    rhfa_complete = fields.Boolean(
        string="FA RH complétée",
        compute="_compute_rhfa_complete",
        store=False, tracking=True
    )

    parent_state = fields.Selection(
        related="demande_id.state",
        string="Etat parent",
        store=False,
        readonly=True, tracking=True
    )

    parent_step = fields.Selection(
        related="demande_id.step",
        string="Etape parent",
        store=False,
        readonly=True, tracking=True
    )

    parent_user_can_act_as_demandeur = fields.Boolean(
        related="demande_id.current_user_can_act_as_demandeur",
        string="Peut agir comme demandeur",
        store=False,
        readonly=True,
    )

    parent_user_is_rh = fields.Boolean(
        related="demande_id.current_user_is_rh",
        string="Utilisateur RH",
        store=False,
        readonly=True,
    )

    parent_user_is_manager = fields.Boolean(
        string="Utilisateur manager",
        compute="_compute_parent_user_roles",
        store=False,
    )

    parent_user_is_md = fields.Boolean(
        string="Utilisateur MD",
        compute="_compute_parent_user_roles",
        store=False,
    )

    fa_note_globale = fields.Float(
        string="Note globale",
        compute="_compute_fa_note_globale",
        store=False,
        digits=(16, 2), tracking=True
    )

    rhfa_note_globale = fields.Float(
        string="Note globale",
        compute="_compute_rhfa_note_globale",
        store=False,
        digits=(16, 2), tracking=True
    )

    demande_type = fields.Selection(
        related="demande_id.demande_type",
        string="Type de demande",
        store=False,
        readonly=True
    )

    type_contrat = fields.Selection(
        related="demande_id.type_contrat",
        string="Type de contrat",
        store=False,
        readonly=True
    )

    stagiaire_remuneration = fields.Selection(
        related="demande_id.stagiaire_remuneration",
        string="Rémunération stagiaire",
        store=False,
        readonly=True
    )

    @api.depends("stage_end_date", "demande_id.demande_type")
    def _compute_can_edit_stage_in_progress(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.can_edit_stage_in_progress = bool(
                rec.demande_id.demande_type == "demande_stagiaire"
                and rec.stage_end_date
                and today > rec.stage_end_date
            )

    @api.depends_context("uid")
    def _compute_parent_user_roles(self):
        is_manager = self.env.user.has_group("ar_recrutement.group_ar_recrutement_manager")
        is_md = self.env.user.has_group("ar_recrutement.group_ar_recrutement_md")
        for rec in self:
            rec.parent_user_is_manager = is_manager
            rec.parent_user_is_md = is_md

    @api.constrains("stage_in_progress", "stage_end_date", "demande_id.demande_type")
    def _check_stage_in_progress_manual_update(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.demande_id.demande_type != "demande_stagiaire":
                continue

            if rec.stage_end_date and today <= rec.stage_end_date:
                # avant la fin théorique, la case doit rester cochée automatiquement
                if rec.stage_in_progress is False:
                    raise ValidationError(_("La case 'En cours de stage' ne peut être décochée qu'après la fin théorique du stage."))


    @api.depends(
        "hiring_date",
        "demande_id.stagiaire_duree_mois",
        "demande_id.demande_type",
        "retenu_final",
        "rh_validation",
    )
    def _compute_stage_end_date(self):
        today = fields.Date.context_today(self)

        for rec in self:
            rec.stage_end_date = False

            if rec.demande_id.demande_type != "demande_stagiaire":
                rec.stage_in_progress = False
                continue

            if rec.retenu_final != "oui" or rec.rh_validation != "oui":
                rec.stage_in_progress = False
                continue

            if not rec.hiring_date or not rec.demande_id.stagiaire_duree_mois:
                rec.stage_in_progress = False
                continue

            start_date = rec.hiring_date
            end_date = start_date + relativedelta(months=rec.demande_id.stagiaire_duree_mois)
            rec.stage_end_date = end_date

            # Cochage automatique tant que la date théorique n'est pas dépassée
            if start_date <= today <= end_date:
                rec.stage_in_progress = True

    @api.depends("demande_id.department_id")
    def _compute_epe_defaults(self):
        for rec in self:
            rec.epe_affectation_id = rec.demande_id.department_id or False

    @api.onchange("candidate_name")
    def _onchange_candidate_name_set_epe_nom_prenom(self):
        for rec in self:
            if not rec.epe_nom_prenom:
                rec.epe_nom_prenom = rec.candidate_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("epe_nom_prenom") and vals.get("candidate_name"):
                vals["epe_nom_prenom"] = vals["candidate_name"]
        return super().create(vals_list)

    def write(self, vals):
        demandeur_fields = {"demandeur_decision", "retenu_final"}
        if demandeur_fields.intersection(vals):
            for rec in self:
                if rec.demande_id and rec.demande_id.step in ("demandeur_choose", "demandeur_final_choice"):
                    rec.demande_id._check_can_act_as_demandeur()
        fa_fields = {
            "fa_date_entretien",
            "fa_presentation_generale",
            "fa_formation_initiale",
            "fa_formation_complementaire_eval",
            "fa_experiences_professionnelles",
            "fa_communication_orale",
            "fa_ecoute",
            "fa_negociation_persuasion",
            "fa_esprit_equipe_leadership",
            "fa_autonomie",
            "fa_dynamisme",
            "fa_reactivite",
            "fa_engagement",
            "fa_rigueur",
            "fa_actuellement_en_poste",
            "fa_fonction_actuelle",
            "fa_entreprise_actuelle",
            "fa_salaire_actuel",
            "fa_preavis",
            "fa_pretentions_salariales_num",
            "fa_appreciations_generales",
        }
        if fa_fields.intersection(vals):
            for rec in self:
                if not rec.demande_id or rec.demande_id.step != "demandeur_final_choice":
                    raise AccessError(_("La FA est modifiable uniquement à l'étape Validation demandeur."))
                rec.demande_id._check_can_act_as_demandeur()
        rhfa_fields = {
            "rhfa_date_entretien",
            "rhfa_presentation_generale",
            "rhfa_formation_initiale",
            "rhfa_formation_complementaire_eval",
            "rhfa_experiences_professionnelles",
            "rhfa_communication_orale",
            "rhfa_ecoute",
            "rhfa_negociation_persuasion",
            "rhfa_esprit_equipe_leadership",
            "rhfa_autonomie",
            "rhfa_dynamisme",
            "rhfa_reactivite",
            "rhfa_engagement",
            "rhfa_rigueur",
            "rhfa_actuellement_en_poste",
            "rhfa_fonction_actuelle",
            "rhfa_entreprise_actuelle",
            "rhfa_salaire_actuel",
            "rhfa_preavis",
            "rhfa_pretentions_salariales_num",
            "rhfa_appreciations_generales",
        }
        if rhfa_fields.intersection(vals):
            if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
                raise AccessError(_("Seul le groupe RH peut renseigner la FA RH."))
            for rec in self:
                if not rec.demande_id or rec.demande_id.step != "rh_validate_final":
                    raise AccessError(_("La FA RH est modifiable uniquement à l'étape Validation RH."))
        epe_fields = {
            "epe_poste",
            "epe_date_entree_fonction",
            "epe_affectation_id",
            "epe_evaluateur_id",
            "epe_date_evaluation",
            "epe_points_forts",
            "epe_points_ameliorer",
            "epe_missions_realisation",
            "epe_atteinte_resultats",
            "epe_potentiel_developpement",
            "epe_maitrise_technique",
            "epe_capacite_adaptation",
            "epe_engagement_dynamisme",
            "epe_autonomie_initiative",
            "epe_commentaire",
        }
        if epe_fields.intersection(vals):
            for rec in self:
                if not rec.demande_id or rec.demande_id.state != "periode_essai_n1":
                    raise AccessError(_("L'EPE est modifiable uniquement Ã  l'Ã©tape PÃ©riode d'essai N+1."))
                rec.demande_id._check_can_act_as_demandeur()
        rh_fields = {
            "candidate_name",
            "cv_file",
            "cv_filename",
            "interview_datetime",
            "rh_validation",
            "hiring_date",
            "chef_equipe_id",
            "manager_affecte_id",
            "superviseur_affecte_id",
            "ancien_matricule",
            "nouvelle_affectation_matricule",
            "offre_candidat_nom",
            "offre_candidat_file",
            "offre_candidat_filename",
            "offre_decision",
            "medical_visit_done",
            "medical_visit_date",
            "announcement_civility",
        }
        if rh_fields.intersection(vals):
            is_rh = self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh")
            if not is_rh:
                raise AccessError(_("Seul le groupe RH peut renseigner ces informations."))
        if {"chef_equipe_id", "manager_affecte_id", "superviseur_affecte_id"}.intersection(vals):
            for rec in self:
                if not rec.demande_id or rec.demande_id.state != "affectation" or rec.demande_id.step != "wait_validation":
                    raise AccessError(_("Les champs d'affectation sont modifiables uniquement a l'etape Affectation."))
        return super().write(vals)

    @api.depends(
        "candidate_name",
        "demande_id.objet_recrutement",
        "demande_id.date_embauche_effective",
        "epe_evaluateur_id",
        "epe_date_evaluation",
        "epe_points_forts",
        "epe_points_ameliorer",
        "epe_missions_realisation",
        "epe_atteinte_resultats",
        "epe_potentiel_developpement",
        "epe_maitrise_technique",
        "epe_capacite_adaptation",
        "epe_engagement_dynamisme",
        "epe_autonomie_initiative",
        "epe_commentaire",
    )

    def _compute_epe_complete(self):
        for rec in self:
            rec.epe_complete = all([
            rec.epe_nom_prenom,
            rec.epe_poste,
            rec.epe_date_entree_fonction,
            rec.epe_affectation_id,
            rec.epe_evaluateur_id,
            rec.epe_date_evaluation,
            rec.epe_points_forts,
            rec.epe_points_ameliorer,
            rec.epe_missions_realisation,
            rec.epe_atteinte_resultats,
            rec.epe_potentiel_developpement,
            rec.epe_maitrise_technique,
            rec.epe_capacite_adaptation,
            rec.epe_engagement_dynamisme,
            rec.epe_autonomie_initiative,
            rec.epe_commentaire,
        ])


    def action_open_epe(self):
        self.ensure_one()
        if not self.epe_nom_prenom and self.candidate_name:
            self.with_context(skip_epe_required_check=True).write({
                "epe_nom_prenom": self.candidate_name,
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("EPE"),
            "res_model": "ar.demande.recrutement.candidate",
            "view_mode": "form",
            "view_id": self.env.ref("ar_recrutement.view_ar_demande_recrutement_candidate_epe_form").id,
            "res_id": self.id,
            "target": "new",
            "context": {
                "default_epe_nom_prenom": self.epe_nom_prenom or self.candidate_name,
                "default_epe_poste": self.epe_poste or self.demande_id.objet_recrutement,
                "default_epe_date_entree_fonction": self.epe_date_entree_fonction or self.hiring_date or self.demande_id.date_embauche_effective,
                "default_epe_evaluateur_id": self.env.user.id,
            },
        }


    def action_download_epe(self):
        self.ensure_one()
        return self.env.ref("ar_recrutement.action_report_candidate_epe").report_action(self)


    def _raise_candidate_missing_fields(self, title, missing_items):
        if missing_items:
            unique_items = list(dict.fromkeys(missing_items))
            raise ValidationError("%s\n%s" % (
                _("Veuillez remplir les champs suivants :"),
                "\n".join("- %s" % item for item in unique_items)
            ))

    def _get_missing_epe_fields(self):
        self.ensure_one()
        checks = [
            ("epe_nom_prenom", _("Nom & Prénom")),
            ("epe_poste", _("Poste")),
            ("epe_date_entree_fonction", _("Date d'entrée en fonction")),
            ("epe_affectation_id", _("Affectation")),
            ("epe_evaluateur_id", _("Évaluateur")),
            ("epe_date_evaluation", _("Date d'évaluation")),
            ("epe_points_forts", _("Points Forts")),
            ("epe_points_ameliorer", _("Points à améliorer")),
            ("epe_missions_realisation", _("Principales missions et réalisations")),
            ("epe_atteinte_resultats", _("Atteinte des résultats/objectifs")),
            ("epe_potentiel_developpement", _("Potentiel pour le développement")),
            ("epe_maitrise_technique", _("Maitrise technique")),
            ("epe_capacite_adaptation", _("Capacité d'adaptation")),
            ("epe_engagement_dynamisme", _("Engagement et dynamisme")),
            ("epe_autonomie_initiative", _("Autonomie et prise d'initiative")),
            ("epe_commentaire", _("Commentaire")),
        ]
        return [label for field_name, label in checks if not self[field_name]]

    def _get_missing_fa_fields(self):
        self.ensure_one()
        checks = [
            ("fa_interview_realisee_par", _("Entretien réalisé par")),
            ("fa_date_entretien", _("Date d'entretien")),
            ("fa_presentation_generale", _("Présentation générale")),
            ("fa_formation_initiale", _("Formation initiale")),
            ("fa_formation_complementaire_eval", _("Formation complémentaire")),
            ("fa_experiences_professionnelles", _("Expériences professionnelles / Compétences métiers")),
            ("fa_communication_orale", _("Communication orale")),
            ("fa_ecoute", _("Écoute")),
            ("fa_negociation_persuasion", _("Capacité de négociation et persuasion")),
            ("fa_esprit_equipe_leadership", _("Esprit d'équipe / leadership")),
            ("fa_autonomie", _("Autonomie")),
            ("fa_dynamisme", _("Dynamisme")),
            ("fa_reactivite", _("Réactivité")),
            ("fa_engagement", _("Engagement")),
            ("fa_rigueur", _("Rigueur")),
            ("fa_actuellement_en_poste", _("Actuellement en poste")),
            ("fa_appreciations_generales", _("Appréciations et motivations générales")),
        ]
        missing = [label for field_name, label in checks if not self[field_name]]
        if self.fa_actuellement_en_poste == "oui":
            for field_name, label in [
                ("fa_fonction_actuelle", _("Fonction actuelle")),
                ("fa_entreprise_actuelle", _("Entreprise actuelle")),
                ("fa_salaire_actuel", _("Salaire actuel")),
                ("fa_preavis", _("Préavis")),
            ]:
                if not self[field_name]:
                    missing.append(label)
        if self.demande_type != "demande_stagiaire" or self.stagiaire_remuneration == "avec":
            if not self.fa_pretentions_salariales_num or self.fa_pretentions_salariales_num <= 0:
                missing.append(_("Prétentions salariales"))
        return missing

    def _get_missing_rhfa_fields(self):
        self.ensure_one()
        checks = [
            ("rhfa_interview_realisee_par", _("Entretien réalisé par")),
            ("rhfa_date_entretien", _("Date d'entretien")),
            ("rhfa_presentation_generale", _("Présentation générale")),
            ("rhfa_formation_initiale", _("Formation initiale")),
            ("rhfa_formation_complementaire_eval", _("Formation complémentaire")),
            ("rhfa_experiences_professionnelles", _("Expériences professionnelles / Compétences métiers")),
            ("rhfa_communication_orale", _("Communication orale")),
            ("rhfa_ecoute", _("Écoute")),
            ("rhfa_negociation_persuasion", _("Capacité de négociation et persuasion")),
            ("rhfa_esprit_equipe_leadership", _("Esprit d'équipe / leadership")),
            ("rhfa_autonomie", _("Autonomie")),
            ("rhfa_dynamisme", _("Dynamisme")),
            ("rhfa_reactivite", _("Réactivité")),
            ("rhfa_engagement", _("Engagement")),
            ("rhfa_rigueur", _("Rigueur")),
            ("rhfa_actuellement_en_poste", _("Actuellement en poste")),
            ("rhfa_appreciations_generales", _("Appréciations et motivations générales")),
        ]
        missing = [label for field_name, label in checks if not self[field_name]]
        if self.rhfa_actuellement_en_poste == "oui":
            for field_name, label in [
                ("rhfa_fonction_actuelle", _("Fonction actuelle")),
                ("rhfa_entreprise_actuelle", _("Entreprise actuelle")),
                ("rhfa_salaire_actuel", _("Salaire actuel")),
                ("rhfa_preavis", _("Préavis")),
            ]:
                if not self[field_name]:
                    missing.append(label)
        if self.demande_type != "demande_stagiaire" or self.stagiaire_remuneration == "avec":
            if not self.rhfa_pretentions_salariales_num or self.rhfa_pretentions_salariales_num <= 0:
                missing.append(_("Prétentions salariales"))
        return missing

    @api.constrains(
        "parent_state",
        "is_refused_line",
        "epe_nom_prenom",
        "epe_poste",
        "epe_date_entree_fonction",
        "epe_date_evaluation",
        "epe_points_forts",
        "epe_points_ameliorer",
        "epe_missions_realisation",
        "epe_atteinte_resultats",
        "epe_potentiel_developpement",
        "epe_maitrise_technique",
        "epe_capacite_adaptation",
        "epe_engagement_dynamisme",
        "epe_autonomie_initiative",
        "epe_commentaire",
    )
    def _check_epe_fields(self):
        if self.env.context.get("skip_epe_required_check"):
            return

        for rec in self:
            if rec.parent_state != "periode_essai_n1" or rec.is_refused_line:
                continue

            started = any([
                rec.epe_nom_prenom,
                rec.epe_poste,
                rec.epe_date_entree_fonction,
                rec.epe_date_evaluation,
                rec.epe_points_forts,
                rec.epe_points_ameliorer,
                rec.epe_missions_realisation,
                rec.epe_atteinte_resultats,
                rec.epe_potentiel_developpement,
                rec.epe_maitrise_technique,
                rec.epe_capacite_adaptation,
                rec.epe_engagement_dynamisme,
                rec.epe_autonomie_initiative,
                rec.epe_commentaire,
        ])

            if started and not rec.epe_complete:
                rec._raise_candidate_missing_fields(
                    _("Veuillez renseigner les champs obligatoires suivants :"),
                    rec._get_missing_epe_fields()
                )
                raise ValidationError(_(
                    "Veuillez renseigner tous les champs obligatoires de la fiche EPE. "
                    "Le champ 'Autres Remarques' reste facultatif."
                ))

    @api.depends(
    "fa_presentation_generale",
    "fa_formation_initiale",
    "fa_formation_complementaire_eval",
    "fa_experiences_professionnelles",
    "fa_communication_orale",
    "fa_ecoute",
    "fa_negociation_persuasion",
    "fa_esprit_equipe_leadership",
    "fa_autonomie",
    "fa_dynamisme",
    "fa_reactivite",
    "fa_engagement",
    "fa_rigueur",
)
    def _compute_fa_note_globale(self):
        for rec in self:
            values = [
                rec.fa_presentation_generale,
                rec.fa_formation_initiale,
                rec.fa_formation_complementaire_eval,
                rec.fa_experiences_professionnelles,
                rec.fa_communication_orale,
                rec.fa_ecoute,
                rec.fa_negociation_persuasion,
                rec.fa_esprit_equipe_leadership,
                rec.fa_autonomie,
                rec.fa_dynamisme,
                rec.fa_reactivite,
                rec.fa_engagement,
                rec.fa_rigueur,
            ]

            total = sum(int(v) for v in values if v not in (False, None, ""))
            rec.fa_note_globale = total / 13.0

    @api.depends(
    "rhfa_presentation_generale",
    "rhfa_formation_initiale",
    "rhfa_formation_complementaire_eval",
    "rhfa_experiences_professionnelles",
    "rhfa_communication_orale",
    "rhfa_ecoute",
    "rhfa_negociation_persuasion",
    "rhfa_esprit_equipe_leadership",
    "rhfa_autonomie",
    "rhfa_dynamisme",
    "rhfa_reactivite",
    "rhfa_engagement",
    "rhfa_rigueur",
)
    def _compute_rhfa_note_globale(self):
        for rec in self:
            values = [
                rec.rhfa_presentation_generale,
                rec.rhfa_formation_initiale,
                rec.rhfa_formation_complementaire_eval,
                rec.rhfa_experiences_professionnelles,
                rec.rhfa_communication_orale,
                rec.rhfa_ecoute,
                rec.rhfa_negociation_persuasion,
                rec.rhfa_esprit_equipe_leadership,
                rec.rhfa_autonomie,
                rec.rhfa_dynamisme,
                rec.rhfa_reactivite,
                rec.rhfa_engagement,
                rec.rhfa_rigueur,
            ]

            total = sum(int(v) for v in values if v not in (False, None, ""))
            rec.rhfa_note_globale = total / 13.0

    @api.constrains(
        "fa_pretentions_salariales_num",
        "rhfa_pretentions_salariales_num",
        "parent_step",
        "demande_type",
        "stagiaire_remuneration",
    )
    def _check_pretentions_salariales_positive(self):
        for rec in self:
            pretention_required = (
                rec.demande_type != "demande_stagiaire"
                or (
                    rec.demande_type == "demande_stagiaire"
                    and rec.stagiaire_remuneration == "avec"
                )
            )

            if not pretention_required:
                continue

            if rec.parent_step == "demandeur_final_choice":
                if rec.fa_pretentions_salariales_num not in (False, None):
                    if rec.fa_pretentions_salariales_num <= 0:
                        raise ValidationError(_("Les prétentions salariales de la FA doivent être supérieures à 0."))

            if rec.parent_step == "rh_validate_final":
                if rec.rhfa_pretentions_salariales_num not in (False, None):
                    if rec.rhfa_pretentions_salariales_num <= 0:
                        raise ValidationError(_("Les prétentions salariales de la FA RH doivent être supérieures à 0."))

    @api.depends(
        "fa_interview_realisee_par",
        "fa_date_entretien",
        "fa_presentation_generale",
        "fa_formation_initiale",
        "fa_formation_complementaire_eval",
        "fa_experiences_professionnelles",
        "fa_communication_orale",
        "fa_ecoute",
        "fa_negociation_persuasion",
        "fa_esprit_equipe_leadership",
        "fa_autonomie",
        "fa_dynamisme",
        "fa_reactivite",
        "fa_engagement",
        "fa_rigueur",
        "fa_actuellement_en_poste",
        "fa_fonction_actuelle",
        "fa_entreprise_actuelle",
        "fa_salaire_actuel",
        "fa_preavis",
        "fa_pretentions_salariales_num",
        "fa_appreciations_generales",
        "demande_type",
        "stagiaire_remuneration",
    )
    def _compute_fa_complete(self):
        for rec in self:
            pretention_ok = (
                rec.demande_type != "demande_stagiaire"
                or rec.stagiaire_remuneration == "avec"
            )

            if pretention_ok:
                pretention_ok = bool(
                    rec.fa_pretentions_salariales_num
                    and rec.fa_pretentions_salariales_num > 0
                )
            else:
                pretention_ok = True

            base_ok = all([
                rec.fa_interview_realisee_par,
                rec.fa_date_entretien,
                rec.fa_presentation_generale,
                rec.fa_formation_initiale,
                rec.fa_formation_complementaire_eval,
                rec.fa_experiences_professionnelles,
                rec.fa_communication_orale,
                rec.fa_ecoute,
                rec.fa_negociation_persuasion,
                rec.fa_esprit_equipe_leadership,
                rec.fa_autonomie,
                rec.fa_dynamisme,
                rec.fa_reactivite,
                rec.fa_engagement,
                rec.fa_rigueur,
                rec.fa_actuellement_en_poste,
                pretention_ok,
                rec.fa_appreciations_generales,
            ])

            poste_ok = True
            if rec.fa_actuellement_en_poste == "oui":
                poste_ok = all([
                    rec.fa_fonction_actuelle,
                    rec.fa_entreprise_actuelle,
                    rec.fa_salaire_actuel,
                    rec.fa_preavis,
                ])

            rec.fa_complete = bool(base_ok and poste_ok)

    @api.depends(
        "rhfa_interview_realisee_par",
        "rhfa_date_entretien",
        "rhfa_presentation_generale",
        "rhfa_formation_initiale",
        "rhfa_formation_complementaire_eval",
        "rhfa_experiences_professionnelles",
        "rhfa_communication_orale",
        "rhfa_ecoute",
        "rhfa_negociation_persuasion",
        "rhfa_esprit_equipe_leadership",
        "rhfa_autonomie",
        "rhfa_dynamisme",
        "rhfa_reactivite",
        "rhfa_engagement",
        "rhfa_rigueur",
        "rhfa_actuellement_en_poste",
        "rhfa_fonction_actuelle",
        "rhfa_entreprise_actuelle",
        "rhfa_salaire_actuel",
        "rhfa_preavis",
        "rhfa_pretentions_salariales_num",
        "rhfa_appreciations_generales",
        "demande_type",
        "stagiaire_remuneration",
    )
    def _compute_rhfa_complete(self):
        for rec in self:
            pretention_ok = (
                rec.demande_type != "demande_stagiaire"
                or rec.stagiaire_remuneration == "avec"
            )

            if pretention_ok:
                pretention_ok = bool(
                    rec.rhfa_pretentions_salariales_num
                    and rec.rhfa_pretentions_salariales_num > 0
                )
            else:
                pretention_ok = True

            base_ok = all([
                rec.rhfa_interview_realisee_par,
                rec.rhfa_date_entretien,
                rec.rhfa_presentation_generale,
                rec.rhfa_formation_initiale,
                rec.rhfa_formation_complementaire_eval,
                rec.rhfa_experiences_professionnelles,
                rec.rhfa_communication_orale,
                rec.rhfa_ecoute,
                rec.rhfa_negociation_persuasion,
                rec.rhfa_esprit_equipe_leadership,
                rec.rhfa_autonomie,
                rec.rhfa_dynamisme,
                rec.rhfa_reactivite,
                rec.rhfa_engagement,
                rec.rhfa_rigueur,
                rec.rhfa_actuellement_en_poste,
                pretention_ok,
                rec.rhfa_appreciations_generales,
            ])

            poste_ok = True
            if rec.rhfa_actuellement_en_poste == "oui":
                poste_ok = all([
                    rec.rhfa_fonction_actuelle,
                    rec.rhfa_entreprise_actuelle,
                    rec.rhfa_salaire_actuel,
                    rec.rhfa_preavis,
                ])

            rec.rhfa_complete = bool(base_ok and poste_ok)

    def action_open_fa(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fiche d'appréciation"),
            "res_model": "ar.demande.recrutement.candidate",
            "view_mode": "form",
            "view_id": self.env.ref("ar_recrutement.view_ar_demande_recrutement_candidate_fa_form").id,
            "res_id": self.id,
            "target": "new",
            "context": {
                "default_fa_interview_realisee_par": self.env.user.id,
            },
        }

    def action_open_rh_fa(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fiche d'appréciation RH"),
            "res_model": "ar.demande.recrutement.candidate",
            "view_mode": "form",
            "view_id": self.env.ref("ar_recrutement.view_ar_demande_recrutement_candidate_rhfa_form").id,
            "res_id": self.id,
            "target": "new",
            "context": {
                "default_rhfa_interview_realisee_par": self.env.user.id,
            },
        }
    
    def _open_candidate_recruitment_popup(self, xmlid, title):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "ar.demande.recrutement.candidate",
            "view_mode": "form",
            "view_id": self.env.ref(xmlid).id,
            "res_id": self.id,
            "target": "new",
        }

    def action_open_candidate_entretien_popup(self):
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_entretien",
            _("Entretien"),
        )

    def action_open_candidate_deliberation_offre_popup(self):
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_deliberation_offre",
            _("Offre du Candidat"),
        )

    def action_open_candidate_date_matricule_popup(self):
        if self.demande_type == "demande_stagiaire":
            return self._open_candidate_recruitment_popup(
                "ar_recrutement.view_ar_demande_recrutement_candidate_popup_date_embauche",
                _("Date d'embauche"),
            )
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_date_matricule",
            _("Date d'embauche & Matricule"),
        )

    def action_open_candidate_stagiaire_documents_popup(self):
        self.ensure_one()
        if not self.demande_id:
            raise ValidationError(_("Aucune demande liee a ce candidat."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Documents stagiaire"),
            "res_model": "ar.demande.de.recrutement",
            "view_mode": "form",
            "view_id": self.env.ref("ar_recrutement.view_ar_demande_recrutement_popup_stagiaire_documents").id,
            "res_id": self.demande_id.id,
            "target": "new",
        }

    def action_open_candidate_dossier_popup(self):
        self.ensure_one()
        if self.demande_id:
            self.demande_id._ensure_dossier_candidat_lines()
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_dossier",
            _("Dossier du Candidat"),
        )

    def action_open_candidate_visite_medicale_popup(self):
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_visite_medicale",
            _("Visite medicale"),
        )

    def action_open_candidate_announcement_popup(self):
        self.ensure_one()
        if self.demande_id:
            self.demande_id._ensure_dossier_candidat_lines()
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_announcement",
            _("Announcement"),
        )

    def action_open_candidate_suivi_collaborateur_popup(self):
        self.ensure_one()
        if self.demande_id:
            self.demande_id._sync_integration_lines()
        return self._open_candidate_recruitment_popup(
            "ar_recrutement.view_ar_demande_recrutement_candidate_popup_suivi_collaborateur",
            _("Suivi collaborateur"),
        )

    def action_send_candidate_announcement_mail(self):
        self.ensure_one()
        rec = self.demande_id
        if not rec:
            raise ValidationError(_("Aucune demande liee a ce candidat."))
        if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut envoyer l'announcement."))
        if rec.state != "envoie_annonce":
            raise AccessError(_("L'envoi de l'announcement est autorise uniquement a l'etat Announcement."))
        if self.offre_decision != "accepte" or not self.hiring_date:
            raise ValidationError(_("Ce candidat n'est pas encore pret pour l'announcement."))
        if self.announcement_sent:
            raise ValidationError(_("L'announcement de ce candidat a deja ete envoye."))

        missing = []
        if not self.announcement_civility:
            missing.append(_("Announcement : Civilite (%s)") % self.candidate_name)
        photo_line = rec.with_context(announcement_candidate_id=self.id)._get_announcement_photo_line()
        if not photo_line:
            missing.append(_("Announcement : Photo (%s)") % self.candidate_name)
        rec._raise_missing_fields(_("Veuillez renseigner les champs obligatoires suivants :"), missing)

        recipients = rec._get_employee_emails()
        if not recipients:
            raise ValidationError(_("Aucun email employe trouve pour envoyer l'announcement."))

        template = rec.env.ref("ar_recrutement.mail_template_rec_announcement_to_employees", raise_if_not_found=False)
        if not template:
            raise ValidationError(_("Template email announcement introuvable."))

        clean_recipients = [rec._clean_header(email) for email in recipients]
        clean_recipients = [email for email in clean_recipients if email]
        template.with_context(announcement_candidate_id=self.id).send_mail(
            rec.id,
            force_send=True,
            email_values={
                "email_to": rec._clean_header(",".join(clean_recipients)),
                "reply_to": rec._clean_header(rec.env.user.partner_id.email or rec.env.user.email or ""),
            },
        )
        self.write({
            "announcement_sent": True,
            "announcement_sent_date": fields.Date.context_today(rec),
        })
        rec.message_post(
            body=_("L'email d'announcement a ete envoye pour le candidat %s a %s employe(s).") % (self.candidate_name, len(clean_recipients))
        )
        return {"type": "ir.actions.act_window_close"}

    def action_download_fa(self):
        self.ensure_one()
        return self.env.ref("ar_recrutement.action_report_candidate_fa").report_action(self)
    
    def action_download_rh_fa(self):
        self.ensure_one()
        return self.env.ref("ar_recrutement.action_report_candidate_rhfa").report_action(self)

    @api.depends("demandeur_decision")
    def _compute_is_refused_line(self):
        for rec in self:
            rec.is_refused_line = (rec.demandeur_decision == "refuse")

    @api.constrains(
        "fa_actuellement_en_poste",
        "fa_pretentions_salariales_num",
        "parent_step",
        "demande_type",
        "stagiaire_remuneration",
    )
    def _check_fa_fields(self):
        for rec in self:
            if rec.parent_step != "demandeur_final_choice":
                continue

            pretention_required = (
                rec.demande_type != "demande_stagiaire"
                or rec.stagiaire_remuneration == "avec"
            )

            if any([
                rec.fa_date_entretien,
                rec.fa_presentation_generale,
                rec.fa_formation_initiale,
                rec.fa_formation_complementaire_eval,
                rec.fa_experiences_professionnelles,
                rec.fa_communication_orale,
                rec.fa_ecoute,
                rec.fa_negociation_persuasion,
                rec.fa_esprit_equipe_leadership,
                rec.fa_autonomie,
                rec.fa_dynamisme,
                rec.fa_reactivite,
                rec.fa_engagement,
                rec.fa_rigueur,
                rec.fa_actuellement_en_poste,
                rec.fa_pretentions_salariales_num if pretention_required else False,
                rec.fa_appreciations_generales,
            ]) and not rec.fa_complete:
                if pretention_required:
                    if rec.fa_pretentions_salariales_num not in (False, None):
                        if rec.fa_pretentions_salariales_num <= 0:
                            raise ValidationError(_("Les prétentions salariales de la FA doivent être supérieures à 0."))

                rec._raise_candidate_missing_fields(
                    _("Veuillez renseigner les champs obligatoires suivants :"),
                    rec._get_missing_fa_fields()
                )
                raise ValidationError(_("Veuillez renseigner tous les champs obligatoires de la fiche FA."))

    @api.constrains(
        "rhfa_actuellement_en_poste",
        "rhfa_pretentions_salariales_num",
        "parent_step",
        "demande_type",
        "stagiaire_remuneration",
    )
    def _check_rhfa_fields(self):
        for rec in self:
            if rec.parent_step != "rh_validate_final":
                continue

            pretention_required = (
                rec.demande_type != "demande_stagiaire"
                or rec.stagiaire_remuneration == "avec"
            )

            if any([
                rec.rhfa_date_entretien,
                rec.rhfa_presentation_generale,
                rec.rhfa_formation_initiale,
                rec.rhfa_formation_complementaire_eval,
                rec.rhfa_experiences_professionnelles,
                rec.rhfa_communication_orale,
                rec.rhfa_ecoute,
                rec.rhfa_negociation_persuasion,
                rec.rhfa_esprit_equipe_leadership,
                rec.rhfa_autonomie,
                rec.rhfa_dynamisme,
                rec.rhfa_reactivite,
                rec.rhfa_engagement,
                rec.rhfa_rigueur,
                rec.rhfa_actuellement_en_poste,
                rec.rhfa_pretentions_salariales_num if pretention_required else False,
                rec.rhfa_appreciations_generales,
            ]) and not rec.rhfa_complete:
                if pretention_required:
                    if rec.rhfa_pretentions_salariales_num not in (False, None):
                        if rec.rhfa_pretentions_salariales_num <= 0:
                            raise ValidationError(_("Les prétentions salariales de la FA RH doivent être supérieures à 0."))

                rec._raise_candidate_missing_fields(
                    _("Veuillez renseigner les champs obligatoires suivants :"),
                    rec._get_missing_rhfa_fields()
                )
                raise ValidationError(_("Veuillez renseigner tous les champs obligatoires de la fiche FA RH."))
            
    def action_save_candidate_popup(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window_close"}

    
class ARDemandeRecrutementAnnonce(models.Model):
    _name = "ar.demande.recrutement.annonce"
    _description = "Lignes Annonce - Demande de Recrutement"
    _order = "id desc"

    demande_id = fields.Many2one(
        "ar.demande.de.recrutement",
        string="Demande",
        required=True,
        ondelete="cascade",
        tracking=True
    )

    annonce_file = fields.Binary(
        string="Fichier d'annonce",
        attachment=True,
        required=True,
        tracking=True
    )
    annonce_filename = fields.Char(string="Nom du fichier annonce", tracking=True)

    annonce_link = fields.Char(string="Lien d'annonce", tracking=True)

    def _check_rh_can_edit(self):
        if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner les annonces."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_rh_can_edit()
        return super().create(vals_list)

    def write(self, vals):
        if {"annonce_file", "annonce_filename", "annonce_link"}.intersection(vals):
            self._check_rh_can_edit()
        return super().write(vals)

    def unlink(self):
        self._check_rh_can_edit()
        return super().unlink()


class ARDemandeRecrutementDossierCandidatLine(models.Model):
    _name = "ar.demande.recrutement.dossier.candidat.line"
    _description = "Dossier du Candidat - Demande de Recrutement"
    _order = "candidate_id, id asc"

    demande_id = fields.Many2one(
        "ar.demande.de.recrutement",
        string="Demande",
        required=True,
        ondelete="cascade",
        tracking=True
    )

    demande_state = fields.Selection(
        related="demande_id.state",
        string="État demande",
        store=True,
        readonly=True
    )

    candidate_id = fields.Many2one(
        "ar.demande.recrutement.candidate",
        string="Candidat",
        ondelete="cascade",
        tracking=True,
    )
    candidate_name = fields.Char(
        string="Candidat",
        compute="_compute_candidate_name",
        store=False,
    )

    @api.depends("candidate_id", "candidate_id.candidate_name", "demande_id.candidate_ids.offre_decision", "demande_id.candidate_ids.hiring_date")
    def _compute_candidate_name(self):
        for rec in self:
            if rec.candidate_id:
                rec.candidate_name = rec.candidate_id.candidate_name
                continue

            candidates = rec.demande_id.candidate_ids.filtered(
                lambda c: c.offre_decision == "accepte"
                and c.hiring_date
                and not c.is_refused_line
            )
            rec.candidate_name = candidates.candidate_name if len(candidates) == 1 else ""

    document_type = fields.Selection([
        ("cin", "CIN"),
        ("certificat_habitude_physique", "Certficat d'habiyude physique"),
        ("diplomes", "Diplômes"),
        ("attestations", "Attestations"),
        ("certificats_anciennes_experiences", "Certificats des anciennes expériences"),
        ("fiche_anthropometrique", "Fiche anthropométrique"),
        ("extrait_naissance", "Extrait de naissance"),
        ("certificat_residence", "Certificat de résidence"),
        ("photos", "Photos"),
        ("acte_mariage", "Acte de mariage"),
        ("extrait_naissance_enfants", "Extrait de naissances des enfants"),
        ("cv", "CV"),
        ("diplome", "Diplôme"),
        ("attestation_travail", "Attestation de travail"),
        ("rib", "RIB"),
        ("photo", "Photo"),
        ("contrat", "Contrat"),
        ("autre", "Autre"),
    ], string="Document", tracking=True)

    document_file = fields.Binary(
        string="Fichier",
        attachment=True,
        tracking=True
    )

    document_filename = fields.Char(string="Nom du fichier", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner le Dossier du Candidat."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner le Dossier du Candidat."))
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner le Dossier du Candidat."))
        return super().unlink()

class ARDemandeRecrutementIntegration(models.Model):
    _name = "ar.demande.recrutement.integration"
    _description = "Parcours d'intégration - Demande de recrutement"
    _order = "id desc"

    def init(self):
        super().init()
        self.env.cr.execute("""
            DO $$
            BEGIN
                IF to_regclass('public.ar_demande_recrutement_integration') IS NULL THEN
                    RETURN;
                END IF;

                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name = 'ar_demande_recrutement_integration'
                       AND column_name = 'demande_id'
                       AND is_nullable = 'NO'
                ) THEN
                    EXECUTE 'ALTER TABLE ar_demande_recrutement_integration ALTER COLUMN demande_id DROP NOT NULL';
                END IF;

                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name = 'ar_demande_recrutement_integration'
                       AND column_name IN ('validation_n1_essai', 'validation_rh_essai')
                ) THEN
                    EXECUTE $sql$
                        UPDATE ar_demande_recrutement_integration
                           SET validation_n1_essai = CASE validation_n1_essai
                               WHEN 'oui' THEN 'confirmation'
                               WHEN 'non' THEN 'rupture'
                               ELSE validation_n1_essai
                           END,
                           validation_rh_essai = CASE validation_rh_essai
                               WHEN 'oui' THEN 'confirmation'
                               WHEN 'non' THEN 'rupture'
                               ELSE validation_rh_essai
                           END
                         WHERE validation_n1_essai IN ('oui', 'non')
                            OR validation_rh_essai IN ('oui', 'non')
                    $sql$;
                END IF;

                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name = 'ar_demande_recrutement_integration'
                       AND column_name = 'validation_direction_generale'
                ) THEN
                    EXECUTE $sql$
                        UPDATE ar_demande_recrutement_integration
                           SET validation_direction_generale = CASE validation_direction_generale
                               WHEN 'oui' THEN 'confirmation'
                               WHEN 'non' THEN 'rupture'
                               ELSE validation_direction_generale
                           END
                         WHERE validation_direction_generale IN ('oui', 'non')
                    $sql$;
                END IF;

                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name = 'ar_demande_recrutement_integration'
                       AND column_name = 'validation_demande_id'
                ) THEN
                    EXECUTE $sql$
                        UPDATE ar_demande_recrutement_integration
                           SET validation_demande_id = demande_id
                         WHERE validation_demande_id IS NULL
                           AND demande_id IS NOT NULL
                    $sql$;

                    IF to_regclass('public.ar_demande_recrutement_integration_line') IS NOT NULL THEN
                        EXECUTE $sql$
                            UPDATE ar_demande_recrutement_integration integration
                               SET demande_id = NULL
                              FROM (
                                    SELECT DISTINCT ON (integration.validation_demande_id, integration.candidate_id)
                                           integration.validation_demande_id,
                                           integration.candidate_id,
                                           integration.id AS keep_id
                                      FROM ar_demande_recrutement_integration integration
                                     WHERE integration.validation_demande_id IS NOT NULL
                                       AND integration.candidate_id IS NOT NULL
                                     ORDER BY integration.validation_demande_id,
                                              integration.candidate_id,
                                              CASE
                                                  WHEN EXISTS (
                                                      SELECT 1
                                                        FROM ar_demande_recrutement_integration_line detail
                                                       WHERE detail.integration_id = integration.id
                                                  )
                                                  THEN 1 ELSE 0
                                              END DESC,
                                              CASE
                                                  WHEN COALESCE(integration.feedback_rh, '') != ''
                                                    OR COALESCE(integration.feedback_md, '') != ''
                                                  THEN 1 ELSE 0
                                              END DESC,
                                              CASE
                                                  WHEN COALESCE(integration.validation_n1_essai, '') != ''
                                                    OR COALESCE(integration.validation_rh_essai, '') != ''
                                                    OR COALESCE(integration.validation_direction_generale, '') != ''
                                                    OR COALESCE(integration.validation_deliberation_finale, '') != ''
                                                  THEN 1 ELSE 0
                                              END DESC,
                                              integration.id DESC
                              ) AS kept_lines
                             WHERE integration.validation_demande_id = kept_lines.validation_demande_id
                               AND integration.candidate_id = kept_lines.candidate_id
                               AND integration.id != kept_lines.keep_id
                        $sql$;
                    END IF;
                END IF;
            END $$;
        """)
    demande_id = fields.Many2one(
        "ar.demande.de.recrutement",
        string="Demande",
        ondelete="cascade",
        tracking=True
    )

    validation_demande_id = fields.Many2one(
        "ar.demande.de.recrutement",
        string="Demande validation période d'essai",
        ondelete="cascade",
        tracking=True
    )

    demande_state = fields.Selection(
        selection=lambda self: self.env["ar.demande.de.recrutement"]._fields["state"].selection,
        string="État demande",
        compute="_compute_demande_state",
        store=True,
        readonly=True
    )

    current_user_is_rh = fields.Boolean(
        string="Utilisateur RH",
        compute="_compute_current_user_roles",
        store=False,
    )

    current_user_is_manager = fields.Boolean(
        string="Utilisateur manager",
        compute="_compute_current_user_roles",
        store=False,
    )

    current_user_can_act_as_demandeur = fields.Boolean(
        string="Peut agir comme demandeur",
        compute="_compute_current_user_roles",
        store=False,
    )

    current_user_is_md = fields.Boolean(
        string="Utilisateur MD",
        compute="_compute_current_user_roles",
        store=False,
    )

    @api.depends("demande_id.state", "validation_demande_id.state")
    def _compute_demande_state(self):
        for rec in self:
            demande = rec.demande_id or rec.validation_demande_id
            rec.demande_state = demande.state if demande else False

    @api.depends_context("uid")
    def _compute_current_user_roles(self):
        is_rh = self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh")
        is_manager = self.env.user.has_group("ar_recrutement.group_ar_recrutement_manager")
        is_md = self.env.user.has_group("ar_recrutement.group_ar_recrutement_md")
        for rec in self:
            rec.current_user_is_rh = is_rh
            rec.current_user_is_manager = is_manager
            rec.current_user_is_md = is_md
            demande = rec.validation_demande_id or rec.demande_id
            rec.current_user_can_act_as_demandeur = bool(
                demande and demande.current_user_can_act_as_demandeur
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        demandes = records.mapped("demande_id")
        if demandes:
            demandes._cleanup_suivi_duplicate_lines()
        return records

    def write(self, vals):
        if "feedback_rh" in vals and not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner le Feedback RH."))
        if "feedback_md" in vals and not self.env.user.has_group("ar_recrutement.group_ar_recrutement_md"):
            raise AccessError(_("Seul le groupe MD peut renseigner le Feedback MD."))
        if "validation_n1_essai" in vals:
            for rec in self:
                demande = rec.validation_demande_id or rec.demande_id
                if not demande or demande.state != "periode_essai_n1":
                    raise AccessError(_("La période d'essai N+1 est modifiable uniquement à l'étape Période d'essai N+1."))
                demande._check_can_act_as_demandeur()
        if "validation_rh_essai" in vals and not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner la période d'essai RH."))
        if "validation_direction_generale" in vals and not self.env.user.has_group("ar_recrutement.group_ar_recrutement_md"):
            raise AccessError(_("Seul le groupe MD peut renseigner la Direction générale."))
        if "validation_deliberation_finale" in vals and not self.env.user.has_group("ar_recrutement.group_ar_recrutement_rh"):
            raise AccessError(_("Seul le groupe RH peut renseigner la délibération finale."))
        return super().write(vals)

    candidate_id = fields.Many2one(
        "ar.demande.recrutement.candidate",
        string="Candidat",
        required=True,
        ondelete="cascade",
        tracking=True
    )

    candidate_name = fields.Char(
        string="Nom du candidat",
        related="candidate_id.candidate_name",
        store=True,
        readonly=True
    )

    integration_department_id = fields.Many2one(
        "hr.department",
        string="Département",
        tracking=True
    )

    feedback_rh = fields.Text(string="Feedback RH", tracking=True)
    feedback_md = fields.Text(string="Feedback MD", tracking=True)

    is_trial_history = fields.Boolean(
        string="Historique",
        compute="_compute_is_trial_history",
        store=False
    )

    validation_n1_essai = fields.Selection([
        ("confirmation", "Confirmation"),
        ("reconduction", "Reconduction"),
        ("rupture", "Rupture du contrat"),
    ], string="PE N+1", tracking=True)

    epe_complete = fields.Boolean(
        related="candidate_id.epe_complete",
        string="EPE complétée",
        store=False,
        readonly=True
    )

    validation_rh_essai = fields.Selection([
        ("confirmation", "Confirmation"),
        ("reconduction", "Reconduction"),
        ("rupture", "Rupture du contrat"),
    ], string="PE RH", tracking=True)

    validation_direction_generale = fields.Selection([
        ("confirmation", "Confirmation"),
        ("reconduction", "Reconduction"),
        ("rupture", "Rupture du contrat"),
    ], string="Direction générale", tracking=True)

    validation_deliberation_finale = fields.Selection([
        ("confirmation", "Confirmation"),
        ("reconduction", "Reconduction"),
        ("rupture", "Rupture du contrat"),
    ], string="Délibération", tracking=True)

    @api.depends("demande_id", "validation_demande_id", "candidate_id", "validation_demande_id.validation_integration_ids.candidate_id")
    def _compute_is_trial_history(self):
        for rec in self:
            demande = rec.validation_demande_id or rec.demande_id
            if not demande or not rec.candidate_id:
                rec.is_trial_history = False
                continue

            same_candidate_lines = demande.validation_integration_ids.filtered(
                lambda l: l.candidate_id == rec.candidate_id
            )
            active_line = same_candidate_lines.sorted("id", reverse=True)[:1]
            rec.is_trial_history = bool(active_line and rec != active_line)

    has_integration_form = fields.Boolean(
        string="Formulaire intégration existant",
        compute="_compute_has_integration_form",
        store=False
    )

    integration_line_ids = fields.One2many(
        "ar.demande.recrutement.integration.line",
        "integration_id",
        string="Lignes d'intégration",
        tracking=True
    )

    @api.depends("integration_line_ids")
    def _compute_has_integration_form(self):
        for rec in self:
            rec.has_integration_form = bool(rec.integration_line_ids)

    def action_download_integration(self):
        self.ensure_one()
        return self.env.ref("ar_recrutement.action_report_candidate_integration").report_action(self)

    def _prepare_default_integration_lines(self):
        self.ensure_one()
        return [
            (0, 0, {
                "sequence": 10,
                "service_accueillant": "rh",
                "rubrique": "Présentation et visite de l'entreprise",
            }),
            (0, 0, {
                "sequence": 20,
                "service_accueillant": "rh",
                "rubrique": "Organigramme",
            }),
            (0, 0, {
                "sequence": 30,
                "service_accueillant": "rh",
                "rubrique": "Formation d'intégration Elearning",
            }),
            (0, 0, {
                "sequence": 40,
                "service_accueillant": "rh",
                "rubrique": "Servant Leadership & Its Pillars",
            }),
            (0, 0, {
                "sequence": 50,
                "service_accueillant": "rh",
                "rubrique": "Araymond's Dedication To Universal Human Rights",
            }),
            (0, 0, {
                "sequence": 60,
                "service_accueillant": "rh",
                "rubrique": "Sos Internatinal",
            }),
            (0, 0, {
                "sequence": 70,
                "service_accueillant": "rh",
                "rubrique": "Code De Conduite",
            }),
            (0, 0, {
                "sequence": 80,
                "service_accueillant": "qualite",
                "rubrique": "Qualité Développement",
            }),
            (0, 0, {
                "sequence": 90,
                "service_accueillant": "qualite",
                "rubrique": "Qualité terrain",
            }),
            (0, 0, {
                "sequence": 100,
                "service_accueillant": "qualite",
                "rubrique": "Qualité système",
            }),
            (0, 0, {
                "sequence": 110,
                "service_accueillant": "qualite",
                "rubrique": "Laboratoire",
            }),
            (0, 0, {
                "sequence": 120,
                "service_accueillant": "supply",
                "rubrique": "Partie terrain",
            }),
            (0, 0, {
                "sequence": 130,
                "service_accueillant": "supply",
                "rubrique": "Partie ADV",
            }),
            (0, 0, {
                "sequence": 140,
                "service_accueillant": "bd",
                "rubrique": "Costing",
            }),
            (0, 0, {
                "sequence": 150,
                "service_accueillant": "bd",
                "rubrique": "Program Manager",
            }),
            (0, 0, {
                "sequence": 160,
                "service_accueillant": "finance",
                "rubrique": "Finance",
            }),
            (0, 0, {
                "sequence": 170,
                "service_accueillant": "production",
                "rubrique": "Injection",
            }),
            (0, 0, {
                "sequence": 180,
                "service_accueillant": "production",
                "rubrique": "Assemblage",
            }),
            (0, 0, {
                "sequence": 190,
                "service_accueillant": "technique",
                "rubrique": "Technique",
            }),
            (0, 0, {
                "sequence": 200,
                "service_accueillant": "be",
                "rubrique": "BE",
            }),
            (0, 0, {
                "sequence": 210,
                "service_accueillant": "formation",
                "rubrique": "Formation poste de travail",
            }),
            (0, 0, {
                "sequence": 220,
                "service_accueillant": "process",
                "rubrique": "Procédure & Processus",
            }),
        ]


    def action_open_integration(self):
        self.ensure_one()

        if not self.integration_line_ids:
            self.write({
                "integration_line_ids": self._prepare_default_integration_lines()
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("Intégration"),
            "res_model": "ar.demande.recrutement.integration",
            "view_mode": "form",
            "view_id": self.env.ref("ar_recrutement.view_ar_demande_recrutement_integration_form").id,
            "res_id": self.id,
            "target": "new",
        }

    def action_open_epe(self):
        self.ensure_one()
        return self.candidate_id.action_open_epe()
    
class ARDemandeRecrutementIntegrationLine(models.Model):
    _name = "ar.demande.recrutement.integration.line"
    _description = "Ligne parcours d'intégration"
    _order = "sequence asc, id asc"

    integration_id = fields.Many2one(
        "ar.demande.recrutement.integration",
        string="Intégration",
        required=True,
        ondelete="cascade"
    )

    sequence = fields.Integer(string="Séquence", default=10)

    service_accueillant = fields.Selection([
        ("rh", "RH"),
        ("qualite", "Qualité"),
        ("supply", "Supply chain"),
        ("bd", "BD"),
        ("finance", "Finance"),
        ("production", "Production"),
        ("technique", "Technique"),
        ("be", "BE"),
        ("formation", "Formation poste de travail"),
        ("process", "Procédure & Processus"),
    ], string="Département ou Service accueillant", required=True)

    rubrique = fields.Char(
        string="Rubrique / Étape",
        required=True
    )

    tuteur_id = fields.Many2one(
        "res.users",
        string="Tuteur"
    )

    date_integration = fields.Date(
        string="Dates"
    )

    commentaire = fields.Text(
        string="Commentaire"
    )

    def get_service_accueillant_label(self):
        self.ensure_one()
        return dict(self._fields["service_accueillant"].selection).get(self.service_accueillant, "")

